'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useQueries } from '@tanstack/react-query';
import { Wallet, Trash2 } from 'lucide-react';
import { matchesApi } from '@/lib/api';
import { useMyBets, legResult, betResult, type LegResult } from '@/lib/mybets';
import { bookmakerById } from '@/lib/bookmakers';
import { useAuth } from '@/lib/auth';

const naira = (n: number) => `₦${Math.round(n).toLocaleString()}`;
const ICON: Record<LegResult, string> = { won: '✅', lost: '❌', void: '➖', pending: '⏳' };

/**
 * My bets (Phase 6): what you staked at your bookmaker and how it went,
 * settled from the final scores. Kept on this device only.
 */
export default function MyBetsPage() {
  const { bets, remove, weeklyLimit, setWeeklyLimit } = useMyBets();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  const list = ready ? bets : [];

  const matchIds = useMemo(() => Array.from(new Set(list.flatMap((b) => b.selections.map((s) => s.matchId)))), [list]);
  const results = useQueries({
    queries: matchIds.map((id) => ({
      queryKey: ['match', id],
      queryFn: () => matchesApi.getById(id),
      staleTime: 10 * 60 * 1000,
    })),
  });
  const byId = new Map(results.map((r, i) => [matchIds[i], r.data as any]));

  const rows = list.map((b) => {
    const legs = b.selections.map((s) => {
      const m = byId.get(s.matchId);
      return { s, m, r: legResult(s.key, m?.home_score, m?.away_score, m?.status) };
    });
    const status = betResult(legs.map((l) => l.r));
    const returned = status === 'won' ? b.stake * b.odds : status === 'void' ? b.stake : 0;
    return { b, legs, status, profit: status === 'pending' ? 0 : returned - b.stake };
  });
  const settled = rows.filter((r) => r.status !== 'pending');
  const staked = settled.reduce((a, r) => a + r.b.stake, 0);
  const profit = settled.reduce((a, r) => a + r.profit, 0);
  const won = settled.filter((r) => r.status === 'won').length;
  const weekAgo = Date.now() - 7 * 86400000;
  const stakedThisWeek = list.filter((b) => Date.parse(b.placedAt) >= weekAgo).reduce((a, b) => a + b.stake, 0);

  return (
    <>
      <div className="content-header">
        <h1>My bets</h1>
        <p>Bets you placed at your bookmaker, settled from the final scores. <SavedWhere /></p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <Stat label="Profit / loss" value={`${profit >= 0 ? '+' : '−'}${naira(Math.abs(profit))}`} tone={profit >= 0 ? 'good' : 'bad'} />
        <Stat label="Return on stakes" value={staked ? `${((profit / staked) * 100).toFixed(1)}%` : '--'} />
        <Stat label="Bets won" value={settled.length ? `${won} of ${settled.length}` : '--'} />
        <Stat label="Staked this week" value={naira(stakedThisWeek)} tone={weeklyLimit && stakedThisWeek > weeklyLimit ? 'bad' : undefined} />
      </div>

      <div className="card card-compact mb-6 flex flex-wrap items-center gap-3 text-sm">
        <label htmlFor="limit" className="text-text-muted">My weekly limit ₦</label>
        <input id="limit" type="number" min="0" step="500" className="input input-sm w-32"
          value={weeklyLimit ?? ''} placeholder="none"
          onChange={(e) => setWeeklyLimit(e.target.value ? Number(e.target.value) : null)} />
        {weeklyLimit ? (
          stakedThisWeek > weeklyLimit
            ? <span className="text-red-400 text-xs">Over your limit by {naira(stakedThisWeek - weeklyLimit)} this week. Consider stopping until next week.</span>
            : <span className="text-text-muted text-xs">{naira(weeklyLimit - stakedThisWeek)} left this week</span>
        ) : <span className="text-text-muted text-xs">Set a limit and Bet Hope warns you when you go over it.</span>}
      </div>

      {!list.length ? (
        <div className="card text-center py-12">
          <div className="card-icon w-14 h-14 mx-auto mb-3"><Wallet className="w-7 h-7" /></div>
          <p className="font-semibold text-text mb-1">No bets saved yet</p>
          <p className="text-sm text-text-muted max-w-sm mx-auto">After you place a bet at your bookmaker, open the Bet Hope slip and press &ldquo;I placed this bet&rdquo;.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map(({ b, legs, status, profit }) => (
            <div key={b.id} className="card">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-text">
                    {status !== 'pending' && (
                      <span className={`mr-1.5 px-2 py-0.5 rounded text-xs font-bold ${status === 'won' ? 'bg-green-500/20 text-green-500' : status === 'lost' ? 'bg-red-500/20 text-red-400' : 'bg-surface text-text-muted'}`}>
                        {status === 'won' ? 'WON' : status === 'lost' ? 'LOST' : 'VOID'}
                      </span>
                    )}
                    {status === 'pending' && ICON.pending} {legs.length === 1 ? 'Single' : `${legs.length}-fold acca`} · {naira(b.stake)} @ {b.odds.toFixed(2)}
                  </div>
                  <div className="text-xs text-text-muted">
                    {new Date(b.placedAt).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })} · {bookmakerById(b.bookmaker)?.name || b.bookmaker}
                    {b.source === 'extension' && <span className="ml-1 px-1.5 py-0.5 rounded bg-brand/15 text-brand text-[10px]">via extension</span>}
                    {b.ticketId && <> · ticket {b.ticketId}</>}
                    {b.bookingCode && <> · code {b.bookingCode}</>}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className={`text-sm font-bold ${status === 'won' ? 'text-green-500' : status === 'lost' ? 'text-red-400' : 'text-text-muted'}`}>
                    {status === 'pending' ? `returns ${naira(b.stake * b.odds)}` : `${profit >= 0 ? '+' : '−'}${naira(Math.abs(profit))}`}
                  </div>
                  <button onClick={() => { if (confirm('Delete this bet from My bets?')) remove(b.id); }} className="text-text-muted hover:text-red-500 mt-1" aria-label="Delete bet">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <ul className="space-y-1">
                {legs.map(({ s, m, r }) => (
                  <li key={`${s.matchId}-${s.key}`} className="text-xs flex justify-between gap-2">
                    <Link href={`/matches/${s.matchId}`} className="min-w-0 truncate hover:text-brand">
                      {ICON[r]} <span className="text-text">{s.label}</span> <span className="text-text-muted">· {s.match}</span>
                    </Link>
                    <span className="text-text-muted flex-shrink-0">{m?.status === 'finished' ? `${m.home_score}-${m.away_score}` : ''}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
      <p className="text-[11px] text-text-muted mt-4">18+. Bet only what you can afford to lose. If betting stops being fun, take a break.</p>
    </>
  );
}

function SavedWhere() {
  const { user, syncing } = useAuth();
  return user
    ? <>Saved to your account ({user.email}).{syncing && <span className="text-brand"> Loading your bets from your account…</span>}</>
    : <>Saved on this device only. <Link href="/account" className="text-brand hover:underline">Sign in</Link> to keep them on any device.</>;
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'good' | 'bad' }) {
  return (
    <div className="card card-compact !mb-0">
      <div className="text-xs text-text-muted">{label}</div>
      <div className={`text-lg font-bold ${tone === 'good' ? 'text-green-500' : tone === 'bad' ? 'text-red-400' : 'text-text'}`}>{value}</div>
    </div>
  );
}
