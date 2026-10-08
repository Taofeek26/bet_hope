'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Zap, Newspaper, TrendingUp, Brain, Trophy, Layers, ExternalLink } from 'lucide-react';
import { engageApi, type FlashItem } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

const KINDS = [
  { key: '', label: 'All' },
  { key: 'news', label: 'Team news' },
  { key: 'odds_move', label: 'Odds moves' },
  { key: 'model_change', label: 'Model' },
  { key: 'results,acca', label: 'Results' },
];

const ICON: Record<FlashItem['kind'], React.ComponentType<{ className?: string }>> = {
  news: Newspaper, odds_move: TrendingUp, model_change: Brain, results: Trophy, acca: Layers,
};

const TAG_STYLE: Record<string, string> = {
  injury: 'bg-red-500/15 text-red-400', suspension: 'bg-red-500/15 text-red-400',
  lineup: 'bg-amber-500/15 text-amber-400', manager: 'bg-amber-500/15 text-amber-400',
  transfer: 'bg-surface text-text-muted', other: 'bg-surface text-text-muted',
};

function ago(iso: string) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m || 1}m ago`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h}h ago` : `${Math.round(h / 24)}d ago`;
}

/**
 * Flash feed (Phase 6): team news, odds moves, model changes and results,
 * newest first. On a match page it shows only that match.
 */
export function FlashFeed({ matchId, limit = 20, title = 'Flash', compact = false }: { matchId?: number; limit?: number; title?: string; compact?: boolean }) {
  const [kind, setKind] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['flash', { matchId, kind, limit }],
    queryFn: () => engageApi.flash({ match: matchId, kind: kind || undefined, limit, hours: matchId ? 24 * 14 : 72 }),
    refetchInterval: 5 * 60 * 1000,
  });
  const items = data?.items || [];
  if (matchId && !isLoading && !items.length) return null; // nothing about this match yet

  return (
    <div className="card mb-6">
      <div className="card-header">
        <div className="card-icon"><Zap className="w-5 h-5" /></div>
        <div className="min-w-0">
          <h2 className="card-title">{title}</h2>
          <p className="card-desc">Team news, odds moves, model changes and results · updated every morning</p>
        </div>
      </div>
      {!matchId && (
        <div className="flex gap-1.5 overflow-x-auto pb-2 mb-2 -mx-1 px-1">
          {KINDS.map((k) => (
            <button key={k.key} onClick={() => setKind(k.key)}
              className={`px-3 py-1 text-xs rounded-full whitespace-nowrap border ${kind === k.key ? 'bg-brand text-bg border-brand' : 'border-border-dim text-text-muted hover:text-text'}`}>
              {k.label}
            </button>
          ))}
        </div>
      )}
      {isLoading ? <LoadingSpinner /> : !items.length ? (
        <p className="text-sm text-text-muted py-6 text-center">Nothing new in the last few days. Flashes arrive with the daily update around 04:15–05:15 UTC.</p>
      ) : (
        <ul className="divide-y divide-border-dim">
          {items.map((f) => {
            const Icon = ICON[f.kind] || Zap;
            return (
              <li key={f.id} className="py-3 flex gap-3">
                <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${f.importance >= 3 ? 'text-brand' : 'text-text-muted'}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start gap-2 flex-wrap">
                    <span className={`text-sm text-text ${f.importance >= 3 ? 'font-semibold' : ''}`}>{f.title}</span>
                    {f.tag && f.tag !== 'other' && (
                      <span className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${TAG_STYLE[f.tag] || 'bg-surface text-text-muted'}`}>{f.tag}</span>
                    )}
                  </div>
                  {!compact && f.body && <p className="text-xs text-text-muted mt-1 whitespace-pre-line break-words">{f.body}</p>}
                  <div className="text-[11px] text-text-muted mt-1 flex items-center gap-2 flex-wrap">
                    <span>{ago(f.published_at)}</span>
                    {f.source && <span>· {f.source}</span>}
                    {f.match && !matchId && <Link href={`/matches/${f.match.id}`} className="text-brand hover:underline">· {f.match.label}</Link>}
                    {f.url && <a href={f.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 hover:text-brand">· read <ExternalLink className="w-3 h-3" /></a>}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
