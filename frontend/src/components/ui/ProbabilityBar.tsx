'use client';

import { cn, formatProbability } from '@/lib/utils';

interface ProbabilityBarProps {
  homeProb: number;
  drawProb: number;
  awayProb: number;
  showLabels?: boolean;
  className?: string;
}

export function ProbabilityBar({
  homeProb,
  drawProb,
  awayProb,
  showLabels = true,
  className,
}: ProbabilityBarProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {/* Bar */}
      <div className="h-3 rounded-full overflow-hidden flex bg-slate-700">
        <div
          className="bg-green-500 transition-all duration-500"
          style={{ width: `${homeProb * 100}%` }}
        />
        <div
          className="bg-yellow-500 transition-all duration-500"
          style={{ width: `${drawProb * 100}%` }}
        />
        <div
          className="bg-red-500 transition-all duration-500"
          style={{ width: `${awayProb * 100}%` }}
        />
      </div>

      {/* Labels */}
      {showLabels && (
        <div className="flex justify-between text-xs">
          <span className="text-green-400">{formatProbability(homeProb)}</span>
          <span className="text-yellow-400">{formatProbability(drawProb)}</span>
          <span className="text-red-400">{formatProbability(awayProb)}</span>
        </div>
      )}
    </div>
  );
}

interface SimpleProbabilityBarProps {
  probability: number;
  color?: 'green' | 'yellow' | 'red' | 'blue';
  className?: string;
}

export function SimpleProbabilityBar({
  probability,
  color = 'blue',
  className,
}: SimpleProbabilityBarProps) {
  const colorClasses = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    blue: 'bg-primary-500',
  };

  return (
    <div className={cn('h-2 rounded-full bg-slate-700 overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full transition-all duration-500', colorClasses[color])}
        style={{ width: `${probability * 100}%` }}
      />
    </div>
  );
}
