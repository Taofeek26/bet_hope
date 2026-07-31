'use client';

import { useEffect, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, Play, Lock, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { authApi, adminTasksApi, TaskRun, TaskRunStatus } from '@/lib/api';

const ACTIVE_TASKS_KEY = 'bethope_active_task_ids';

function readActiveIds(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(ACTIVE_TASKS_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeActiveIds(ids: string[]) {
  localStorage.setItem(ACTIVE_TASKS_KEY, JSON.stringify(ids));
}

const TASK_DEFS: { command: string; args: string[]; label: string; description: string }[] = [
  {
    command: 'sync_real_data',
    args: ['--fixtures'],
    label: 'Sync Data',
    description: 'Pull upcoming fixtures + generate predictions for them',
  },
  {
    command: 'train_model',
    args: ['--leagues', 'E0', '--seasons', '2425'],
    label: 'Train Model',
    description: 'Retrain on Premier League 2024-25 (safe scope — wider scopes can exceed the 15-minute Lambda limit)',
  },
  {
    command: 'generate_predictions',
    args: ['--upcoming', '--days', '14'],
    label: 'Generate Predictions',
    description: 'Run the active model over upcoming matches',
  },
];

export default function AdminPage() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const [activeIds, setActiveIds] = useState<string[]>([]);

  useEffect(() => {
    setToken(typeof window !== 'undefined' ? localStorage.getItem('token') : null);
    setActiveIds(readActiveIds());
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setLoggingIn(true);
    try {
      const { access } = await authApi.login(username, password);
      localStorage.setItem('token', access);
      setToken(access);
    } catch (err: any) {
      setLoginError(
        err?.response?.status === 401
          ? 'Invalid username or password.'
          : 'Login failed — check the API is reachable.'
      );
    } finally {
      setLoggingIn(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  const addActiveId = useCallback((id: string) => {
    setActiveIds((prev) => {
      const next = [id, ...prev.filter((x) => x !== id)].slice(0, 10);
      writeActiveIds(next);
      return next;
    });
  }, []);

  const removeActiveId = useCallback((id: string) => {
    setActiveIds((prev) => {
      const next = prev.filter((x) => x !== id);
      writeActiveIds(next);
      return next;
    });
  }, []);

  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ['admin-tasks-history'],
    queryFn: () => adminTasksApi.list(),
    enabled: !!token,
    refetchInterval: 10000,
  });

  const trigger = async (def: typeof TASK_DEFS[number]) => {
    try {
      const task = await adminTasksApi.trigger(def.command, def.args);
      addActiveId(task.id);
      refetchHistory();
    } catch (err) {
      // surfaced via the failed TaskRun row itself in most cases; a network-
      // level failure (e.g. not logged in) just no-ops the button here.
      console.error('Failed to trigger task', err);
    }
  };

  if (!token) {
    return (
      <>
        <div className="content-header">
          <h1>Admin</h1>
          <p>Sign in to trigger data sync, training, and prediction jobs</p>
        </div>
        <div className="blueprint plate" style={{ maxWidth: 420 }}>
          <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
          <form onSubmit={handleLogin} className="p-6 space-y-4">
            <div className="flex items-center gap-2 text-text-muted text-xs uppercase tracking-wide mb-2">
              <Lock className="w-3.5 h-3.5" /> Admin sign-in
            </div>
            <input
              className="w-full bg-input border border-border px-3 py-2 text-sm"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
            <input
              className="w-full bg-input border border-border px-3 py-2 text-sm"
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
            {loginError && <p className="text-red-400 text-xs">{loginError}</p>}
            <button type="submit" disabled={loggingIn} className="btn btn-primary w-full justify-center">
              {loggingIn ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign in'}
            </button>
          </form>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="content-header flex items-center justify-between">
        <div>
          <h1>Admin</h1>
          <p>Trigger data sync, training, and prediction jobs and watch them run</p>
        </div>
        <button onClick={handleLogout} className="btn btn-secondary btn-sm">Sign out</button>
      </div>

      <h2 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Run a task</h2>
      <div className="grid sm:grid-cols-3 gap-4 mb-8">
        {TASK_DEFS.map((def) => (
          <div key={def.command} className="blueprint elev-sm flex flex-col justify-between">
            <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
            <div>
              <div className="card-title text-sm mb-1">{def.label}</div>
              <p className="text-xs text-text-muted mb-4">{def.description}</p>
            </div>
            <button onClick={() => trigger(def)} className="btn btn-primary btn-sm w-full justify-center gap-2">
              <Play className="w-3.5 h-3.5" /> Run
            </button>
          </div>
        ))}
      </div>

      {activeIds.length > 0 && (
        <>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">In progress</h2>
          <div className="space-y-3 mb-8">
            {activeIds.map((id) => (
              <LiveTaskCard key={id} id={id} onSettled={() => refetchHistory()} onDismiss={() => removeActiveId(id)} />
            ))}
          </div>
        </>
      )}

      <h2 className="text-sm font-semibold uppercase tracking-wide text-text-muted mb-3">Recent runs</h2>
      <div className="blueprint plate">
        <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="px-5 py-2 font-normal">Command</th>
              <th className="px-5 py-2 font-normal">Status</th>
              <th className="px-5 py-2 font-normal">Started</th>
              <th className="px-5 py-2 font-normal">Duration</th>
            </tr>
          </thead>
          <tbody>
            {(history || []).length === 0 && (
              <tr><td colSpan={4} className="px-5 py-6 text-center text-text-muted text-sm">No tasks run yet</td></tr>
            )}
            {(history || []).map((t) => (
              <tr key={t.id} className="border-b border-border-dim last:border-b-0">
                <td className="px-5 py-3 text-sm">{t.command_display}</td>
                <td className="px-5 py-3"><StatusBadge status={t.status} /></td>
                <td className="px-5 py-3 text-xs text-text-muted">
                  {t.started_at ? new Date(t.started_at).toLocaleString() : '—'}
                </td>
                <td className="px-5 py-3 text-xs text-text-muted">
                  {t.duration_seconds != null ? `${t.duration_seconds}s` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function StatusBadge({ status }: { status: TaskRunStatus }) {
  const map: Record<TaskRunStatus, { icon: JSX.Element; className: string; label: string }> = {
    pending: { icon: <Clock className="w-3 h-3" />, className: 'text-text-muted', label: 'Pending' },
    running: { icon: <RefreshCw className="w-3 h-3 animate-spin" />, className: 'text-brand', label: 'Running' },
    success: { icon: <CheckCircle className="w-3 h-3" />, className: 'text-emerald-400', label: 'Success' },
    error: { icon: <XCircle className="w-3 h-3" />, className: 'text-red-400', label: 'Error' },
    timeout: { icon: <XCircle className="w-3 h-3" />, className: 'text-amber-400', label: 'Timeout' },
  };
  const s = map[status] ?? map.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${s.className}`}>
      {s.icon} {s.label}
    </span>
  );
}

function LiveTaskCard({ id, onSettled, onDismiss }: { id: string; onSettled: () => void; onDismiss: () => void }) {
  const { data: task } = useQuery({
    queryKey: ['admin-task', id],
    queryFn: () => adminTasksApi.getStatus(id),
    // Polling — not a websocket — is exactly what makes this survive a
    // closed/reopened tab: the id is in localStorage, and on remount this
    // query just picks the row back up from wherever the job actually is.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'pending' || status === 'running' ? 2500 : false;
    },
  });

  const settled = task && task.status !== 'pending' && task.status !== 'running';

  useEffect(() => {
    if (settled) onSettled();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled]);

  if (!task) return null;

  const elapsedSeconds = task.started_at
    ? Math.round((Date.now() - new Date(task.started_at).getTime()) / 1000)
    : 0;

  return (
    <div className="blueprint elev-sm">
      <i className="corner tl" /><i className="corner tr" /><i className="corner bl" /><i className="corner br" />
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">{task.command_display}</span>
          <StatusBadge status={task.status} />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-muted">
            {task.duration_seconds != null ? `${task.duration_seconds}s` : `${elapsedSeconds}s elapsed`}
          </span>
          {settled && (
            <button onClick={onDismiss} className="text-xs text-text-muted hover:text-text">Dismiss</button>
          )}
        </div>
      </div>
      {task.error && <p className="text-xs text-red-400 mb-2">{task.error}</p>}
      {task.log_tail && (
        <pre className="text-[11px] leading-relaxed text-text-muted bg-black/40 border border-border-dim p-3 max-h-40 overflow-auto whitespace-pre-wrap">
          {task.log_tail}
        </pre>
      )}
    </div>
  );
}
