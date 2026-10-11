'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Check, X } from 'lucide-react';
import { useMyBets, type PlacedBet } from '@/lib/mybets';

/**
 * Receives bets the SportyBet extension saw being placed (Phase 6) and adds
 * them to My bets, then tells the extension they arrived so it can forget them.
 */
export function ExtensionInbox() {
  const upsert = useMyBets((s) => s.upsert);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (e.source !== window || e.data?.source !== 'bethope-ext' || e.data.type !== 'BETS_PLACED') return;
      const bets: PlacedBet[] = e.data.bets || [];
      const ids: string[] = [];
      let added = 0;
      for (const b of bets) {
        if (!b?.id || !Array.isArray(b.selections) || !(b.stake > 0) || !(b.odds > 1)) continue;
        added += upsert({ ...b, source: 'extension', bookmaker: 'sportybet' }) ? 1 : 0;
        ids.push(b.id);
      }
      window.postMessage({ source: 'bethope', type: 'BETS_RECEIVED', ids }, window.location.origin);
      if (added) setToast(`${added} SportyBet ticket${added === 1 ? '' : 's'} saved to My bets`);
    };
    window.addEventListener('message', onMsg);
    // Ask the extension for anything placed while Bet Hope was closed.
    const ask = () => window.postMessage({ source: 'bethope', type: 'GET_PLACED' }, window.location.origin);
    const t = setTimeout(ask, 800);
    document.addEventListener('visibilitychange', ask);
    return () => { clearTimeout(t); window.removeEventListener('message', onMsg); document.removeEventListener('visibilitychange', ask); };
  }, [upsert]);

  if (!toast) return null;
  return <Toast text={toast} href="/my-bets" onClose={() => setToast(null)} tone="good" />;
}

export function Toast({ text, href, onClose, tone, second = false }: { text: string; href?: string; onClose: () => void; tone?: 'good' | 'bad'; second?: boolean }) {
  useEffect(() => { const t = setTimeout(onClose, 9000); return () => clearTimeout(t); }, [onClose]);
  return (
    <div role="status" className={`fixed left-3 right-3 sm:left-auto sm:right-4 sm:w-96 ${second ? 'top-40' : 'top-20'} z-[70] p-3 rounded-xl border shadow-2xl bg-card flex items-start gap-2 ${tone === 'bad' ? 'border-red-500/50' : 'border-brand/50'}`}>
      <Check className={`w-4 h-4 mt-0.5 flex-shrink-0 ${tone === 'bad' ? 'text-red-400' : 'text-brand'}`} />
      <div className="flex-1 text-sm text-text whitespace-pre-line">
        {text}
        {href && <> · <Link href={href} onClick={onClose} className="text-brand hover:underline">View</Link></>}
      </div>
      <button onClick={onClose} aria-label="Dismiss" className="text-text-muted hover:text-text"><X className="w-4 h-4" /></button>
    </div>
  );
}
