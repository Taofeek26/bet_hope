'use client';

import { Clock } from 'lucide-react';
import { useStartingSoon } from '@/hooks/useApi';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { PickList } from './DailyPicks';

/**
 * Starting soon: the first 10 matches kicking off in the next 2 hours, each
 * with its pick across markets (same rule as top picks), soonest first.
 */
export function StartingSoon() {
  const { data, isLoading } = useStartingSoon(2);
  const picks = data?.picks || [];

  return (
    <div className="card mb-6">
      <div className="card-header">
        <div className="card-icon"><Clock className="w-5 h-5" /></div>
        <div className="min-w-0">
          <h2 className="card-title">Starting in the next 2 hours</h2>
          <p className="card-desc">Up to 10 matches, soonest first · best market per match</p>
        </div>
      </div>
      {isLoading ? <LoadingSpinner /> : picks.length ? <PickList picks={picks} /> : (
        <p className="text-sm text-text-muted py-4">No match with a pick kicks off in the next 2 hours.</p>
      )}
    </div>
  );
}
