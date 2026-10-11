'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQueries, useQuery } from '@tanstack/react-query';
import { Star, Trophy, Calendar, X } from 'lucide-react';
import { leaguesApi, teamsApi } from '@/lib/api';
import { useFavoritesStore } from '@/lib/store';
import { useSettings } from '@/contexts/SettingsContext';
import { formatDateWithPreset, formatKickoff } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

/**
 * Phase 4: real favourites. The page used to show hard-coded demo teams
 * (Arsenal "vs Chelsea – Today 15:00", ...) with buttons that did nothing.
 * Favourites are added with the star on any team or league page and kept
 * in this browser.
 */
export default function FavoritesPage() {
  const { favoriteTeams, favoriteLeagues, toggleFavoriteTeam, toggleFavoriteLeague } = useFavoritesStore();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  const teamIds = ready ? favoriteTeams : [];
  const leagueCodes = ready ? favoriteLeagues : [];

  return (
    <>
      <div className="content-header">
        <h1>Favourites</h1>
        <p>Teams and leagues you follow. Add them with the ☆ button on any team or league page.</p>
      </div>

      <div className="content-grid">
        <div className="col-span-8">
          <div className="card">
            <div className="card-header">
              <div className="card-icon"><Star className="w-5 h-5" /></div>
              <div>
                <h2 className="card-title">Favourite teams</h2>
                <p className="card-desc">Next fixture for each team</p>
              </div>
            </div>
            {!ready ? <LoadingSpinner /> : teamIds.length === 0 ? (
              <Empty
                text="No favourite teams yet."
                hint="Open a team (search in the header, or click a team in any league table) and press “Add to favourites”."
                href="/leagues" cta="Browse leagues"
              />
            ) : (
              <div className="space-y-3">
                {teamIds.map((id) => (
                  <FavouriteTeam key={id} id={id} onRemove={() => toggleFavoriteTeam(id)} />
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="col-span-4">
          <div className="card">
            <div className="card-header">
              <div className="card-icon"><Trophy className="w-5 h-5" /></div>
              <div>
                <h2 className="card-title">Favourite leagues</h2>
                <p className="card-desc">Standings and fixtures</p>
              </div>
            </div>
            {!ready ? <LoadingSpinner /> : leagueCodes.length === 0 ? (
              <Empty text="No favourite leagues yet." hint="Open a league and press “Add to favourites”." href="/leagues" cta="Browse leagues" />
            ) : (
              <FavouriteLeagues codes={leagueCodes} onRemove={toggleFavoriteLeague} />
            )}
          </div>
          <p className="text-xs text-text-muted px-1">
            Alerts for new picks and value bets are set in <Link href="/settings" className="text-brand hover:underline">Settings → Notifications</Link>.
          </p>
        </div>
      </div>
    </>
  );
}

function FavouriteTeam({ id, onRemove }: { id: number; onRemove: () => void }) {
  const { settings } = useSettings();
  const [team, fixtures] = useQueries({
    queries: [
      { queryKey: ['teams', id], queryFn: () => teamsApi.getById(id) },
      { queryKey: ['teams', id, 'fixtures'], queryFn: () => teamsApi.getFixtures(id) },
    ],
  });
  const t: any = team.data;
  const next: any = fixtures.data?.upcoming_matches?.[0];
  if (team.isError) {
    return (
      <div className="flex items-center justify-between p-4 bg-surface rounded-lg border border-border-dim text-sm text-text-muted">
        This team is no longer available.
        <button onClick={onRemove} className="btn btn-secondary btn-sm">Remove</button>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-4 p-4 bg-surface rounded-lg border border-border-dim">
      {t?.logo_url ? (
        <img src={t.logo_url} alt="" className="w-10 h-10 object-contain" />
      ) : (
        <div className="w-10 h-10 rounded-lg bg-brand/10 flex items-center justify-center text-brand font-bold">{t?.name?.charAt(0) || '·'}</div>
      )}
      <div className="flex-1 min-w-0">
        <Link href={`/teams/${id}`} className="font-semibold text-text hover:text-brand truncate block">{t?.name || 'Loading…'}</Link>
        <div className="text-sm text-text-muted">{t?.league?.name || t?.league_name || ''}</div>
      </div>
      <div className="text-right text-sm">
        <div className="text-xs text-text-muted mb-1">Next match</div>
        {fixtures.isLoading ? <span className="text-text-muted">…</span> : next ? (
          <Link href={`/matches/${next.id}`} className="text-text-secondary hover:text-brand flex items-center gap-1 justify-end">
            <Calendar className="w-3 h-3" />
            {next.home_team_name} v {next.away_team_name} · {formatDateWithPreset(next.match_date, settings.dateFormat)}
            {(next.kickoff_at || next.kickoff_time) && ` ${formatKickoff(next.kickoff_at, next.kickoff_time, settings.timezone)}`}
          </Link>
        ) : <span className="text-text-muted">No fixture scheduled yet</span>}
      </div>
      <button onClick={onRemove} className="btn btn-icon btn-secondary" aria-label={`Remove ${t?.name || 'team'} from favourites`}>
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

function FavouriteLeagues({ codes, onRemove }: { codes: string[]; onRemove: (code: string) => void }) {
  const { data: leagues = [], isLoading } = useQuery({
    queryKey: ['leagues', { page_size: 100 }],
    queryFn: () => leaguesApi.getAll(),
  });
  if (isLoading) return <LoadingSpinner />;
  const byCode = new Map(leagues.map((l: any) => [l.code, l]));
  return (
    <div className="space-y-3">
      {codes.map((code) => {
        const l: any = byCode.get(code);
        return (
          <div key={code} className="flex items-center gap-3 p-4 bg-surface rounded-lg border border-border-dim">
            <Link href={`/leagues/${code}`} className="flex-1 min-w-0 hover:text-brand">
              <div className="font-semibold text-text truncate">{l?.name || code}</div>
              <div className="text-xs text-text-muted">{l?.country || ''}</div>
            </Link>
            <button onClick={() => onRemove(code)} className="btn btn-icon btn-secondary" aria-label={`Remove ${l?.name || code} from favourites`}>
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function Empty({ text, hint, href, cta }: { text: string; hint: string; href: string; cta: string }) {
  return (
    <div className="text-center py-10">
      <div className="card-icon w-14 h-14 mx-auto mb-3"><Star className="w-7 h-7" /></div>
      <p className="font-semibold text-text mb-1">{text}</p>
      <p className="text-text-muted text-sm max-w-sm mx-auto mb-4">{hint}</p>
      <Link href={href} className="btn btn-primary">{cta}</Link>
    </div>
  );
}
