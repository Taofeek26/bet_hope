'use client';

import { useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import { Trophy, MapPin, Calendar, ArrowLeft, TrendingUp } from 'lucide-react';
import { leaguesApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import Link from 'next/link';

export default function LeagueDetailPage() {
  const params = useParams();
  const code = params.code as string;

  const { data: league, isLoading: leagueLoading, error: leagueError } = useQuery<any>({
    queryKey: ['league', code],
    queryFn: () => leaguesApi.getByCode(code),
    enabled: !!code,
  });

  const { data: standings, isLoading: standingsLoading } = useQuery<any>({
    queryKey: ['league-standings', code],
    queryFn: () => leaguesApi.getStandings(code),
    enabled: !!code,
  });

  if (leagueLoading) {
    return (
      <div className="flex justify-center py-20">
        <LoadingSpinner />
      </div>
    );
  }

  if (leagueError || !league) {
    return (
      <div className="card text-center py-12">
        <p className="text-text-muted mb-4">League not found</p>
        <Link href="/leagues" className="btn btn-primary">
          Back to Leagues
        </Link>
      </div>
    );
  }

  return (
    <>
      {/* Back Button */}
      <Link href="/leagues" className="inline-flex items-center gap-2 text-text-muted hover:text-text mb-4">
        <ArrowLeft className="w-4 h-4" />
        Back to Leagues
      </Link>

      {/* League Header */}
      <div className="card mb-6">
        <div className="flex items-center gap-6">
          {league.logo_url ? (
            <img src={league.logo_url} alt={league.name} className="w-20 h-20 object-contain" />
          ) : (
            <div className="w-20 h-20 rounded-xl bg-brand/10 flex items-center justify-center">
              <Trophy className="w-10 h-10 text-brand" />
            </div>
          )}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-text">{league.name}</h1>
            <div className="flex items-center gap-4 mt-2 text-text-muted">
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {league.country}
              </span>
              <span className="badge badge-brand">Tier {league.tier}</span>
              {league.is_active && <span className="badge badge-win">Active</span>}
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-value">{league.seasons_count || 1}</div>
          <div className="stat-label">Seasons</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{league.teams_count || standings?.standings?.length || '--'}</div>
          <div className="stat-label">Teams</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{league.matches_count?.toLocaleString() || '--'}</div>
          <div className="stat-label">Matches</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{league.predictions_count?.toLocaleString() || '--'}</div>
          <div className="stat-label">Predictions</div>
        </div>
      </div>

      {/* Standings */}
      <div className="card">
        <div className="card-header">
          <div className="card-icon">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h2 className="card-title">Standings</h2>
            <p className="card-desc">{standings?.season?.name || 'Current Season'}</p>
          </div>
        </div>

        {standingsLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : standings?.standings && standings.standings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-text-muted border-b border-border">
                  <th className="text-left py-3 px-2">#</th>
                  <th className="text-left py-3 px-2">Team</th>
                  <th className="text-center py-3 px-2">P</th>
                  <th className="text-center py-3 px-2">W</th>
                  <th className="text-center py-3 px-2">D</th>
                  <th className="text-center py-3 px-2">L</th>
                  <th className="text-center py-3 px-2">GD</th>
                  <th className="text-center py-3 px-2">Pts</th>
                </tr>
              </thead>
              <tbody>
                {standings.standings.map((team: any, index: number) => {
                  const teamName = team.team_name || team.team?.name || 'Unknown';
                  const teamLogo = team.team_logo || team.team?.logo_url;

                  return (
                    <tr key={team.team_id || index} className="border-b border-border-dim hover:bg-surface">
                      <td className="py-3 px-2 text-text-muted">{team.position || index + 1}</td>
                      <td className="py-3 px-2">
                        <Link href={`/teams/${team.team_id}`} className="flex items-center gap-2 text-text hover:text-brand">
                          {teamLogo ? (
                            <img src={teamLogo} alt={teamName} className="w-5 h-5 object-contain" />
                          ) : (
                            <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                              {teamName.charAt(0)}
                            </div>
                          )}
                          {teamName}
                        </Link>
                      </td>
                      <td className="text-center py-3 px-2 text-text-sec">{team.matches_played || team.played || 0}</td>
                      <td className="text-center py-3 px-2 text-text-sec">{team.wins || 0}</td>
                      <td className="text-center py-3 px-2 text-text-sec">{team.draws || 0}</td>
                      <td className="text-center py-3 px-2 text-text-sec">{team.losses || 0}</td>
                      <td className="text-center py-3 px-2 text-text-sec">
                        {(team.goals_for || 0) - (team.goals_against || 0)}
                      </td>
                      <td className="text-center py-3 px-2 font-bold text-text">{team.points || 0}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-text-muted">
            No standings data available
          </div>
        )}
      </div>
    </>
  );
}
