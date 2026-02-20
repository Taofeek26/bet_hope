'use client';

import { usePredictionStats, useModelInfo } from '@/hooks/useApi';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { SimpleProbabilityBar } from '@/components/ui/ProbabilityBar';
import { formatProbability } from '@/lib/utils';
import { BarChart3, CheckCircle, XCircle, Target } from 'lucide-react';

export function PredictionStats() {
  const { data: stats, isLoading } = usePredictionStats({ days: 30 });
  const { data: modelInfo } = useModelInfo();

  if (isLoading) return <LoadingSpinner />;

  if (!stats || (stats as any).error) {
    return (
      <div className="text-text-muted text-center py-8">
        <p className="mb-2">No verified predictions yet.</p>
        <p className="text-xs">Statistics will appear after matches are completed.</p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="flex items-center gap-2 sm:gap-3">
        <div className="p-1.5 sm:p-2 rounded-lg bg-accent-500/20">
          <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 text-accent-400" />
        </div>
        <div>
          <CardTitle className="text-sm sm:text-base">Model Performance</CardTitle>
          <p className="text-xs sm:text-sm text-slate-400">{stats.period}</p>
        </div>
      </CardHeader>

      <CardBody className="space-y-4 sm:space-y-6">
        {/* Overall accuracy */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs sm:text-sm text-slate-400">Overall Accuracy</span>
            <span className="text-base sm:text-lg font-semibold text-white">
              {formatProbability(stats.accuracy)}
            </span>
          </div>
          <SimpleProbabilityBar
            probability={stats.accuracy}
            color={stats.accuracy >= 0.5 ? 'green' : 'red'}
          />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2 sm:gap-4">
          <StatCard
            icon={CheckCircle}
            label="Correct"
            value={stats.correct_predictions}
            color="text-green-400"
          />
          <StatCard
            icon={XCircle}
            label="Total"
            value={stats.total_predictions}
            color="text-slate-400"
          />
        </div>

        {/* By confidence */}
        {stats.by_confidence && (
          <div>
            <h4 className="text-xs sm:text-sm font-medium text-slate-300 mb-2 sm:mb-3">
              By Confidence Level
            </h4>
            <div className="space-y-1.5 sm:space-y-2">
              {Object.entries(stats.by_confidence).map(([level, data]: [string, any]) => (
                <div key={level} className="flex items-center justify-between text-xs sm:text-sm">
                  <span className="text-slate-400 capitalize">{level}</span>
                  <div className="flex items-center gap-1.5 sm:gap-2">
                    <span className="text-slate-500">{data.total} picks</span>
                    <span className="text-white font-medium">
                      {formatProbability(data.accuracy)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Model info */}
        {modelInfo && (
          <div className="pt-3 sm:pt-4 border-t border-slate-700/50">
            <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
              <Target className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-primary-400" />
              <span className="text-xs sm:text-sm font-medium text-slate-300">Active Model</span>
            </div>
            <p className="text-[10px] sm:text-xs text-slate-400">
              Version: {modelInfo.version}
            </p>
            <p className="text-[10px] sm:text-xs text-slate-400">
              Trained: {new Date(modelInfo.trained_at).toLocaleDateString()}
            </p>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: string;
}

function StatCard({ icon: Icon, label, value, color }: StatCardProps) {
  return (
    <div className="p-2 sm:p-3 rounded-lg bg-slate-800/50">
      <div className="flex items-center gap-1.5 sm:gap-2 mb-0.5 sm:mb-1">
        <Icon className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${color}`} />
        <span className="text-[10px] sm:text-xs text-slate-400">{label}</span>
      </div>
      <p className="text-lg sm:text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
