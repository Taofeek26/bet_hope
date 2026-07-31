"""
Check Tasks Management Command

Shows status of scheduled Celery tasks.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Check status of scheduled Celery tasks'

    def handle(self, *args, **options):
        self.stdout.write('Checking Celery task configuration...\n')

        # Check beat schedule
        self._check_beat_schedule()

        # Check task routing
        self._check_task_routing()

        # Try to ping Celery
        self._ping_celery()

    def _check_beat_schedule(self):
        """Show configured beat schedule."""
        from config.celery import app

        schedule = app.conf.beat_schedule

        self.stdout.write(self.style.HTTP_INFO('Scheduled Tasks:'))
        self.stdout.write('-' * 50)

        for name, config in schedule.items():
            task = config['task']
            schedule_str = str(config['schedule'])
            queue = config.get('options', {}).get('queue', 'default')

            self.stdout.write(f'  {name}:')
            self.stdout.write(f'    Task: {task}')
            self.stdout.write(f'    Schedule: {schedule_str}')
            self.stdout.write(f'    Queue: {queue}')
            self.stdout.write('')

        self.stdout.write(self.style.SUCCESS(
            f'\nTotal: {len(schedule)} scheduled tasks'
        ))

    def _check_task_routing(self):
        """Show task routing configuration."""
        from config.celery import app

        routes = app.conf.task_routes

        self.stdout.write(self.style.HTTP_INFO('\nTask Routing:'))
        self.stdout.write('-' * 50)

        for pattern, config in routes.items():
            queue = config.get('queue', 'unknown')
            self.stdout.write(f'  {pattern} -> {queue}')

    def _ping_celery(self):
        """Try to ping Celery workers."""
        from config.celery import app

        self.stdout.write(self.style.HTTP_INFO('\nCelery Worker Status:'))
        self.stdout.write('-' * 50)

        try:
            i = app.control.inspect()

            # Get active workers
            active = i.active()
            if active:
                self.stdout.write(self.style.SUCCESS('Workers online:'))
                for worker, tasks in active.items():
                    self.stdout.write(f'  {worker}: {len(tasks)} active tasks')
            else:
                self.stdout.write(self.style.WARNING('No workers responding'))

            # Get registered tasks
            registered = i.registered()
            if registered:
                total_tasks = sum(len(tasks) for tasks in registered.values())
                self.stdout.write(self.style.SUCCESS(
                    f'\nTotal registered tasks: {total_tasks}'
                ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Could not connect to Celery: {e}'))
