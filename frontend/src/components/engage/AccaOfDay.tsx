'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Layers, Plus } from 'lucide-react';
import { engageApi } from '@/lib/api';
import { useBetSlip } from '@/lib/betslip';
import { useSettings } from '@/contexts/SettingsContext';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ShareButton } from './ShareButton';

const RESULT_ICON: Record<string, string> = { won: '✅', lost: '❌', void: '➖' };

/**
 * Acca of the day (Phase 6; mixed markets since Phase 8): the 3-4 strongest
 * picks kicking off in the next 36 hours, with the honest chance that ALL of them win, tracked every day.
 */
export function AccaOfDay() {
  const { settings } = useSettings();
  const { toggle, selections, setOpen } = useBetSlip();
  const { data, isLoading } = useQuery({ queryKey: ['acca'], queryFn: engageApi.acca, refetchInterval: 10 * 60 * 1000 });
  const acca = data?.today || data?.latest;
  const isToday = !!data?.today;
  const record = data?.record;

  const addAll = () => {
    for (const leg of acca.legs) {
      if (selections.some((s) => s.matchId === leg.match_id && s.key === leg.key)) continue;
      toggle({
        matchId: leg.match_id, match: leg.match, kickoff: leg.kickoff, kickoffAt: leg.kickoff, league: leg.league,
        home: leg.home, away: leg.away, leagueCode: leg.league_code,
        group: leg.group || '1X2', key: leg.key, label: leg.label,
        probability: leg.probability, fairOdds: leg.fair_odds, bestOdds: leg.best_odds,
      });
    }
    setOpen(true);
  };

  const shareText = acca ? [
    `Bet Hope acca of the day (${acca.date}):`,
    ...acca.legs.map((l: any) => `• ${l.match}: ${l.label} (${Math.round(l.probability * 100)}%)`),
    `All win: ${(acca.combined_probability * 100).toFixed(0)}% · fair odds ${acca.combined_fair_odds.toFixed(2)}`,
  ].join('\n') : '';

  return (
    <div className="card mb-6">
      <div className="card-header">
        <div className="card-icon"><Layers className="w-5 h-5" /></div>
        <div className="min-w-0">
          <h2 className="card-title">Acca of the day</h2>
          <p className="card-desc">
            Strongest picks in the next 36 hours, mixed markets
            {record?.settled ? ` · won ${record.won} of the last ${record.settled}` : ''}
          </p>
        </div>
      </div>
      {isLoading ? <LoadingSpinner /> : !acca ? (
        <p className="text-sm text-text-muted py-4">No acca yet. One is built each morning when at least 3 matches with a 60%+ pick (result, double chance, GG/NG or over/under) kick off within 36 hours. During international breaks there may be none.</p>
      ) : (
        <>
          {!isToday && (
            <p className="text-xs text-text-muted mb-2">
              No acca today (not enough strong picks). Latest: {acca.date}{acca.status !== 'open' ? `, ${acca.status}` : ''}.
            </p>
          )}
          <ul className="space-y-2 mb-3">
            {acca.legs.map((l: any) => (
              <li key={l.match_id} className="flex items-center justify-between gap-2 p-2 bg-surface rounded-lg">
                <div className="min-w-0">
                  <Link href={`/matches/${l.match_id}`} className="text-xs text-text-muted hover:text-brand truncate block">{l.match}</Link>
                  <div className="text-sm text-text font-medium truncate">{l.result ? `${RESULT_ICON[l.result] || ''} ` : ''}{l.label}{l.score ? ` · ${l.score}` : ''}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm text-text">{Math.round(l.probability * 100)}%</div>
                  <div className="text-[11px] text-text-muted">fair {l.fair_odds.toFixed(2)}{l.best_odds ? ` · best ${l.best_odds.toFixed(2)}` : ''}</div>
                </div>
              </li>
            ))}
          </ul>
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <div className="p-2 bg-surface rounded">
              <div className="text-text-muted">Chance all win</div>
              <div className="text-text font-semibold text-base">{(acca.combined_probability * 100).toFixed(0)}%</div>
            </div>
            <div className="p-2 bg-surface rounded">
              <div className="text-text-muted">Fair total odds</div>
              <div className="text-text font-semibold text-base">{acca.combined_fair_odds.toFixed(2)}{acca.combined_best_odds ? <span className="text-xs text-text-muted font-normal"> · best {acca.combined_best_odds.toFixed(2)}</span> : null}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {isToday && acca.status === 'open' && settings.bettingTools && (
              <button onClick={addAll} className="btn btn-primary btn-sm"><Plus className="w-4 h-4" /> Add all to slip</button>
            )}
            <ShareButton text={shareText} url={typeof window !== 'undefined' ? `${window.location.origin}/` : undefined} />
          </div>
          <p className="text-[10px] text-text-muted mt-2">Every leg must win. The chance shown is the model&apos;s, multiplied across legs. 18+ · bet responsibly.</p>
        </>
      )}
    </div>
  );
}
