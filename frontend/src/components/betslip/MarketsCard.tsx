'use client';

import { useEffect, useState } from 'react';
import { Ticket, Plus, Check } from 'lucide-react';
import { useBetSlip, isInSlip } from '@/lib/betslip';
import { useSettings } from '@/contexts/SettingsContext';

interface MarketRow {
  group: string;
  key: string;
  label: string;
  probability: number;
  fair_odds: number;
  best_odds: number | null;
  best_bookmaker: string | null;
  edge: number | null;
  tested: boolean;
}

/** Popular markets for one match, with "add to slip" (Phase 5, step 3). */
export function MarketsCard({ match, markets }: { match: any; markets: MarketRow[] }) {
  const { settings } = useSettings();
  const { selections, toggle } = useBetSlip();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!settings.bettingTools || !markets?.length) return null;

  const groups = markets.reduce<Record<string, MarketRow[]>>((acc, m) => {
    (acc[m.group] ||= []).push(m);
    return acc;
  }, {});
  const home = match.home_team?.name || 'Home';
  const away = match.away_team?.name || 'Away';

  return (
    <div className="card mb-6" id="markets">
      <div className="card-header">
        <div className="card-icon"><Ticket className="w-5 h-5" /></div>
        <div>
          <h2 className="card-title">Markets</h2>
          <p className="card-desc">Model chance and fair odds for popular bets. Add one per match to your slip.</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(groups).map(([group, rows]) => (
          <div key={group}>
            <div className="text-xs font-semibold uppercase tracking-wide text-text-muted mb-2">{group}</div>
            <div className="space-y-1.5">
              {rows.map((m) => {
                const inSlip = ready && isInSlip(selections, match.id, m.key);
                return (
                  <button
                    key={m.key}
                    onClick={() =>
                      toggle({
                        matchId: match.id,
                        match: `${home} v ${away}`,
                        kickoff: match.kickoff_at || match.match_date,
                        league: match.league_name,
                        group: m.group, key: m.key, label: m.label,
                        probability: m.probability, fairOdds: m.fair_odds, bestOdds: m.best_odds,
                      })
                    }
                    aria-pressed={inSlip}
                    className={`w-full flex items-center gap-2 p-2 rounded-lg border text-left transition-colors ${
                      inSlip ? 'border-brand bg-brand/10' : 'border-border-dim bg-surface hover:border-border'
                    }`}
                  >
                    <span className="flex-1 min-w-0">
                      <span className="block text-sm text-text truncate">{m.label}</span>
                      <span className="block text-[11px] text-text-muted">
                        {(m.probability * 100).toFixed(0)}% · fair {m.fair_odds.toFixed(2)}
                        {m.best_odds ? ` · best ${m.best_odds.toFixed(2)}` : ''}
                        {m.edge != null && m.edge > 0.05 ? ' · value' : ''}
                      </span>
                    </span>
                    {inSlip ? <Check className="w-4 h-4 text-brand flex-shrink-0" /> : <Plus className="w-4 h-4 text-text-muted flex-shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-text-muted mt-4">
        Home / draw / away and over/under 2.5 were tested on matches the model never saw. The other goal markets are estimates
        from the same expected-goals model. &ldquo;Fair odds&rdquo; = what the price would be with no bookmaker margin; a bookmaker
        price above it is good value by the model&apos;s reckoning.
      </p>
    </div>
  );
}
