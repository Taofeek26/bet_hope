'use client';

import { useUpcomingMatches } from '@/hooks/useApi';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ProbabilityBar } from '@/components/ui/ProbabilityBar';
import { formatDate, formatTime, formatRelativeDate } from '@/lib/utils';
import { Calendar, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export function UpcomingMatches() {
  const { data, isLoading, error } = useUpcomingMatches();

  if (isLoading) return <LoadingSpinner />;

  if (error || !data) {
    return (
      <Card>
        <CardBody>
          <p className="text-text-muted text-center py-8">
            Unable to load upcoming matches. Connect the backend to see data.
          </p>
        </CardBody>
      </Card>
    );
  }

  const dates = Object.keys(data.matches_by_date || {}).sort();

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary-500/20">
            <Calendar className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <CardTitle>Upcoming Matches</CardTitle>
            <p className="text-sm text-slate-400">
              {data.total_matches} matches in next 7 days
            </p>
          </div>
        </div>
        <Link
          href="/matches"
          className="flex items-center gap-1 text-sm text-primary-400 hover:text-primary-300"
        >
          View all <ArrowRight className="w-4 h-4" />
        </Link>
      </CardHeader>

      <CardBody>
        {dates.length > 0 ? (
          <div className="space-y-6">
            {dates.slice(0, 3).map((date) => (
              <DateSection
                key={date}
                date={date}
                matches={data.matches_by_date[date]}
              />
            ))}
          </div>
        ) : (
          <p className="text-slate-400 text-center py-8">
            No upcoming matches scheduled.
          </p>
        )}
      </CardBody>
    </Card>
  );
}

function DateSection({ date, matches }: { date: string; matches: any[] }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
        <span>{formatRelativeDate(date)}</span>
        <span className="text-slate-500">-</span>
        <span className="text-slate-500">{formatDate(date, 'EEEE, MMM d')}</span>
      </h3>
      <div className="space-y-3">
        {matches.slice(0, 5).map((match: any) => (
          <MatchRow key={match.id} match={match} />
        ))}
        {matches.length > 5 && (
          <p className="text-sm text-slate-500 pl-2">
            +{matches.length - 5} more matches
          </p>
        )}
      </div>
    </div>
  );
}

function MatchRow({ match }: { match: any }) {
  const hasPrediction = match.has_prediction;

  return (
    <Link href={`/matches/${match.id}`}>
      <div className="p-3 rounded-lg bg-slate-800/30 hover:bg-slate-800/50 transition-colors cursor-pointer">
        <div className="flex items-center gap-4">
          {/* Time */}
          <div className="w-14 text-center">
            <span className="text-sm text-slate-400">
              {formatTime(match.kickoff_time) || 'TBD'}
            </span>
          </div>

          {/* Teams */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white truncate">
                {match.home_team_name}
              </span>
              <span className="text-xs text-slate-500 mx-2">vs</span>
              <span className="text-sm font-medium text-white truncate">
                {match.away_team_name}
              </span>
            </div>
            <span className="text-xs text-slate-500">{match.league_name}</span>
          </div>

          {/* Prediction indicator */}
          <div className="w-20">
            {hasPrediction ? (
              <Badge variant="win">Predicted</Badge>
            ) : (
              <Badge variant="outline">Pending</Badge>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
