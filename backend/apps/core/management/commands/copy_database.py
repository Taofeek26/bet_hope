"""
Copy every table from the current database (DATABASE_URL) into another
Postgres database. Built for the Phase 1 move off RDS (see
html/phase-1.html): run it inside the manage Lambda while it can still
reach RDS, pointing --target-url at the new Neon/Supabase database.

Steps:
  1. Report source table sizes (only this, with --report-only).
  2. Create the pgvector extension on the target and run `migrate` there.
  3. In ONE target transaction: truncate the copied tables, stream each
     table source -> target with COPY, then commit. Django creates its
     foreign keys DEFERRABLE INITIALLY DEFERRED, so table order doesn't
     matter inside the transaction.
  4. Move every id sequence past the copied rows.
  5. Compare row counts table by table; exit non-zero on any mismatch.

It never writes to the source database.
"""
import os
import subprocess
import sys
import threading

import dj_database_url
import psycopg2
from psycopg2 import sql
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _connect(db: dict):
    """Open a psycopg2 connection from a Django DATABASES-style dict."""
    options = {k: v for k, v in (db.get('OPTIONS') or {}).items()}
    options.setdefault('connect_timeout', 10)
    return psycopg2.connect(
        dbname=db['NAME'],
        user=db['USER'],
        password=db['PASSWORD'],
        host=db['HOST'],
        port=db.get('PORT') or 5432,
        **options,
    )


def _tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        return [r[0] for r in cur.fetchall()]


def _columns(conn, table):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            [table],
        )
        return [r[0] for r in cur.fetchall()]


def _count(conn, table):
    with conn.cursor() as cur:
        cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
        return cur.fetchone()[0]


class Command(BaseCommand):
    help = 'Copy all tables from the current database into another Postgres database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--target-url',
            default=os.getenv('TARGET_DATABASE_URL', ''),
            help='postgres:// URL of the target (or set TARGET_DATABASE_URL). '
                 'Use the DIRECT (non-pooled) connection string.',
        )
        parser.add_argument('--report-only', action='store_true',
                            help='Only print source database/table sizes.')
        parser.add_argument('--exclude', nargs='*', default=[],
                            help='Tables to skip (e.g. django_celery_results_taskresult).')
        parser.add_argument('--skip-migrate', action='store_true',
                            help='Target schema already migrated.')
        parser.add_argument('--yes-overwrite-target', action='store_true',
                            help='Required: the copied tables on the target are emptied first.')

    def handle(self, *args, **opts):
        source_db = settings.DATABASES['default']
        src = _connect(source_db)
        src.set_session(readonly=True)

        self._report(src)
        if opts['report_only']:
            return

        if not opts['target_url']:
            raise CommandError('--target-url (or TARGET_DATABASE_URL) is required.')
        if not opts['yes_overwrite_target']:
            raise CommandError('Refusing to run without --yes-overwrite-target.')

        target_db = dj_database_url.parse(opts['target_url'])
        if (target_db['HOST'], target_db['NAME']) == (source_db['HOST'], source_db['NAME']):
            raise CommandError('Target is the same database as the source.')

        dst = _connect(target_db)

        # 1. Schema on the target
        with dst.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
        dst.commit()
        if not opts['skip_migrate']:
            self.stdout.write('Running migrate on target...')
            result = subprocess.run(
                [sys.executable, 'manage.py', 'migrate', '--noinput'],
                env={**os.environ, 'DATABASE_URL': opts['target_url']},
                cwd=settings.BASE_DIR,
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise CommandError(f'migrate on target failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}')
            self.stdout.write(self.style.SUCCESS('  target migrated'))

        # 2. Decide which tables to copy: present on both sides, not excluded
        exclude = set(opts['exclude'])
        src_tables = set(_tables(src))
        dst_tables = set(_tables(dst))
        tables = sorted((src_tables & dst_tables) - exclude)
        missing = sorted(src_tables - dst_tables - exclude)
        if missing:
            self.stdout.write(self.style.WARNING(f'Only on source, not copied: {missing}'))

        # 3. Copy everything in one target transaction
        self.stdout.write(f'Copying {len(tables)} tables...')
        with dst.cursor() as cur:
            cur.execute('SET CONSTRAINTS ALL DEFERRED')
            cur.execute(sql.SQL('TRUNCATE {} CASCADE').format(
                sql.SQL(', ').join(sql.Identifier(t) for t in tables)))
        for table in tables:
            cols = _columns(dst, table)
            src_cols = set(_columns(src, table))
            cols = [c for c in cols if c in src_cols]
            self._copy_table(src, dst, table, cols)
            self.stdout.write(f'  {table}')
        dst.commit()

        # 4. Sequences
        self._reset_sequences(dst)

        # 5. Verify
        mismatches = []
        for table in tables:
            a, b = _count(src, table), _count(dst, table)
            if a != b:
                mismatches.append((table, a, b))
        src.close()
        dst.close()
        if mismatches:
            for t, a, b in mismatches:
                self.stdout.write(self.style.ERROR(f'  MISMATCH {t}: source={a} target={b}'))
            raise CommandError(f'{len(mismatches)} tables differ; do not switch DATABASE_URL yet.')
        self.stdout.write(self.style.SUCCESS(f'Done: {len(tables)} tables copied, row counts match.'))

    def _report(self, conn):
        with conn.cursor() as cur:
            cur.execute('SELECT pg_size_pretty(pg_database_size(current_database()))')
            self.stdout.write(f'Source database size: {cur.fetchone()[0]}')
            cur.execute(
                """
                SELECT relname, n_live_tup,
                       pg_size_pretty(pg_total_relation_size(relid))
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 25
                """
            )
            for name, rows, size in cur.fetchall():
                self.stdout.write(f'  {name:<45} ~{rows:>9} rows  {size}')

    def _copy_table(self, src, dst, table, cols):
        """Stream COPY TO STDOUT (source) into COPY FROM STDIN (target) via a pipe."""
        col_list = sql.SQL(', ').join(sql.Identifier(c) for c in cols)
        out_sql = sql.SQL('COPY (SELECT {} FROM {}) TO STDOUT').format(
            col_list, sql.Identifier(table)).as_string(src)
        in_sql = sql.SQL('COPY {} ({}) FROM STDIN').format(
            sql.Identifier(table), col_list).as_string(dst)

        read_fd, write_fd = os.pipe()
        errors = []

        def produce():
            try:
                with os.fdopen(write_fd, 'wb') as w, src.cursor() as cur:
                    cur.copy_expert(out_sql, w)
            except Exception as e:  # surfaced after the consumer finishes
                errors.append(e)

        producer = threading.Thread(target=produce)
        producer.start()
        with os.fdopen(read_fd, 'rb') as r, dst.cursor() as cur:
            cur.copy_expert(in_sql, r)
        producer.join()
        if errors:
            raise CommandError(f'Reading {table} from source failed: {errors[0]}')

    def _reset_sequences(self, conn):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND (is_identity = 'YES' OR column_default LIKE 'nextval(%%')
                """
            )
            for table, column in cur.fetchall():
                cur.execute(
                    sql.SQL(
                        "SELECT setval(pg_get_serial_sequence(%s, %s), "
                        "COALESCE((SELECT max({col}) FROM {tbl}), 1), "
                        "(SELECT max({col}) FROM {tbl}) IS NOT NULL)"
                    ).format(col=sql.Identifier(column), tbl=sql.Identifier(table)),
                    [table, column],
                )
        conn.commit()
        self.stdout.write('  sequences reset')
