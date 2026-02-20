'use client';

import { useState } from 'react';
import { useDailyPicks } from '@/hooks/useApi';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ProbabilityBar } from '@/components/ui/ProbabilityBar';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AIEnhancement } from '@/components/predictions/AIEnhancement';
import { formatProbability, getOutcomeLabel } from '@/lib/utils';
import { Trophy, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface DailyPicksProps {
  date?: string; // Format: YYYY-MM-DD
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
          Fixtures are synced from data providers. Future matches may not be available yet.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {data.picks.map((pick: any, index: number) => (
        <PickCard key={index} pick={pick} />
      ))}
    </div>
  );
}

function PickCard({ pick }: { pick: any }) {
  const prediction = pick.prediction;
  const match = pick.match;

  return (
    <div className="p-3 sm:p-4 rounded-lg bg-slate-800/50 hover:bg-slate-800/70 transition-colors">
      {/* Clickable match info section */}
      <Link href={`/matches/${match.id}`} className="block">
        {/* League & Time */}
        <div className="flex items-center justify-between mb-2 sm:mb-3">
          <span className="text-[10px] sm:text-xs text-slate-400 truncate max-w-[60%]">{match.league}</span>
          <span className="text-[10px] sm:text-xs text-slate-400">{match.time || 'TBD'}</span>
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
            <p className="font-medium text-white text-xs sm:text-sm truncate">{match.home_team}</p>
          </div>
          <div className="px-2 sm:px-4 text-slate-500 text-[10px] sm:text-sm flex-shrink-0">vs</div>
          <div className="flex-1 flex items-center justify-end gap-1.5 sm:gap-2 min-w-0">
            <p className="font-medium text-white text-xs sm:text-sm truncate">{match.away_team}</p>
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
              <span className="truncate max-w-[80px] sm:max-w-none">
                {prediction.outcome === 'HOME' || prediction.outcome === 'H'
                  ? match.home_team
                  : prediction.outcome === 'AWAY' || prediction.outcome === 'A'
                  ? match.away_team
                  : 'Draw'}
              </span>
            </Badge>
            <span className="text-[10px] sm:text-sm text-slate-400 flex-shrink-0">
              {formatProbability(prediction.confidence)}
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
