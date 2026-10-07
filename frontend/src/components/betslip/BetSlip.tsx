'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Ticket, X, Copy, ExternalLink, Trash2, Check } from 'lucide-react';
import { useBetSlip } from '@/lib/betslip';
import { useSettings } from '@/contexts/SettingsContext';
import { BOOKMAKERS, bookmakerById } from '@/lib/bookmakers';

const pct = (p: number) => `${(p * 100).toFixed(p < 0.1 ? 1 : 0)}%`;
const naira = (n: number) => `₦${Math.round(n).toLocaleString()}`;

/**
 * Bet slip (Phase 5, step 3). Build selections here, type in your
 * bookmaker's prices to see whether the model thinks they're fair, then copy
 * the slip and open your bookmaker to place it there. Nigerian bookmakers
 * have no public API, so Bet Hope can't fill or place the bet for you.
 */
export function BetSlip() {
  const { settings, updateSetting } = useSettings();
  const { selections, open, stake, remove, setYourOdds, setStake, clear, setOpen } = useBetSlip();
  const [ready, setReady] = useState(false);
  const [copied, setCopied] = useState(false);
  const [ext, setExt] = useState(false);
  const [sb, setSb] = useState<{ busy?: boolean; msg?: string; ok?: boolean; misses?: string[] } | null>(null);
  useEffect(() => {
    setReady(true);
    // The desktop extension marks the page when it is installed.
    const check = () => setExt(!!document.documentElement.dataset.bethopeExt);
    check();
    const t = setTimeout(check, 800);
    const onMsg = (e: MessageEvent) => {
      if (e.source !== window || e.data?.source !== 'bethope-ext' || e.data.type !== 'LOAD_SPORTYBET_RESULT') return;
      const r = e.data.result || {};
      // Fill in SportyBet's own prices for the picks it found.
      for (const row of r.report || []) if (row.ok && row.odds) useBetSlip.getState().setYourOdds(row.matchId, row.odds);
      const misses = (r.report || []).filter((row: any) => !row.ok).map((row: any) => `${row.label}: ${row.reason}`);
      setSb(r.ok
        ? { ok: true, msg: `Loaded ${r.loaded} of ${r.total} on SportyBet (code ${r.code}). Enter your stake there and place the bet yourself.`, misses }
        : { ok: false, msg: r.error || 'SportyBet could not be loaded', misses });
    };
    window.addEventListener('message', onMsg);
    return () => { clearTimeout(t); window.removeEventListener('message', onMsg); };
  }, []);

  const loadOnSportyBet = () => {
    setSb({ busy: true, msg: 'Opening SportyBet…' });
    window.postMessage({ source: 'bethope', type: 'LOAD_SPORTYBET', selections: useBetSlip.getState().selections }, window.location.origin);
  };

  if (!ready || !settings.bettingTools) return null;

  const n = selections.length;
  const chance = selections.reduce((a, s) => a * s.probability, 1);
  const fair = selections.reduce((a, s) => a * s.fairOdds, 1);
  const allYours = n > 0 && selections.every((s) => s.yourOdds && s.yourOdds > 1);
  const yours = allYours ? selections.reduce((a, s) => a * (s.yourOdds as number), 1) : null;
  const ev = yours ? chance * yours - 1 : null;
  const chosen = settings.bookmakers.length ? BOOKMAKERS.filter((b) => settings.bookmakers.includes(b.id)) : BOOKMAKERS;
  const bookie = bookmakerById(settings.defaultBookmaker) || chosen[0];

  const slipText = () =>
    [
      `Bet Hope slip: ${n} selection${n === 1 ? '' : 's'}`,
      ...selections.map((s, i) =>
        `${i + 1}. ${s.match}${s.kickoff ? ` (${new Date(s.kickoff).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })})` : ''}: ${s.group} ${s.key} = ${s.label}${s.yourOdds ? ` @ ${s.yourOdds}` : ''}`),
      `Model chance ${pct(chance)} · fair odds ${fair.toFixed(2)}${yours ? ` · your odds ${yours.toFixed(2)}` : ''}`,
    ].join('\n');

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(slipText());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt('Copy your slip:', slipText());
    }
  };

  return (
    <>
      {open && (
        <aside
          className="fixed inset-y-0 right-0 z-50 w-full sm:w-[400px] bg-card border-l border-border shadow-2xl flex flex-col"
          aria-label="Bet slip"
        >
          <div className="flex items-center justify-between p-4 border-b border-border-dim">
            <div className="flex items-center gap-2">
              <Ticket className="w-5 h-5 text-brand" />
              <h2 className="font-semibold text-text">Bet slip</h2>
              <span className="text-xs text-text-muted">{n} selection{n === 1 ? '' : 's'}</span>
            </div>
            <button onClick={() => setOpen(false)} className="btn btn-icon btn-secondary" aria-label="Close bet slip">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {n === 0 ? (
              <div className="text-sm text-text-muted text-center py-10">
                <p className="mb-2">Your slip is empty.</p>
                <p className="text-xs">
                  Open a match and pick a market (Home / Draw / Away, GG, Over 2.5 …), or press
                  &ldquo;+ Slip&rdquo; on a prediction.
                </p>
                <Link href="/predictions" onClick={() => setOpen(false)} className="btn btn-secondary btn-sm mt-4">Browse predictions</Link>
              </div>
            ) : (
              selections.map((s) => {
                const edge = s.yourOdds ? s.probability - 1 / s.yourOdds : null;
                return (
                  <div key={s.matchId} className="p-3 bg-surface rounded-lg border border-border-dim">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <Link href={`/matches/${s.matchId}#markets`} onClick={() => setOpen(false)} className="text-xs text-text-muted hover:text-brand truncate block">
                          {s.match}
                        </Link>
                        <div className="text-sm font-semibold text-text">{s.label}</div>
                        <div className="text-[11px] text-text-muted">
                          {s.group} · model {pct(s.probability)} · fair odds {s.fairOdds.toFixed(2)}
                          {s.bestOdds ? ` · best intl ${s.bestOdds.toFixed(2)}` : ''}
                        </div>
                      </div>
                      <button onClick={() => remove(s.matchId)} className="text-text-muted hover:text-red-500" aria-label={`Remove ${s.label}`}>
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <label className="text-[11px] text-text-muted" htmlFor={`odds-${s.matchId}`}>Your bookmaker&apos;s odds</label>
                      <input
                        id={`odds-${s.matchId}`}
                        type="number" inputMode="decimal" step="0.01" min="1.01" placeholder="e.g. 1.85"
                        value={s.yourOdds ?? ''}
                        onChange={(e) => setYourOdds(s.matchId, e.target.value ? Number(e.target.value) : null)}
                        className="input input-sm w-24 text-xs"
                      />
                      {edge != null && (
                        <span className={`text-[11px] ${edge > 0 ? 'text-green-500' : 'text-red-400'}`}>
                          {edge > 0 ? 'above' : 'below'} fair ({edge > 0 ? '+' : ''}{(edge * 100).toFixed(1)} pts)
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {n > 0 && (
            <div className="border-t border-border-dim p-4 space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 bg-surface rounded">
                  <div className="text-text-muted">Model chance all win</div>
                  <div className="text-text font-semibold">{pct(chance)}</div>
                </div>
                <div className="p-2 bg-surface rounded">
                  <div className="text-text-muted">Fair total odds</div>
                  <div className="text-text font-semibold">{fair.toFixed(2)}</div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <label htmlFor="slip-stake" className="text-text-muted">Stake ₦</label>
                <input id="slip-stake" type="number" min="0" step="100" value={stake}
                  onChange={(e) => setStake(Number(e.target.value) || 0)} className="input input-sm w-28 text-xs" />
                {yours && <span className="text-text-muted">returns {naira(stake * yours)} at odds {yours.toFixed(2)}</span>}
              </div>
              {ev != null ? (
                <p className={`text-xs ${ev > 0 ? 'text-green-500' : 'text-red-400'}`}>
                  At your odds the model expects {ev > 0 ? 'a gain' : 'a loss'} of about {Math.abs(ev * 100).toFixed(1)}% of stake on average.
                  {n > 1 && ' Each extra selection multiplies the bookmaker’s margin.'}
                </p>
              ) : (
                <p className="text-[11px] text-text-muted">Type your bookmaker&apos;s odds for every selection to compare with the model.</p>
              )}

              <div className="flex items-center gap-2">
                <select
                  aria-label="Bookmaker"
                  value={bookie?.id}
                  onChange={(e) => updateSetting('defaultBookmaker', e.target.value)}
                  className="input input-sm text-xs flex-1"
                >
                  {chosen.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
                <button onClick={copy} className="btn btn-secondary btn-sm" aria-label="Copy slip">
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
                <a
                  href={bookie?.url} target="_blank" rel="noopener noreferrer"
                  onClick={() => { copy(); }}
                  className="btn btn-primary btn-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open
                </a>
              </div>
              {settings.bookmakers.includes('sportybet') && (
                ext ? (
                  <div className="space-y-1">
                    <button onClick={loadOnSportyBet} disabled={sb?.busy} className="btn btn-primary btn-sm w-full">
                      <Ticket className="w-4 h-4" /> {sb?.busy ? 'Loading on SportyBet…' : 'Load on SportyBet'}
                    </button>
                    {sb?.msg && !sb.busy && <p className={`text-[11px] ${sb.ok ? 'text-green-500' : 'text-red-400'}`}>{sb.msg}</p>}
                    {!!sb?.misses?.length && <ul className="text-[10px] text-text-muted list-disc pl-4">{sb.misses.map((m) => <li key={m}>{m}</li>)}</ul>}
                  </div>
                ) : null
              )}
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-text-muted">
                  Copies the slip, then opens {bookie?.name}; add the picks and stake there. 18+ · bet only what you can afford to lose.
                </p>
                <button onClick={clear} className="text-[11px] text-text-muted hover:text-red-500 flex items-center gap-1 flex-shrink-0">
                  <Trash2 className="w-3 h-3" /> Clear
                </button>
              </div>
            </div>
          )}
        </aside>
      )}
    </>
  );
}

/**
 * Slip button for the header (replaces the floating button, which covered
 * page content on phones with no way to scroll past it).
 */
export function SlipButton() {
  const { settings } = useSettings();
  const { selections, setOpen } = useBetSlip();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready || !settings.bettingTools) return null;
  const n = selections.length;
  return (
    <button
      onClick={() => setOpen(true)}
      className="btn btn-primary btn-sm h-9 px-3 relative"
      aria-label={`Open bet slip (${n} selection${n === 1 ? '' : 's'})`}
    >
      <Ticket className="w-4 h-4" />
      <span className="hidden sm:inline">Slip</span>
      {n > 0 && <span className="px-1.5 rounded-full bg-bg text-brand text-xs font-bold leading-5">{n}</span>}
    </button>
  );
}
