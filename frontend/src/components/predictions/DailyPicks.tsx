'use client';

import { useState } from 'react';
import { useDailyPicks } from '@/hooks/useApi';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProbabilityBar } from '@/components/ui/ProbabilityBar';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AIEnhancement } from '@/components/predictions/AIEnhancement';
import { formatProbability, getOutcomeLabel, formatKickoff } from '@/lib/utils';
import { useSettings } from '@/contexts/SettingsContext';
import { Trophy, ArrowRight, Plus, Check } from 'lucide-react';
import { useBetSlip, isInSlip } from '@/lib/betslip';
import Link from 'next/link';

interface DailyPicksProps {
  date?: string; // Format: YYYY-MM-DD
}

// The match's pick across markets (Phase 8); older API responses had only 1X2.
function marketOf(pick: any) {
  const { prediction, match } = pick;
  const side = prediction.outcome === 'HOME' ? 'home' : prediction.outcome === 'AWAY' ? 'away' : 'draw';
  return pick.pick || {
    group: '1X2', key: { home: '1', away: '2', draw: 'X' }[side],
    label: side === 'draw' ? 'Draw' : `${side === 'home' ? match.home_team : match.away_team} to win`,
    probability: prediction.confidence, fair_odds: 1 / prediction.confidence, best_odds: null,
  };
}

function selectionOf(pick: any) {
  const { match } = pick;
  const market = marketOf(pick);
  return {
    matchId: match.id, match: `${match.home_team} v ${match.away_team}`, kickoff: match.kickoff_at,
    kickoffAt: match.kickoff_at, league: match.league, leagueCode: match.league_code,
    home: match.home_team, away: match.away_team,
    group: market.group, key: market.key, label: market.label,
    probability: market.probability, fairOdds: market.fair_odds, bestOdds: market.best_odds,
  };
}

export function DailyPicks({ date }: DailyPicksProps) {
  const { data, isLoading, error } = useDailyPicks(date ? { date } : undefined);

  if (isLoading) return <LoadingSpinner />;

  if (!data || !data.picks || data.picks.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-text-muted mb-2">
          No high-confidence picks available for this date.
        </p>
        <p className="text-text-muted text-sm">
          Picks need a fixture where one market (result, double chance, GG/NG or over/under) has a 65%+ chance. Days without fixtures — e.g. international breaks — have none; the numbered dates above show where picks exist.
        </p>
      </div>
    );
  }

  return <PickList picks={data.picks} />;
}

/** Pick cards with "Add all to slip" (top picks, starting soon). */
export function PickList({ picks }: { picks: any[] }) {
  const { settings } = useSettings();
  const { selections, toggle, setOpen } = useBetSlip();
  const open = picks.filter((p: any) => !p.match.kickoff_at || new Date(p.match.kickoff_at) > new Date());
  const missing = open.filter((p: any) => !isInSlip(selections, p.match.id, marketOf(p).key));
  const chance = open.reduce((a: number, p: any) => a * marketOf(p).probability, 1);
  const addAll = () => {
    for (const p of missing) toggle(selectionOf(p));
    setOpen(true);
  };

  return (
    <div className="space-y-4">
      {settings.bettingTools && open.length > 1 && (
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <p className="text-[11px] text-text-muted">
            All {open.length} together win {(chance * 100).toFixed(chance < 0.1 ? 1 : 0)}% of the time.
            {open.length > 4 && ' Fewer picks win far more often.'}
          </p>
          <button onClick={addAll} disabled={!missing.length} className="btn btn-primary btn-sm">
            {missing.length ? <Plus className="w-4 h-4" /> : <Check className="w-4 h-4" />}
            {missing.length ? `Add all ${open.length} to slip` : 'All in slip'}
          </button>
        </div>
      )}
      {picks.map((pick: any) => (
        <PickCard key={pick.match.id} pick={pick} />
      ))}
    </div>
  );
}

function PickCard({ pick }: { pick: any }) {
  const { settings } = useSettings();
  const { selections, toggle } = useBetSlip();
  const prediction = pick.prediction;
  const match = pick.match;
  const market = marketOf(pick);
  const added = isInSlip(selections, match.id, market.key);

  return (
    <div className="blueprint elev-sm hover:bg-surface/70 transition-colors">
      <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
      {/* Clickable match info section */}
      <Link href={`/matches/${match.id}`} className="block">
        {/* League & Time */}
        <div className="flex items-center justify-between mb-2 sm:mb-3">
          <span className="text-[10px] sm:text-xs text-text-secondary truncate max-w-[60%]">{match.league}</span>
          <span className="text-[10px] sm:text-xs text-text-secondary">{formatKickoff(match.kickoff_at, match.time, settings.timezone) || 'TBD'}</span>
        </div>

        {/* Teams */}
        <div className="flex items-center justify-between mb-3 sm:mb-4 gap-2">
          <div className="flex-1 flex items-center gap-1.5 sm:gap-2 min-w-0">
            {match.home_team_logo ? (
              <img src={match.home_team_logo} alt={match.home_team} className="w-5 h-5 sm:w-6 sm:h-6 object-contain flex-shrink-0" />
            ) : (
              <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-brand/10 flex items-center justify-center text-[10px] sm:text-xs font-bold text-brand flex-shrink-0">
                {match.home_team?.charAt(0)}
              </div>
            )}
            <p className="font-medium text-text text-xs sm:text-sm truncate">{match.home_team}</p>
          </div>
          <div className="px-2 sm:px-4 text-text-muted text-[10px] sm:text-sm flex-shrink-0">vs</div>
          <div className="flex-1 flex items-center justify-end gap-1.5 sm:gap-2 min-w-0">
            <p className="font-medium text-text text-xs sm:text-sm truncate">{match.away_team}</p>
            {match.away_team_logo ? (
              <img src={match.away_team_logo} alt={match.away_team} className="w-5 h-5 sm:w-6 sm:h-6 object-contain flex-shrink-0" />
            ) : (
              <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-brand/10 flex items-center justify-center text-[10px] sm:text-xs font-bold text-brand flex-shrink-0">
                {match.away_team?.charAt(0)}
              </div>
            )}
          </div>
        </div>

        {/* Prediction */}
        <div className="flex items-center justify-between mb-2 sm:mb-3 gap-2">
          <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-1">
            <Badge variant={pick.risk === 'low' ? 'win' : 'draw'}>
              <span className="truncate max-w-[140px] sm:max-w-none">{market.label}</span>
            </Badge>
            <span className="text-[10px] sm:text-sm text-text-secondary flex-shrink-0">
              {formatProbability(market.probability)} · fair {market.fair_odds.toFixed(2)}
            </span>
          </div>
          <Badge variant={pick.risk === 'low' ? 'win' : 'draw'}>
            {pick.risk} risk
          </Badge>
        </div>

        {/* Probability Bar */}
        <ProbabilityBar
          homeProb={prediction.probabilities.home}
          drawProb={prediction.probabilities.draw}
          awayProb={prediction.probabilities.away}
        />
      </Link>

      {settings.bettingTools && (
        <div className="flex items-center gap-2 justify-end mt-2">
          <button
            onClick={() => toggle(selectionOf(pick))}
            className={`btn btn-sm text-xs ${added ? 'btn-primary' : 'btn-secondary'}`}
            aria-pressed={added}
            aria-label={added ? `Remove ${market.label} from slip` : `Add ${market.label} to slip`}
          >
            {added ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />} Slip
          </button>
          <Link href={`/matches/${match.id}#markets`} className="text-[11px] text-text-muted hover:text-brand">More markets</Link>
        </div>
      )}

      {/* AI Enhancement - outside the Link to prevent navigation */}
      {prediction.id && (
        <AIEnhancement
          predictionId={prediction.id}
          matchInfo={{
            homeTeam: match.home_team,
            awayTeam: match.away_team,
          }}
        />
      )}
    </div>
  );
}
