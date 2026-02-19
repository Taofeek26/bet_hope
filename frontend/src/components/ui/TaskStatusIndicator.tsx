'use client';

import { useState } from 'react';
import { Activity, CheckCircle, AlertCircle, Clock, ChevronDown, RefreshCw } from 'lucide-react';
import { useTaskStatus } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

export function TaskStatusIndicator() {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading, refetch, isRefetching } = useTaskStatus();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface text-text-muted text-sm">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span className="hidden sm:inline">Loading...</span>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { overall_health, summary } = data;

  // Determine indicator styling based on health
  const healthConfig = {
    healthy: {
      bg: 'bg-emerald-500/10 hover:bg-emerald-500/20',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      icon: CheckCircle,
      label: 'All Systems Running',
    },
    partial: {
      bg: 'bg-amber-500/10 hover:bg-amber-500/20',
      border: 'border-amber-500/30',
      text: 'text-amber-400',
      icon: Clock,
      label: 'Some Tasks Delayed',
    },
    warning: {
      bg: 'bg-red-500/10 hover:bg-red-500/20',
      border: 'border-red-500/30',
      text: 'text-red-400',
      icon: AlertCircle,
      label: 'Tasks Need Attention',
    },
    unknown: {
      bg: 'bg-slate-500/10 hover:bg-slate-500/20',
      border: 'border-slate-500/30',
      text: 'text-slate-400',
      icon: Activity,
      label: 'No Task History',
    },
  };

  const config = healthConfig[overall_health] || healthConfig.unknown;
  const StatusIcon = config.icon;

  return (
    <div className="relative">
      {/* Main Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all text-sm',
          config.bg,
          config.border,
          config.text
        )}
      >
        <StatusIcon className="w-4 h-4" />
        <span className="hidden sm:inline font-medium">
          {summary.healthy}/{summary.total} Tasks
        </span>
        <ChevronDown className={cn('w-4 h-4 transition-transform', expanded && 'rotate-180')} />
      </button>

      {/* Dropdown Panel */}
      {expanded && (
        <>
          {/* Backdrop to close on click outside */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setExpanded(false)}
          />

          {/* Panel */}
          <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-card border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-surface">
              <div>
                <h3 className="font-semibold text-text">Task Status</h3>
                <p className="text-xs text-text-muted">{config.label}</p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  refetch();
                }}
                className="p-2 rounded-lg hover:bg-input text-text-muted hover:text-text transition-colors"
                title="Refresh"
              >
                <RefreshCw className={cn('w-4 h-4', isRefetching && 'animate-spin')} />
              </button>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-2 p-4 border-b border-border">
              <div className="text-center p-2 rounded-lg bg-emerald-500/10">
                <div className="text-lg font-bold text-emerald-400">{summary.healthy}</div>
                <div className="text-xs text-text-muted">Healthy</div>
              </div>
              <div className="text-center p-2 rounded-lg bg-amber-500/10">
                <div className="text-lg font-bold text-amber-400">{summary.stale}</div>
                <div className="text-xs text-text-muted">Stale</div>
              </div>
              <div className="text-center p-2 rounded-lg bg-slate-500/10">
                <div className="text-lg font-bold text-slate-400">{summary.unknown}</div>
                <div className="text-xs text-text-muted">Unknown</div>
              </div>
            </div>

            {/* Task Groups */}
            <div className="max-h-80 overflow-y-auto">
              {data.groups.map((group) => (
                <div key={group.group} className="border-b border-border last:border-b-0">
                  <div className="px-4 py-2 bg-surface/50">
                    <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                      {group.group}
                    </h4>
                  </div>
                  <div className="divide-y divide-border/50">
                    {group.tasks.map((task) => (
                      <TaskRow key={task.key} task={task} />
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="p-3 bg-surface border-t border-border text-center">
              <p className="text-xs text-text-muted">
                Last checked: {new Date(data.last_checked).toLocaleTimeString()}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface TaskRowProps {
  task: {
    key: string;
    name: string;
    schedule: string;
    last_run: string | null;
    time_ago: string | null;
    last_status: string | null;
    health: 'healthy' | 'stale' | 'unknown';
  };
}

function TaskRow({ task }: TaskRowProps) {
  const healthStyles = {
    healthy: 'bg-emerald-500',
    stale: 'bg-amber-500',
    unknown: 'bg-slate-500',
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 hover:bg-surface/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className={cn('w-2 h-2 rounded-full', healthStyles[task.health])} />
        <div>
          <div className="text-sm font-medium text-text">{task.name}</div>
          <div className="text-xs text-text-muted">{task.schedule}</div>
        </div>
      </div>
      <div className="text-right">
        {task.time_ago ? (
          <div className="text-xs text-text-sec">{task.time_ago}</div>
        ) : (
          <div className="text-xs text-text-muted">Never run</div>
        )}
      </div>
    </div>
  );
}
