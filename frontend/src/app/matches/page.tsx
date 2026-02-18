'use client';

import { useQuery } from '@tanstack/react-query';
import { Calendar, Clock, Trophy, Filter, RefreshCw, ChevronDown, Check, X } from 'lucide-react';
import { matchesApi, leaguesApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useState } from 'react';
import Link from 'next/link';

export default function MatchesPage() {
  const [view, setView] = useState<'upcoming' | 'live' | 'results'>('upcoming');
  const [selectedDays, setSelectedDays] = useState<number>(7);
  const [selectedLeague, setSelectedLeague] = useState<string>('');

  // Fetch leagues for filter
  const { data: leagues } = useQuery({
    queryKey: ['leagues'],
    queryFn: () => leaguesApi.getAll(),
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['matches', view, selectedDays, selectedLeague],
    queryFn: () => {
      if (view === 'live') return matchesApi.getLive();
      if (view === 'results') return matchesApi.getResults({ days: selectedDays, league: selectedLeague || undefined });
      return matchesApi.getUpcoming();
    },
  });

  // Handle different response structures
  const getMatches = () => {
    if (!data) return [];
    if (view === 'live') return data.matches || [];
    if (view === 'results') return data.results || [];
    if (view === 'upcoming' && data.matches_by_date) {
      return Object.values(data.matches_by_date).flat();
    }
    return data.results || data.matches || [];
  };

  const matches = getMatches();

  return (
    <>
      <div className="content-header">
        <h1>Matches</h1>
        <p>Browse upcoming, live, and completed matches</p>
      </div>

      {/* View Toggle */}
      <div className="card card-compact mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex gap-2">
            <button
              onClick={() => setView('upcoming')}
              className={`btn btn-sm ${view === 'upcoming' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Calendar className="w-4 h-4" />
              Upcoming
            </button>
            <button
              onClick={() => setView('live')}
              className={`btn btn-sm ${view === 'live' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Clock className="w-4 h-4" />
              Live
            </button>
            <button
              onClick={() => setView('results')}
              className={`btn btn-sm ${view === 'results' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Trophy className="w-4 h-4" />
              Results
            </button>
          </div>
          <button onClick={() => refetch()} className="btn btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Filters - shown for results view */}
        {view === 'results' && (
          <div className="flex items-center gap-4 mt-4 pt-4 border-t border-border flex-wrap">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-muted" />
              <span className="text-sm text-text-muted">Filters:</span>
            </div>

            {/* Days Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-text-muted">Days:</label>
              <select
                value={selectedDays}
                onChange={(e) => setSelectedDays(Number(e.target.value))}
                className="input input-sm w-24"
              >
                <option value={1}>1 day</option>
                <option value={3}>3 days</option>
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
            </div>

            {/* League Filter */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-text-muted">League:</label>
              <select
                value={selectedLeague}
                onChange={(e) => setSelectedLeague(e.target.value)}
                className="input input-sm w-48"
              >
                <option value="">All Leagues</option>
                {leagues?.map((league: any) => (
                  <option key={league.code} value={league.code}>
                    {league.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Matches List */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <p className="text-text-muted mb-4">Failed to load matches</p>
          <button onClick={() => refetch()} className="btn btn-primary">
            Try Again
          </button>
        </div>
      ) : matches.length === 0 ? (
        <EmptyState view={view} />
      ) : (
        <div className="space-y-3">
          {matches.map((match: any) => (
            <MatchCard key={match.id} match={match} />
          ))}
        </div>
      )}
    </>
  );
}

function MatchCard({ match }: { match: any }) {
  const isLive = match.status === 'live';
  const isFinished = match.status === 'finished';

  // Handle both nested and flat team name formats
  const homeTeam = match.home_team_name || match.home_team?.name || 'Home Team';
  const awayTeam = match.away_team_name || match.away_team?.name || 'Away Team';
  const leagueName = match.league_name || match.league?.name || '';

  // Check prediction verification for finished matches
  const prediction = match.prediction;
  const verification = prediction?.result_verification;
  const hasVerification = isFinished && verification && verification.actual_score;
  const isCorrect = verification?.is_correct;

  return (
    <Link href={`/matches/${match.id}`} className={`match-card hover:border-brand/50 transition-colors ${hasVerification ? (isCorrect ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500') : ''}`}>
      <div className="match-teams flex-1">
        <div className="match-team">
          <span className="text-text font-medium">{homeTeam}</span>
        </div>
        <span className="match-vs">vs</span>
        <div className="match-team">
          <span className="text-text font-medium">{awayTeam}</span>
        </div>
      </div>

      <div className="text-center min-w-[100px]">
        {isFinished ? (
          <div className="text-xl font-bold text-text">
            {match.home_score} - {match.away_score}
          </div>
        ) : isLive ? (
          <div className="badge badge-live">LIVE</div>
        ) : (
          <div className="text-sm text-text-muted">
            <div>{match.kickoff_time || match.match_date || 'TBD'}</div>
            {leagueName && <div className="text-xs">{leagueName}</div>}
          </div>
        )}
      </div>

      <div className="match-prediction min-w-[120px]">
        {prediction && (
          <div className="flex items-center gap-2">
            {hasVerification && (
              <div className={`w-6 h-6 rounded-full flex items-center justify-center ${isCorrect ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                {isCorrect ? <Check className="w-4 h-4 text-green-500" /> : <X className="w-4 h-4 text-red-500" />}
              </div>
            )}
            <div>
              <span className="text-xs text-text-muted">
                {hasVerification ? (isCorrect ? 'Correct' : 'Wrong') : 'Prediction'}
              </span>
              <span className={`badge ${hasVerification ? (isCorrect ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500') : 'badge-brand'}`}>
                {prediction.predicted_outcome === 'H' || prediction.recommended_outcome === 'HOME' ? 'Home' :
                 prediction.predicted_outcome === 'A' || prediction.recommended_outcome === 'AWAY' ? 'Away' : 'Draw'}
              </span>
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}

function EmptyState({ view }: { view: string }) {
  return (
    <div className="card text-center py-16">
      <div className="card-icon w-16 h-16 mx-auto mb-4">
        <Calendar className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold text-text mb-2">
        No {view === 'live' ? 'Live' : view === 'results' ? 'Recent' : 'Upcoming'} Matches
      </h3>
      <p className="text-text-muted text-sm max-w-sm mx-auto">
        {view === 'live'
          ? 'No matches are currently being played.'
          : view === 'results'
          ? 'No recent match results to display.'
          : 'No upcoming matches scheduled.'}
      </p>
    </div>
  );
}
