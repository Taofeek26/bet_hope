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
  const { data: leagues } = useQuery<any>({
    queryKey: ['leagues'],
    queryFn: () => leaguesApi.getAll(),
  });

  const { data, isLoading, error, refetch } = useQuery<any>({
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
      <div className="card card-compact mb-4 sm:mb-6">
        <div className="flex items-center justify-between flex-wrap gap-2 sm:gap-4">
          <div className="flex gap-1 sm:gap-2 flex-wrap">
            <button
              onClick={() => setView('upcoming')}
              className={`btn btn-sm text-xs sm:text-sm ${view === 'upcoming' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span className="hidden xs:inline">Upcoming</span>
              <span className="xs:hidden">Soon</span>
            </button>
            <button
              onClick={() => setView('live')}
              className={`btn btn-sm text-xs sm:text-sm ${view === 'live' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Clock className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              Live
            </button>
            <button
              onClick={() => setView('results')}
              className={`btn btn-sm text-xs sm:text-sm ${view === 'results' ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Trophy className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span className="hidden xs:inline">Results</span>
              <span className="xs:hidden">Done</span>
            </button>
          </div>
          <button onClick={() => refetch()} className="btn btn-secondary btn-sm text-xs sm:text-sm">
            <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {/* Filters - shown for results view */}
        {view === 'results' && (
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-muted" />
              <span className="text-xs sm:text-sm text-text-muted">Filters:</span>
            </div>

            <div className="flex flex-wrap gap-3 sm:gap-4">
              {/* Days Filter */}
              <div className="flex items-center gap-2">
                <label className="text-xs sm:text-sm text-text-muted">Days:</label>
                <select
                  value={selectedDays}
                  onChange={(e) => setSelectedDays(Number(e.target.value))}
                  className="input input-sm w-20 sm:w-24 text-xs sm:text-sm"
                >
                  <option value={1}>1 day</option>
                  <option value={3}>3 days</option>
                  <option value={7}>7 days</option>
                  <option value={14}>14 days</option>
                  <option value={30}>30 days</option>
                </select>
              </div>

              {/* League Filter */}
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <label className="text-xs sm:text-sm text-text-muted flex-shrink-0">League:</label>
                <select
                  value={selectedLeague}
                  onChange={(e) => setSelectedLeague(e.target.value)}
                  className="input input-sm flex-1 min-w-0 max-w-[180px] sm:w-48 text-xs sm:text-sm"
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
  const homeLogo = match.home_team?.logo_url || match.home_team_logo;
  const awayLogo = match.away_team?.logo_url || match.away_team_logo;
  const leagueName = match.league_name || match.league?.name || '';

  // Check prediction verification for finished matches
  const prediction = match.prediction;
  const verification = prediction?.result_verification;
  const hasVerification = isFinished && verification && verification.actual_score;
  const isCorrect = verification?.is_correct;

  return (
    <Link href={`/matches/${match.id}`} className={`match-card hover:border-brand/50 transition-colors flex-col sm:flex-row ${hasVerification ? (isCorrect ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500') : ''}`}>
      {/* Teams row */}
      <div className="match-teams flex-1 w-full sm:w-auto">
        <div className="match-team flex-1 sm:flex-initial justify-start">
          {homeLogo ? (
            <img src={homeLogo} alt={homeTeam} className="w-5 h-5 sm:w-6 sm:h-6 object-contain flex-shrink-0" />
          ) : (
            <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-surface flex items-center justify-center text-[10px] sm:text-xs font-bold text-text-muted flex-shrink-0">
              {homeTeam.charAt(0)}
            </div>
          )}
          <span className="text-text font-medium text-xs sm:text-sm truncate">{homeTeam}</span>
        </div>
        <span className="match-vs text-[10px] sm:text-xs flex-shrink-0">vs</span>
        <div className="match-team flex-1 sm:flex-initial justify-end sm:justify-start">
          <span className="text-text font-medium text-xs sm:text-sm truncate sm:hidden">{awayTeam}</span>
          {awayLogo ? (
            <img src={awayLogo} alt={awayTeam} className="w-5 h-5 sm:w-6 sm:h-6 object-contain flex-shrink-0" />
          ) : (
            <div className="w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-surface flex items-center justify-center text-[10px] sm:text-xs font-bold text-text-muted flex-shrink-0">
              {awayTeam.charAt(0)}
            </div>
          )}
          <span className="text-text font-medium text-xs sm:text-sm truncate hidden sm:block">{awayTeam}</span>
        </div>
      </div>

      {/* Score/Time and Prediction row - stacks on mobile */}
      <div className="flex items-center justify-between w-full sm:w-auto gap-3 sm:gap-4 pt-2 sm:pt-0 border-t sm:border-t-0 border-border-dim mt-2 sm:mt-0">
        <div className="text-center min-w-[70px] sm:min-w-[100px]">
          {isFinished ? (
            <div className="text-base sm:text-xl font-bold text-text">
              {match.home_score} - {match.away_score}
            </div>
          ) : isLive ? (
            <div className="badge badge-live text-[10px] sm:text-xs">LIVE</div>
          ) : (
            <div className="text-xs sm:text-sm text-text-muted">
              <div className="truncate">{match.kickoff_time || match.match_date || 'TBD'}</div>
              {leagueName && <div className="text-[10px] sm:text-xs truncate max-w-[80px] sm:max-w-none">{leagueName}</div>}
            </div>
          )}
        </div>

        <div className="match-prediction min-w-[90px] sm:min-w-[120px] flex-row sm:flex-col items-center sm:items-end">
          {prediction && (
            <div className="flex items-center gap-1.5 sm:gap-2">
              {hasVerification && (
                <div className={`w-5 h-5 sm:w-6 sm:h-6 rounded-full flex items-center justify-center ${isCorrect ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                  {isCorrect ? <Check className="w-3 h-3 sm:w-4 sm:h-4 text-green-500" /> : <X className="w-3 h-3 sm:w-4 sm:h-4 text-red-500" />}
                </div>
              )}
              <div className="flex flex-col items-end">
                <span className="text-[10px] sm:text-xs text-text-muted hidden sm:block">
                  {hasVerification ? (isCorrect ? 'Correct' : 'Wrong') : 'Prediction'}
                </span>
                <span className={`badge text-[10px] sm:text-xs ${hasVerification ? (isCorrect ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500') : 'badge-brand'}`}>
                  {prediction.predicted_outcome === 'H' || prediction.recommended_outcome === 'HOME' ? 'Home' :
                   prediction.predicted_outcome === 'A' || prediction.recommended_outcome === 'AWAY' ? 'Away' : 'Draw'}
                </span>
              </div>
            </div>
          )}
        </div>
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
