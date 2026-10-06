'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, TrendingUp, Target, Percent, RefreshCw, FlaskConical } from 'lucide-react';
import { predictionsApi } from '@/lib/api';
import { useModelInfo } from '@/hooks/useApi';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AccuracyBarChart } from '@/components/analytics/AccuracyBarChart';
import { MetricPlate } from '@/components/ui/MetricPlate';

interface StatsData {
  period: string;
  total_predictions: number;
  correct_predictions: number;
  accuracy: number;
  by_outcome: Record<string, { total: number; correct: number; accuracy: number }>;
  by_confidence: Record<string, { total: number; correct: number; accuracy: number }>;
  error?: string;
}

// Phase 5, step 1: the page used to mix the old v1 predictions with the
// live model's and was fixed to 30 days. Now: pick the model and period,
// and see the live model's tested scorecard next to its live record.
const MODELS = [
  { value: 'live', label: 'Live model' },
  { value: 'v1', label: 'Old model (v1)' },
  { value: 'all', label: 'All models' },
] as const;
const PERIODS = [7, 30, 90, 365] as const;

const pct = (x?: number | null, d = 1) => (x == null ? '--' : `${(x * 100).toFixed(d)}%`);

export default function AnalyticsPage() {
  const [model, setModel] = useState<(typeof MODELS)[number]['value']>('live');
  const [days, setDays] = useState<number>(30);
  const { data: modelInfo } = useModelInfo();
  const liveFamily = modelInfo?.version?.split('_')[0];
  const family = model === 'live' ? liveFamily : model === 'v1' ? 'v1' : undefined;

  const { data, isLoading, error, refetch } = useQuery<StatsData>({
    queryKey: ['prediction-stats', { days, family }],
    queryFn: () => predictionsApi.getStats({ days, model_family: family }),
    enabled: model !== 'live' || !!liveFamily,
  });

  const hasData = data && !data.error && data.total_predictions > 0;
  const highConfidence = data?.by_confidence?.high;
  const modelLabel = model === 'live' ? `Model ${liveFamily || ''}`.trim() : MODELS.find((m) => m.value === model)!.label;
  const periodLabel = days === 365 ? 'Last 12 months' : `Last ${days} days`;

  return (
    <>
      <div className="content-header">
        <h1>Analytics</h1>
        <p>How often the model is right, before kickoff, on matches that have been played</p>
      </div>

      <div className="card card-compact mb-4 sm:mb-6">
        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="an-model" className="text-xs sm:text-sm text-text-muted">Model:</label>
            <select id="an-model" value={model} onChange={(e) => setModel(e.target.value as any)} className="input input-sm text-xs sm:text-sm">
              {MODELS.map((m) => <option key={m.value} value={m.value}>{m.value === 'live' && liveFamily ? `Live model (${liveFamily})` : m.label}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="an-period" className="text-xs sm:text-sm text-text-muted">Period:</label>
            <select id="an-period" value={days} onChange={(e) => setDays(Number(e.target.value))} className="input input-sm text-xs sm:text-sm">
              {PERIODS.map((d) => <option key={d} value={d}>{d === 365 ? '12 months' : `${d} days`}</option>)}
            </select>
          </div>
          <button onClick={() => refetch()} className="btn btn-secondary btn-sm ml-auto">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {model === 'live' && <TestedScorecard info={modelInfo} />}

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
        <div className="card text-center py-12">
          <div className="card-icon w-16 h-16 mx-auto mb-4">
            <BarChart3 className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-semibold text-text mb-2">No graded predictions for {modelLabel} · {periodLabel.toLowerCase()}</h3>
          <p className="text-text-muted text-sm max-w-md mx-auto">
            {model === 'live'
              ? 'The live model’s record starts as the matches it predicted are played and their results are synced (daily at 04:15 UTC). Until then, the tested results above show how it did on matches it never saw in training.'
              : 'Try a longer period.'}
          </p>
        </div>
      ) : (
        <>
          <MetricPlate
            title={`Live record — ${modelLabel} · ${periodLabel}`}
            rows={[
              { metric: 'Accuracy', value: pct(data.accuracy), remark: `${data.correct_predictions} of ${data.total_predictions} correct` },
              { metric: 'Graded predictions', value: String(data.total_predictions), remark: 'Made before kickoff, checked against the result' },
              {
                metric: 'Top-pick accuracy (55%+)',
                value: pct(highConfidence?.accuracy),
                remark: highConfidence ? `${highConfidence.correct} of ${highConfidence.total} top picks` : 'No top picks in this period',
              },
            ]}
          />
          {data.total_predictions < 100 && (
            <p className="text-xs text-text-muted mb-4 px-1">
              Small sample: with fewer than 100 matches, accuracy can easily swing by ±10 points. Read it alongside the tested results.
            </p>
          )}

          <div className="content-grid">
            <div className="col-span-6">
              <div className="card">
                <div className="card-header">
                  <div className="card-icon"><Target className="w-5 h-5" /></div>
                  <div>
                    <h2 className="card-title">Accuracy by predicted outcome</h2>
                    <p className="card-desc">When the model picked home / draw / away, how often it was right</p>
                  </div>
                </div>
                <AccuracyBarChart
                  data={[
                    { label: 'Picked home', accuracy: data.by_outcome.H?.accuracy || 0, total: data.by_outcome.H?.total || 0, correct: data.by_outcome.H?.correct || 0 },
                    { label: 'Picked draw', accuracy: data.by_outcome.D?.accuracy || 0, total: data.by_outcome.D?.total || 0, correct: data.by_outcome.D?.correct || 0 },
                    { label: 'Picked away', accuracy: data.by_outcome.A?.accuracy || 0, total: data.by_outcome.A?.total || 0, correct: data.by_outcome.A?.correct || 0 },
                  ]}
                />
              </div>
            </div>

            <div className="col-span-6">
              <div className="card">
                <div className="card-header">
                  <div className="card-icon"><Percent className="w-5 h-5" /></div>
                  <div>
                    <h2 className="card-title">Accuracy by confidence</h2>
                    <p className="card-desc">Higher confidence should mean right more often</p>
                  </div>
                </div>
                <AccuracyBarChart
                  data={[
                    { label: 'High (55%+)', accuracy: data.by_confidence.high?.accuracy || 0, total: data.by_confidence.high?.total || 0, correct: data.by_confidence.high?.correct || 0 },
                    { label: 'Medium (45–55%)', accuracy: data.by_confidence.medium?.accuracy || 0, total: data.by_confidence.medium?.total || 0, correct: data.by_confidence.medium?.correct || 0 },
                    { label: 'Low (<45%)', accuracy: data.by_confidence.low?.accuracy || 0, total: data.by_confidence.low?.total || 0, correct: data.by_confidence.low?.correct || 0 },
                  ]}
                />
              </div>
            </div>

            <div className="col-span-12">
              <div className="card">
                <div className="card-header">
                  <div className="card-icon"><TrendingUp className="w-5 h-5" /></div>
                  <div>
                    <h2 className="card-title">Summary</h2>
                    <p className="card-desc">{modelLabel} · {periodLabel}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <SummaryTile value={String(data.correct_predictions)} label="Correct" accent />
                  <SummaryTile value={String(data.total_predictions - data.correct_predictions)} label="Incorrect" />
                  <SummaryTile value={pct(data.accuracy)} label="Hit rate" />
                  <SummaryTile value={String(highConfidence?.total || 0)} label="Top picks (55%+)" />
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function SummaryTile({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="p-4 bg-surface rounded-lg text-center">
      <div className={`text-2xl font-bold ${accent ? 'text-brand' : 'text-text'}`}>{value}</div>
      <div className="text-xs text-text-muted">{label}</div>
    </div>
  );
}

/** The live model's results on matches it never saw in training, vs the bookmakers. */
function TestedScorecard({ info }: { info: any }) {
  const sc = info?.scorecard;
  if (!sc?.test) return null;
  const t = sc.test;
  const b = sc.bookmaker;
  const n = sc.samples?.test;
  const from = sc.windows?.test_from;
  return (
    <div className="card mb-4 sm:mb-6">
      <div className="card-header">
        <div className="card-icon"><FlaskConical className="w-5 h-5" /></div>
        <div>
          <h2 className="card-title">Tested on unseen matches</h2>
          <p className="card-desc">
            {info.version} · {n ? `${n.toLocaleString()} matches` : ''}{from ? ` since ${from}` : ''}, none used in training
          </p>
        </div>
      </div>
      <div className="table-wrap overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-text-muted text-xs text-left">
              <th className="py-2 pr-4 font-medium">Predictor</th>
              <th className="py-2 pr-4 font-medium text-right">Accuracy</th>
              <th className="py-2 font-medium text-right" title="Lower is better: penalises confident wrong picks">Log loss ↓</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-border-dim">
              <td className="py-2 pr-4 font-semibold text-text">This model</td>
              <td className="py-2 pr-4 text-right font-semibold text-brand">{pct(t.accuracy, 2)}</td>
              <td className="py-2 text-right font-semibold text-text">{t.log_loss?.toFixed(4)}</td>
            </tr>
            {b && (
              <tr className="border-t border-border-dim">
                <td className="py-2 pr-4 text-text-sec">Bookmakers (average odds)</td>
                <td className="py-2 pr-4 text-right text-text-sec">{pct(b.accuracy, 2)}</td>
                <td className="py-2 text-right text-text-sec">{b.log_loss?.toFixed(4)}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {Array.isArray(sc.calibration) && sc.calibration.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-text-muted mb-2">Does its confidence hold up? When it says X%, how often it was right:</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {sc.calibration.map((row: any) => (
              <div key={row.band} className="p-3 bg-surface rounded-lg text-center">
                <div className="text-xs text-text-muted">{row.band}</div>
                <div className="text-sm text-text">said {pct(row.predicted)} · right {pct(row.actual)}</div>
                <div className="text-[10px] text-text-muted">{row.n?.toLocaleString()} matches</div>
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="text-xs text-text-muted mt-3">
        Football is hard to predict: about 50% is level with the bookmakers. Being accurate is not the same as making money; see Value Bets.
      </p>
    </div>
  );
}
