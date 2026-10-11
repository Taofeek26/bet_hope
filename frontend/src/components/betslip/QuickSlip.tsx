'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Check } from 'lucide-react';
import { useBetSlip, isInSlip } from '@/lib/betslip';
import { useSettings } from '@/contexts/SettingsContext';

const SIDE = { HOME: ['1', 'home'], DRAW: ['X', 'draw'], AWAY: ['2', 'away'] } as const;

/** "+ Slip" for a prediction's own pick, and a link to all markets (Phase 5). */
export function QuickSlip({ prediction }: { prediction: any }) {
  const { settings } = useSettings();
  const { selections, toggle } = useBetSlip();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  const side = SIDE[prediction.recommended_outcome as keyof typeof SIDE];
  const matchId = prediction.match_id ?? prediction.match?.id;
  if (!ready || !settings.bettingTools || !side || !matchId) return null;

  const m = prediction.match || {};
  const [key, probKey] = side;
  const p = Number(prediction.probabilities?.[probKey]);
  if (!p) return null;
  const home = m.home_team?.name || m.home_team || 'Home';
  const away = m.away_team?.name || m.away_team || 'Away';
  const label = key === 'X' ? 'Draw' : `${key === '1' ? home : away} to win`;
  const added = isInSlip(selections, matchId, key);

  return (
    <div className="flex items-center gap-2 justify-end mt-1">
      <button
        onClick={() => toggle({
          matchId, match: `${home} v ${away}`, kickoff: m.kickoff_at || m.match_date, league: m.league,
          home, away, leagueCode: m.league_code, kickoffAt: m.kickoff_at,
          group: '1X2', key, label, probability: p, fairOdds: Math.round((1 / p) * 100) / 100,
        })}
        className={`btn btn-sm text-xs ${added ? 'btn-primary' : 'btn-secondary'}`}
        aria-pressed={added}
        aria-label={added ? `Remove ${label} from slip` : `Add ${label} to slip`}
      >
        {added ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />} Slip
      </button>
      <Link href={`/matches/${matchId}#markets`} className="text-[11px] text-text-muted hover:text-brand">More markets</Link>
    </div>
  );
}
