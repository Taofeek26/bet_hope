'use client';

import { useEffect, useMemo, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { matchesApi } from '@/lib/api';
import { useMyBets, legResult, betResult } from '@/lib/mybets';
import { Toast } from './ExtensionInbox';

const SEEN_KEY = 'bethope_settled_seen';
const naira = (n: number) => `₦${Math.round(n).toLocaleString()}`;

/**
 * Tells you when a saved ticket is decided (Phase 6): "Your SportyBet ticket
 * WON ₦3,200" or "LOST", once per ticket, as an in-app message and, if you
 * allowed notifications, a system alert. Checks only matches that have kicked off.
 */
export function TicketWatcher() {
  const bets = useMyBets((s) => s.bets);
  const [ready, setReady] = useState(false);
  const [toast, setToast] = useState<{ text: string; tone: 'good' | 'bad' } | null>(null);
  useEffect(() => setReady(true), []);

  const seen = useMemo<string[]>(() => {
    if (!ready) return [];
    try { return JSON.parse(localStorage.getItem(SEEN_KEY) || '[]'); } catch { return []; }
  }, [ready, bets]);
  const watch = ready ? bets.filter((b) => !seen.includes(b.id) && Date.now() - Date.parse(b.placedAt) < 21 * 86400000) : [];
  const now = Date.now();
  const ids = Array.from(new Set(watch.flatMap((b) => b.selections
    .filter((s) => !s.kickoffAt || Date.parse(s.kickoffAt) < now)
    .map((s) => s.matchId))));
  const results = useQueries({ queries: ids.map((id) => ({ queryKey: ['match', id], queryFn: () => matchesApi.getById(id), staleTime: 5 * 60 * 1000, refetchInterval: 10 * 60 * 1000 })) });
  const byId = new Map(results.map((r, i) => [ids[i], r.data as any]));
  const signature = results.map((r) => (r.data as any)?.status || '').join(',');

  useEffect(() => {
    if (!ready || !watch.length) return;
    const done: { text: string; tone: 'good' | 'bad' }[] = [];
    const newlySeen: string[] = [];
    for (const b of watch) {
      const legs = b.selections.map((s) => { const m = byId.get(s.matchId); return legResult(s.key, m?.home_score, m?.away_score, m?.status); });
      const st = betResult(legs);
      if (st === 'pending') continue;
      newlySeen.push(b.id);
      const where = b.source === 'extension' ? 'SportyBet ticket' : 'ticket';
      if (st === 'won') done.push({ tone: 'good', text: `🎉 Your ${where} WON: ${naira(b.stake * b.odds)} back on ${naira(b.stake)}` });
      else if (st === 'lost') done.push({ tone: 'bad', text: `Your ${where} lost (${legs.filter((l) => l === 'won').length} of ${legs.length} picks won). Stake ${naira(b.stake)}.` });
      else done.push({ tone: 'good', text: `Your ${where} was void: ${naira(b.stake)} back` });
    }
    if (!newlySeen.length) return;
    try { localStorage.setItem(SEEN_KEY, JSON.stringify([...seen, ...newlySeen].slice(-300))); } catch { /* ignore */ }
    const msg = done.map((d) => d.text).join('\n');
    setToast({ text: msg, tone: done.every((d) => d.tone === 'good') ? 'good' : 'bad' });
    try {
      if ('Notification' in window && Notification.permission === 'granted') {
        navigator.serviceWorker?.getRegistration().then((reg) => {
          if (reg) reg.showNotification('Bet Hope: ticket settled', { body: msg, icon: '/icon-192.png', data: { url: '/my-bets' } });
          else new Notification('Bet Hope: ticket settled', { body: msg, icon: '/icon-192.png' });
        });
      }
    } catch { /* alerts are optional */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, signature, watch.length]);

  if (!toast) return null;
  return <Toast text={toast.text} tone={toast.tone} href="/my-bets" onClose={() => setToast(null)} second />;
}
