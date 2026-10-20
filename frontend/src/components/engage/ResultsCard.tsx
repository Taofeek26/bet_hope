'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Trophy } from 'lucide-react';
import { engageApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ShareButton } from './ShareButton';

/**
 * Yesterday's results (Phase 6): how the top picks did, losses shown as
 * clearly as wins. The honest record is the point.
 */
export function ResultsCard() {
  const { data, isLoading } = useQuery({ queryKey: ['results-yesterday'], queryFn: () => engageApi.results() });
  const day = data?.date ? new Date(`${data.date}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' }) : 'Yesterday';
  const shareText = data?.total
    ? `Bet Hope top picks, ${day}: ${data.won} of ${data.total} won\n` +
      data.picks.slice(0, 10).map((p: any) => `${p.correct ? '✅' : '❌'} ${p.match}: ${p.pick} (${p.score})`).join('\n')
    : '';

  return (
    <div className="card mb-6">
      <div className="card-header">
        <div className="card-icon"><Trophy className="w-5 h-5" /></div>
        <div className="min-w-0">
          <h2 className="card-title">Yesterday&apos;s results</h2>
          <p className="card-desc">Top picks (best market, 65%+), made before kickoff · {day}</p>
        </div>
      </div>
      {isLoading ? <LoadingSpinner /> : !data?.total ? (
        <p className="text-sm text-text-muted py-4">No top picks were played yesterday.</p>
      ) : (
        <>
          <div className="text-2xl font-bold text-text mb-1">{data.won} <span className="text-base font-normal text-text-muted">of {data.total} won</span></div>
          <ul className="divide-y divide-border-dim mb-3">
            {data.picks.slice(0, 8).map((p: any) => (
              <li key={p.match_id} className="py-2 flex items-center justify-between gap-2 text-sm">
                <Link href={`/matches/${p.match_id}`} className="min-w-0 hover:text-brand">
                  <span className="mr-1">{p.correct ? '✅' : '❌'}</span>
                  <span className="text-text truncate">{p.match}</span>
                  <span className="text-text-muted text-xs block sm:inline sm:ml-2">picked {p.pick} · {Math.round(p.confidence * 100)}%</span>
                </Link>
                <span className="text-text font-semibold flex-shrink-0">{p.score}</span>
              </li>
            ))}
          </ul>
          <ShareButton text={shareText} label="Share results" />
        </>
      )}
    </div>
  );
}
