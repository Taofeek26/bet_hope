'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { Calendar, Clock, Trophy, TrendingUp, ArrowLeft, Target } from 'lucide-react';
import { matchesApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import Link from 'next/link';

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = Number(params.id);

  const { data: match, isLoading, error } = useQuery({
    queryKey: ['match', matchId],
    queryFn: () => matchesApi.getById(matchId),
    enabled: !!matchId,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="card text-center py-12">
        <p className="text-text-muted mb-4">Match not found</p>
        <Link href="/matches" className="btn btn-primary">
          Back to Matches
        </Link>
      </div>
    );
  }

  const homeTeam = match.home_team?.name || 'Home Team';
  const awayTeam = match.away_team?.name || 'Away Team';
  const isFinished = match.status === 'finished';
  const isLive = match.status === 'live';

  return (
    <>
      {/* Back Button */}
      <Link href="/matches" className="inline-flex items-center gap-2 text-text-muted hover:text-text mb-4">
        <ArrowLeft className="w-4 h-4" />
        Back to Matches
      </Link>

      {/* Match Header */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-text-muted flex items-center gap-2">
            <Trophy className="w-4 h-4" />
            {match.home_team?.league_name || 'League'}
          </div>
          {isLive && <span className="badge badge-live">LIVE</span>}
          {isFinished && <span className="badge badge-win">FINISHED</span>}
          {!isLive && !isFinished && <span className="badge badge-outline">SCHEDULED</span>}
        </div>

        <div className="flex items-center justify-between py-6">
          <div className="flex-1 text-center">
            <div className="w-16 h-16 rounded-full bg-brand/10 flex items-center justify-center mx-auto mb-3">
              <Trophy className="w-8 h-8 text-brand" />
            </div>
            <h2 className="text-xl font-bold text-text">{homeTeam}</h2>
            <p className="text-sm text-text-muted">Home</p>
          </div>

          <div className="px-8 text-center">
            {isFinished || isLive ? (
              <div className="text-4xl font-bold text-text">
                {match.home_score} - {match.away_score}
              </div>
            ) : (
              <div className="text-2xl font-bold text-text-muted">VS</div>
            )}
            <div className="text-sm text-text-muted mt-2 flex items-center justify-center gap-2">
              <Calendar className="w-4 h-4" />
              {match.match_date}
            </div>
            {match.kickoff_time && (
              <div className="text-sm text-text-muted flex items-center justify-center gap-2">
                <Clock className="w-4 h-4" />
                {match.kickoff_time}
              </div>
            )}
          </div>

          <div className="flex-1 text-center">
            <div className="w-16 h-16 rounded-full bg-brand/10 flex items-center justify-center mx-auto mb-3">
              <Trophy className="w-8 h-8 text-brand" />
            </div>
            <h2 className="text-xl font-bold text-text">{awayTeam}</h2>
            <p className="text-sm text-text-muted">Away</p>
          </div>
        </div>
      </div>

      <div className="content-grid">
        {/* Prediction */}
        {match.prediction && (
          <div className="col-span-6">
            <div className="card">
              <div className="card-header">
                <div className="card-icon">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="card-title">AI Prediction</h2>
                  <p className="card-desc">Model confidence analysis</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-surface rounded-lg">
                  <div className="text-sm text-text-muted mb-1">Predicted Outcome</div>
                  <div className="text-xl font-bold text-brand">
                    {match.prediction.recommended_outcome === 'HOME' ? homeTeam :
                     match.prediction.recommended_outcome === 'AWAY' ? awayTeam : 'Draw'}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <ProbabilityBox label="Home" value={match.prediction.probabilities?.home} />
                  <ProbabilityBox label="Draw" value={match.prediction.probabilities?.draw} />
                  <ProbabilityBox label="Away" value={match.prediction.probabilities?.away} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Odds */}
        {match.odds && (
          <div className="col-span-6">
            <div className="card">
              <div className="card-header">
                <div className="card-icon">
                  <Target className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="card-title">Market Odds</h2>
                  <p className="card-desc">Current betting odds</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <OddsBox label="Home" odds={match.odds.home_odds} prob={match.odds.implied_probs?.home} />
                <OddsBox label="Draw" odds={match.odds.draw_odds} prob={match.odds.implied_probs?.draw} />
                <OddsBox label="Away" odds={match.odds.away_odds} prob={match.odds.implied_probs?.away} />
              </div>
            </div>
          </div>
        )}

        {/* H2H */}
        {match.h2h && (
          <div className="col-span-12">
            <div className="card">
              <div className="card-header">
                <div className="card-icon">
                  <Trophy className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="card-title">Head to Head</h2>
                  <p className="card-desc">Historical meetings</p>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="p-4 bg-surface rounded-lg text-center">
                  <div className="text-2xl font-bold text-text">{match.h2h.total_matches}</div>
                  <div className="text-xs text-text-muted">Total Matches</div>
                </div>
                <div className="p-4 bg-surface rounded-lg text-center">
                  <div className="text-2xl font-bold text-brand">{match.h2h.home_wins}</div>
                  <div className="text-xs text-text-muted">{homeTeam} Wins</div>
                </div>
                <div className="p-4 bg-surface rounded-lg text-center">
                  <div className="text-2xl font-bold text-text-sec">{match.h2h.draws}</div>
                  <div className="text-xs text-text-muted">Draws</div>
                </div>
                <div className="p-4 bg-surface rounded-lg text-center">
                  <div className="text-2xl font-bold text-blue-500">{match.h2h.away_wins}</div>
                  <div className="text-xs text-text-muted">{awayTeam} Wins</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function ProbabilityBox({ label, value }: { label: string; value?: number }) {
  const percentage = value ? (value * 100).toFixed(1) : '0';
  return (
    <div className="p-4 bg-surface rounded-lg text-center">
      <div className="text-xs text-text-muted mb-1">{label}</div>
      <div className="text-xl font-bold text-text">{percentage}%</div>
    </div>
  );
}

function OddsBox({ label, odds, prob }: { label: string; odds?: string | number; prob?: number }) {
  return (
    <div className="p-4 bg-surface rounded-lg text-center">
      <div className="text-xs text-text-muted mb-1">{label}</div>
      <div className="text-xl font-bold text-brand">{odds || '--'}</div>
      {prob && <div className="text-xs text-text-sec">{(prob * 100).toFixed(1)}%</div>}
    </div>
  );
}
