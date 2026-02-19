'use client';

import { useLiveMatches } from '@/hooks/useApi';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Radio } from 'lucide-react';
import Link from 'next/link';

export function LiveMatches() {
  const { data, isLoading } = useLiveMatches();

  if (isLoading) return null;

  if (!data || data.count === 0) return null;

  return (
    <Card className="border-red-500/30">
      <CardHeader className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-red-500/20">
          <Radio className="w-5 h-5 text-red-400 animate-pulse" />
        </div>
        <div>
          <CardTitle className="flex items-center gap-2">
            Live Matches
            <Badge variant="live">{data.count} LIVE</Badge>
          </CardTitle>
        </div>
      </CardHeader>

      <CardBody>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.matches.map((match: any) => (
            <LiveMatchCard key={match.id} match={match} />
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function LiveMatchCard({ match }: { match: any }) {
  return (
    <Link href={`/matches/${match.id}`}>
      <div className="p-4 rounded-lg bg-slate-800/50 hover:bg-slate-800 transition-colors cursor-pointer border border-red-500/20">
        {/* League */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-slate-400">
            {match.season?.league?.name || 'League'}
          </span>
          <Badge variant="live">LIVE</Badge>
        </div>

        {/* Score */}
        <div className="flex items-center justify-between">
          <div className="flex-1 flex items-center gap-2">
            {(match.home_team?.logo_url || match.home_team_logo) ? (
              <img src={match.home_team?.logo_url || match.home_team_logo} alt={match.home_team?.name || match.home_team} className="w-6 h-6 object-contain" />
            ) : (
              <div className="w-6 h-6 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                {(match.home_team?.name || match.home_team)?.charAt(0)}
              </div>
            )}
            <p className="font-medium text-white text-sm">
              {match.home_team?.name || match.home_team}
            </p>
          </div>
          <div className="px-4">
            <span className="text-2xl font-bold text-white">
              {match.home_score ?? 0} - {match.away_score ?? 0}
            </span>
          </div>
          <div className="flex-1 flex items-center justify-end gap-2">
            <p className="font-medium text-white text-sm">
              {match.away_team?.name || match.away_team}
            </p>
            {(match.away_team?.logo_url || match.away_team_logo) ? (
              <img src={match.away_team?.logo_url || match.away_team_logo} alt={match.away_team?.name || match.away_team} className="w-6 h-6 object-contain" />
            ) : (
              <div className="w-6 h-6 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                {(match.away_team?.name || match.away_team)?.charAt(0)}
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
