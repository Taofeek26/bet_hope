'use client';

import { Star, Trophy, Calendar, Bell, Plus } from 'lucide-react';
import Link from 'next/link';

export default function FavoritesPage() {
  // In a real app, this would come from user state/API
  const favoriteTeams = [
    { id: 1, name: 'Arsenal', league: 'Premier League', nextMatch: 'vs Chelsea - Today 15:00' },
    { id: 2, name: 'Barcelona', league: 'La Liga', nextMatch: 'vs Atletico - Tomorrow 20:00' },
    { id: 3, name: 'Bayern Munich', league: 'Bundesliga', nextMatch: 'vs Dortmund - Saturday' },
  ];

  const favoriteLeagues = [
    { id: 1, name: 'Premier League', country: 'England', matches: 10 },
    { id: 2, name: 'La Liga', country: 'Spain', matches: 10 },
  ];

  return (
    <>
      <div className="content-header">
        <h1>Favorites</h1>
        <p>Your favorite teams and leagues in one place</p>
      </div>

      <div className="content-grid">
        {/* Favorite Teams */}
        <div className="col-span-8">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Star className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h2 className="card-title">Favorite Teams</h2>
                <p className="card-desc">Teams you're following</p>
              </div>
              <button className="btn btn-secondary btn-sm">
                <Plus className="w-4 h-4" />
                Add Team
              </button>
            </div>

            {favoriteTeams.length === 0 ? (
              <EmptyFavorites type="teams" />
            ) : (
              <div className="space-y-3">
                {favoriteTeams.map((team) => (
                  <div
                    key={team.id}
                    className="flex items-center gap-4 p-4 bg-surface rounded-lg border border-border-dim"
                  >
                    <div className="w-12 h-12 rounded-lg bg-brand/10 flex items-center justify-center">
                      <Trophy className="w-6 h-6 text-brand" />
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-text">{team.name}</div>
                      <div className="text-sm text-text-muted">{team.league}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-text-muted mb-1">Next Match</div>
                      <div className="text-sm text-text-sec flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {team.nextMatch}
                      </div>
                    </div>
                    <button className="btn btn-icon btn-secondary">
                      <Bell className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Favorite Leagues */}
        <div className="col-span-4">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Trophy className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Favorite Leagues</h2>
                <p className="card-desc">Leagues you follow</p>
              </div>
            </div>

            {favoriteLeagues.length === 0 ? (
              <EmptyFavorites type="leagues" />
            ) : (
              <div className="space-y-3">
                {favoriteLeagues.map((league) => (
                  <Link
                    key={league.id}
                    href={`/leagues/${league.id}`}
                    className="block p-4 bg-surface rounded-lg border border-border-dim hover:border-brand transition-colors"
                  >
                    <div className="font-semibold text-text">{league.name}</div>
                    <div className="text-xs text-text-muted mt-1">
                      {league.country} • {league.matches} matches this week
                    </div>
                  </Link>
                ))}
              </div>
            )}

            <button className="btn btn-outline w-full mt-4">
              <Plus className="w-4 h-4" />
              Add League
            </button>
          </div>

          {/* Notifications Card */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Bell className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Notifications</h2>
              </div>
            </div>
            <div className="space-y-3">
              <label className="flex items-center justify-between p-3 bg-surface rounded-lg">
                <span className="text-sm text-text">Match Start</span>
                <input type="checkbox" defaultChecked className="toggle" />
              </label>
              <label className="flex items-center justify-between p-3 bg-surface rounded-lg">
                <span className="text-sm text-text">New Predictions</span>
                <input type="checkbox" defaultChecked className="toggle" />
              </label>
              <label className="flex items-center justify-between p-3 bg-surface rounded-lg">
                <span className="text-sm text-text">Value Bets</span>
                <input type="checkbox" defaultChecked className="toggle" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function EmptyFavorites({ type }: { type: 'teams' | 'leagues' }) {
  return (
    <div className="text-center py-12">
      <div className="card-icon w-16 h-16 mx-auto mb-4">
        <Star className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold text-text mb-2">No Favorite {type === 'teams' ? 'Teams' : 'Leagues'}</h3>
      <p className="text-text-muted text-sm max-w-sm mx-auto mb-4">
        Add {type} to your favorites to quickly access their matches and predictions.
      </p>
      <button className="btn btn-primary">
        <Plus className="w-4 h-4" />
        Add {type === 'teams' ? 'Team' : 'League'}
      </button>
    </div>
  );
}
