'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { Trophy, MapPin, Calendar, ArrowLeft, TrendingUp, Target } from 'lucide-react';
import { teamsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import Link from 'next/link';

export default function TeamDetailPage() {
  const params = useParams();
  const teamId = Number(params.id);

  const { data: team, isLoading: teamLoading, error: teamError } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => teamsApi.getById(teamId),
    enabled: !!teamId,
  });

  const { data: fixtures, isLoading: fixturesLoading } = useQuery({
    queryKey: ['team-fixtures', teamId],
    queryFn: () => teamsApi.getFixtures(teamId),
    enabled: !!teamId,
  });

  const { data: stats } = useQuery({
    queryKey: ['team-stats', teamId],
    queryFn: () => teamsApi.getStats(teamId),
    enabled: !!teamId,
  });

  if (teamLoading) {
    return (
      <div className="flex justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  if (teamError || !team) {
    return (
      <div className="card text-center py-12">
        <p className="text-text-muted mb-4">Team not found</p>
        <Link href="/leagues" className="btn btn-primary">
          Back to Leagues
        </Link>
      </div>
    );
  }

  const currentStats = stats?.seasons?.[0];

  return (
    <>
      {/* Back Button */}
      <Link href="/leagues" className="inline-flex items-center gap-2 text-text-muted hover:text-text mb-4">
        <ArrowLeft className="w-4 h-4" />
        Back to Leagues
      </Link>

      {/* Team Header */}
      <div className="card mb-6">
        <div className="flex items-center gap-6">
          {team.logo_url ? (
            <img src={team.logo_url} alt={team.name} className="w-20 h-20 object-contain" />
          ) : (
            <div className="w-20 h-20 rounded-xl bg-brand/10 flex items-center justify-center">
              <span className="text-3xl font-bold text-brand">{team.name?.charAt(0)}</span>
            </div>
          )}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-text">{team.name}</h1>
            <div className="flex items-center gap-4 mt-2 text-text-muted">
              <span className="flex items-center gap-1">
                <Trophy className="w-4 h-4" />
                {team.league_name || 'League'}
              </span>
              {team.stadium && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {team.stadium}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      {currentStats && (
        <div className="stats-grid mb-6">
          <div className="stat-card">
            <div className="stat-value">{currentStats.matches_played || 0}</div>
            <div className="stat-label">Played</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{currentStats.wins || 0}</div>
            <div className="stat-label">Wins</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{currentStats.draws || 0}</div>
            <div className="stat-label">Draws</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{currentStats.losses || 0}</div>
            <div className="stat-label">Losses</div>
          </div>
        </div>
      )}

      <div className="content-grid">
        {/* Upcoming Matches */}
        <div className="col-span-6">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Upcoming Matches</h2>
                <p className="card-desc">Next fixtures</p>
              </div>
            </div>

            {fixturesLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : fixtures?.upcoming_matches && fixtures.upcoming_matches.length > 0 ? (
              <div className="space-y-3">
                {fixtures.upcoming_matches.slice(0, 5).map((match: any) => {
                  const homeName = match.home_team_name || match.home_team?.name;
                  const awayName = match.away_team_name || match.away_team?.name;
                  const homeLogo = match.home_team_logo || match.home_team?.logo_url;
                  const awayLogo = match.away_team_logo || match.away_team?.logo_url;

                  return (
                    <Link
                      key={match.id}
                      href={`/matches/${match.id}`}
                      className="block p-3 bg-surface rounded-lg hover:bg-input transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-1">
                            {homeLogo ? (
                              <img src={homeLogo} alt={homeName} className="w-5 h-5 object-contain" />
                            ) : (
                              <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                                {homeName?.charAt(0)}
                              </div>
                            )}
                            <span className="text-sm font-medium text-text">{homeName}</span>
                          </div>
                          <span className="text-xs text-text-muted">vs</span>
                          <div className="flex items-center gap-1">
                            {awayLogo ? (
                              <img src={awayLogo} alt={awayName} className="w-5 h-5 object-contain" />
                            ) : (
                              <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                                {awayName?.charAt(0)}
                              </div>
                            )}
                            <span className="text-sm font-medium text-text">{awayName}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-text-muted">{match.match_date}</span>
                          <span className="badge badge-outline">Scheduled</span>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-text-muted">
                No upcoming matches
              </div>
            )}
          </div>
        </div>

        {/* Recent Results */}
        <div className="col-span-6">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <TrendingUp className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Recent Results</h2>
                <p className="card-desc">Last 5 matches</p>
              </div>
            </div>

            {fixturesLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : fixtures?.past_matches && fixtures.past_matches.length > 0 ? (
              <div className="space-y-3">
                {fixtures.past_matches.slice(0, 5).map((match: any) => {
                  const isHome = match.home_team_id === teamId || match.home_team?.id === teamId;
                  const teamScore = isHome ? match.home_score : match.away_score;
                  const oppScore = isHome ? match.away_score : match.home_score;
                  const result = teamScore > oppScore ? 'W' : teamScore < oppScore ? 'L' : 'D';
                  const resultColor = result === 'W' ? 'badge-win' : result === 'L' ? 'badge-loss' : 'badge-draw';
                  const homeName = match.home_team_name || match.home_team?.name;
                  const awayName = match.away_team_name || match.away_team?.name;
                  const homeLogo = match.home_team_logo || match.home_team?.logo_url;
                  const awayLogo = match.away_team_logo || match.away_team?.logo_url;

                  return (
                    <Link
                      key={match.id}
                      href={`/matches/${match.id}`}
                      className="block p-3 bg-surface rounded-lg hover:bg-input transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-1">
                            {homeLogo ? (
                              <img src={homeLogo} alt={homeName} className="w-5 h-5 object-contain" />
                            ) : (
                              <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                                {homeName?.charAt(0)}
                              </div>
                            )}
                            <span className="text-sm font-medium text-text">{homeName}</span>
                          </div>
                          <span className="text-xs text-text-muted">vs</span>
                          <div className="flex items-center gap-1">
                            {awayLogo ? (
                              <img src={awayLogo} alt={awayName} className="w-5 h-5 object-contain" />
                            ) : (
                              <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                                {awayName?.charAt(0)}
                              </div>
                            )}
                            <span className="text-sm font-medium text-text">{awayName}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-text-muted">{match.match_date}</span>
                          <span className="text-sm font-bold text-text">
                            {match.home_score} - {match.away_score}
                          </span>
                          <span className={`badge ${resultColor}`}>{result}</span>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-text-muted">
                No recent matches
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
