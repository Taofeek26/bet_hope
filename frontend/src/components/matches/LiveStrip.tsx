'use client';

import Link from 'next/link';
import { useLiveMatches } from '@/hooks/useApi';

/** In-play matches with scores (Phase 6). Hidden when nothing is live. */
export function LiveStrip() {
  const { data } = useLiveMatches();
  const matches: any[] = data?.matches || [];
  if (!matches.length) return null;
  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="card-title flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" /> Live now</h2>
        <span className="text-[11px] text-text-muted">Top leagues · updates every {data?.updated_every_minutes || 5} min</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {matches.map((m) => (
          <Link key={m.id} href={`/matches/${m.id}`} className="flex-shrink-0 w-48 p-3 bg-surface rounded-lg border border-border-dim hover:border-brand/50">
            <div className="text-[10px] text-text-muted mb-1 truncate">{m.league_name} · {m.status === 'halftime' ? 'Half time' : 'Live'}</div>
            <div className="flex justify-between text-sm"><span className="truncate text-text">{m.home_team?.name}</span><span className="font-bold text-text">{m.home_score ?? 0}</span></div>
            <div className="flex justify-between text-sm"><span className="truncate text-text">{m.away_team?.name}</span><span className="font-bold text-text">{m.away_score ?? 0}</span></div>
          </Link>
        ))}
      </div>
    </div>
  );
}
