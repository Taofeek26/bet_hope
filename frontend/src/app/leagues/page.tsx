'use client';

import { useQuery } from '@tanstack/react-query';
import { Trophy, MapPin, Calendar, ChevronRight, RefreshCw } from 'lucide-react';
import { leaguesApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import Link from 'next/link';

export default function LeaguesPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['leagues'],
    queryFn: () => leaguesApi.getAll(),
  });

  // Ensure leagues is always an array
  const leagues = Array.isArray(data) ? data : [];

  // Group leagues by tier/country
  const tierLabels: Record<string, string> = {
    '1': 'Top 5 European Leagues',
    '2': 'Other Major Leagues',
    '3': 'Second Division',
    '4': 'Other Leagues',
  };

  const groupedLeagues = leagues.length > 0 ? leagues.reduce((acc: any, league: any) => {
    const tier = league.tier || '4';
    if (!acc[tier]) acc[tier] = [];
    acc[tier].push(league);
    return acc;
  }, {}) : {};

  return (
    <>
      <div className="content-header">
        <h1>Leagues</h1>
        <p>Browse all supported leagues and competitions</p>
      </div>

      {/* Stats */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-value">{leagues.length || 20}</div>
          <div className="stat-label">Leagues</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">10+</div>
          <div className="stat-label">Countries</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">500+</div>
          <div className="stat-label">Teams</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">10</div>
          <div className="stat-label">Years Data</div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <p className="text-text-muted mb-4">Failed to load leagues</p>
          <button onClick={() => refetch()} className="btn btn-primary">
            Try Again
          </button>
        </div>
      ) : leagues.length === 0 ? (
        <div className="card text-center py-16">
          <div className="card-icon w-16 h-16 mx-auto mb-4">
            <Trophy className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-semibold text-text mb-2">No Leagues Available</h3>
          <p className="text-text-muted text-sm max-w-sm mx-auto">
            League data will appear here once the backend is connected.
          </p>
        </div>
      ) : (
        Object.entries(groupedLeagues).map(([tier, tierLeagues]: [string, any]) => (
          <div key={tier} className="mb-8">
            <h2 className="text-lg font-semibold text-text mb-4">
              {tierLabels[tier] || `Tier ${tier}`}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {tierLeagues.map((league: any) => (
                <LeagueCard key={league.id} league={league} />
              ))}
            </div>
          </div>
        ))
      )}
    </>
  );
}

function LeagueCard({ league }: { league: any }) {
  return (
    <Link
      href={`/leagues/${league.code}`}
      className="card card-compact hover:border-brand transition-colors group"
    >
      <div className="flex items-center gap-4">
        <div className="card-icon">
          <Trophy className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-text group-hover:text-brand truncate">
            {league.name}
          </h3>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <MapPin className="w-3 h-3" />
            {league.country || 'International'}
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-text-muted group-hover:text-brand" />
      </div>
    </Link>
  );
}

