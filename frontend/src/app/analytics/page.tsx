'use client';

import { useQuery } from '@tanstack/react-query';
import { BarChart3, TrendingUp, Target, Percent, RefreshCw } from 'lucide-react';
import { predictionsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AccuracyBarChart } from '@/components/analytics/AccuracyBarChart';

interface StatsData {
  period: string;
  total_predictions: number;
  correct_predictions: number;
  accuracy: number;
  by_outcome: Record<string, { total: number; correct: number; accuracy: number }>;
  by_confidence: Record<string, { total: number; correct: number; accuracy: number }>;
  error?: string;
}

export default function AnalyticsPage() {
  const { data, isLoading, error, refetch } = useQuery<StatsData>({
    queryKey: ['prediction-stats'],
    queryFn: () => predictionsApi.getStats({ days: 30 }),
  });

  const hasData = data && !data.error && data.total_predictions > 0;
  const highConfidence = data?.by_confidence?.high;

  return (
    <>
      <div className="content-header">
        <h1>Analytics</h1>
        <p>Model performance and prediction accuracy statistics</p>
      </div>

      <div className="flex justify-end mb-4">
        <button onClick={() => refetch()} className="btn btn-secondary btn-sm">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <p className="text-text-muted mb-4">Failed to load analytics</p>
          <button onClick={() => refetch()} className="btn btn-primary">
            Try Again
          </button>
        </div>
      ) : !hasData ? (
        <>
          {/* Show stats grid with placeholders */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">--</div>
              <div className="stat-label">Overall Accuracy</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">0</div>
              <div className="stat-label">Total Predictions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">--</div>
              <div className="stat-label">High Confidence</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">--</div>
              <div className="stat-label">ROI</div>
            </div>
          </div>

          <div className="card text-center py-12 mt-6">
            <div className="card-icon w-16 h-16 mx-auto mb-4">
              <BarChart3 className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-semibold text-text mb-2">No Verified Predictions Yet</h3>
            <p className="text-text-muted text-sm max-w-sm mx-auto">
              Analytics will appear here once matches with predictions have finished and results are recorded.
            </p>
          </div>
        </>
      ) : (
        <>
          {/* Overview Stats */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{(data.accuracy * 100).toFixed(1)}%</div>
              <div className="stat-label">Overall Accuracy</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{data.total_predictions}</div>
              <div className="stat-label">Total Predictions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {highConfidence ? `${(highConfidence.accuracy * 100).toFixed(1)}%` : '--'}
              </div>
              <div className="stat-label">High Confidence Accuracy</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{data.correct_predictions}</div>
              <div className="stat-label">Correct Predictions</div>
            </div>
          </div>

          <div className="content-grid">
            {/* Accuracy by Outcome */}
            <div className="col-span-6">
              <div className="card">
                <div className="card-header">
                  <div className="card-icon">
                    <Target className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="card-title">Accuracy by Outcome</h2>
                    <p className="card-desc">{data.period}</p>
                  </div>
                </div>

                <AccuracyBarChart
                  data={[
                    { label: 'Home Wins', accuracy: data.by_outcome.H?.accuracy || 0, total: data.by_outcome.H?.total || 0, correct: data.by_outcome.H?.correct || 0 },
                    { label: 'Draws', accuracy: data.by_outcome.D?.accuracy || 0, total: data.by_outcome.D?.total || 0, correct: data.by_outcome.D?.correct || 0 },
                    { label: 'Away Wins', accuracy: data.by_outcome.A?.accuracy || 0, total: data.by_outcome.A?.total || 0, correct: data.by_outcome.A?.correct || 0 },
                  ]}
                />
              </div>
            </div>

            {/* Accuracy by Confidence */}
            <div className="col-span-6">
              <div className="card">
                <div className="card-header">
                  <div className="card-icon">
                    <Percent className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="card-title">Accuracy by Confidence</h2>
                    <p className="card-desc">How confidence correlates with accuracy</p>
                  </div>
                </div>

                <AccuracyBarChart
                  data={[
                    { label: 'High (60%+)', accuracy: data.by_confidence.high?.accuracy || 0, total: data.by_confidence.high?.total || 0, correct: data.by_confidence.high?.correct || 0 },
                    { label: 'Medium (45-60%)', accuracy: data.by_confidence.medium?.accuracy || 0, total: data.by_confidence.medium?.total || 0, correct: data.by_confidence.medium?.correct || 0 },
                    { label: 'Low (<45%)', accuracy: data.by_confidence.low?.accuracy || 0, total: data.by_confidence.low?.total || 0, correct: data.by_confidence.low?.correct || 0 },
                  ]}
                />
              </div>
            </div>

            {/* Summary Card */}
            <div className="col-span-12">
              <div className="card">
                <div className="card-header">
                  <div className="card-icon">
                    <TrendingUp className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="card-title">Performance Summary</h2>
                    <p className="card-desc">{data.period}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-surface rounded-lg text-center">
                    <div className="text-2xl font-bold text-brand">
                      {data.correct_predictions}
                    </div>
                    <div className="text-xs text-text-muted">Correct</div>
                  </div>
                  <div className="p-4 bg-surface rounded-lg text-center">
                    <div className="text-2xl font-bold text-text-secondary">
                      {data.total_predictions - data.correct_predictions}
                    </div>
                    <div className="text-xs text-text-muted">Incorrect</div>
                  </div>
                  <div className="p-4 bg-surface rounded-lg text-center">
                    <div className="text-2xl font-bold text-text">
                      {(data.accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-text-muted">Hit Rate</div>
                  </div>
                  <div className="p-4 bg-surface rounded-lg text-center">
                    <div className="text-2xl font-bold text-text">
                      {highConfidence?.total || 0}
                    </div>
                    <div className="text-xs text-text-muted">High Conf. Bets</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

