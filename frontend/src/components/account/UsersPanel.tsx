'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Users, X } from 'lucide-react';
import { accountApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

const naira = (n: number) => `${n < 0 ? '−' : ''}₦${Math.abs(Math.round(n)).toLocaleString()}`;
const day = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: '2-digit' }) : '—');

/** Admin: every user with their activity, and each user's bets (Phase 7). */
export function UsersPanel() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [openId, setOpenId] = useState<number | null>(null);
  const { data, isLoading, error } = useQuery({ queryKey: ['admin-users', search], queryFn: () => accountApi.adminUsers(search || undefined) });

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-text-muted flex items-center gap-2"><Users className="w-4 h-4" /> Users</h2>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search username, email or name" className="input input-sm w-56" aria-label="Search users" />
      </div>
      {isLoading ? <LoadingSpinner /> : error ? <p className="text-sm text-red-400">Could not load users (staff only).</p> : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <Tile label="Users" value={String(data.totals.users)} />
            <Tile label="Signed in, last 7 days" value={String(data.totals.active_7d)} />
            <Tile label="Saved bets" value={String(data.totals.bets)} />
            <Tile label="Total staked" value={naira(data.totals.staked)} />
          </div>
          <div className="card !p-0 overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead>
                <tr className="text-left text-xs text-text-muted border-b border-border">
                  {['User', 'Joined', 'Last sign-in', 'Bets', 'Won / lost', 'Staked', 'Profit / loss', ''].map((h) => <th key={h} className="px-4 py-2 font-normal">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.users.map((u: any) => (
                  <tr key={u.id} className="border-b border-border-dim last:border-b-0 hover:bg-surface cursor-pointer" onClick={() => setOpenId(u.id)}>
                    <td className="px-4 py-2">
                      <div className="text-text">{u.name || u.username}</div>
                      <div className="text-[11px] text-text-muted">@{u.username}{u.email && u.email !== u.username ? ` · ${u.email}` : ''}{u.is_staff ? ' · admin' : ''}{!u.is_active ? ' · disabled' : ''}</div>
                    </td>
                    <td className="px-4 py-2 text-xs text-text-muted">{day(u.joined)}</td>
                    <td className="px-4 py-2 text-xs text-text-muted">{day(u.last_login)}</td>
                    <td className="px-4 py-2">{u.bets}</td>
                    <td className="px-4 py-2 text-xs">{u.won} / {u.lost}{u.pending ? ` · ${u.pending} open` : ''}</td>
                    <td className="px-4 py-2">{naira(u.staked)}</td>
                    <td className={`px-4 py-2 font-semibold ${u.profit > 0 ? 'text-green-500' : u.profit < 0 ? 'text-red-400' : 'text-text-muted'}`}>{naira(u.profit)}</td>
                    <td className="px-4 py-2 text-brand text-xs">View</td>
                  </tr>
                ))}
                {!data.users.length && <tr><td colSpan={8} className="px-4 py-6 text-center text-text-muted">No users found</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
      {openId != null && <UserDrawer id={openId} onClose={() => setOpenId(null)} onChanged={() => qc.invalidateQueries({ queryKey: ['admin-users'] })} />}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return <div className="card card-compact !mb-0"><div className="text-xs text-text-muted">{label}</div><div className="text-lg font-bold text-text">{value}</div></div>;
}

function UserDrawer({ id, onClose, onChanged }: { id: number; onClose: () => void; onChanged: () => void }) {
  const { data, isLoading, refetch } = useQuery({ queryKey: ['admin-user', id], queryFn: () => accountApi.adminUser(id) });
  const [temp, setTemp] = useState<string | null>(null);
  const [msg, setMsg] = useState('');
  const toggle = async () => {
    try { await accountApi.adminSetActive(id, !data.user.is_active); await refetch(); onChanged(); }
    catch (e: any) { setMsg(e?.response?.data?.error || 'Not allowed'); }
  };
  const reset = async () => {
    if (!confirm('Set a temporary password for this user? Their current password stops working.')) return;
    try { setTemp((await accountApi.adminResetPassword(id)).temporary_password); }
    catch (e: any) { setMsg(e?.response?.data?.error || 'Not allowed'); }
  };
  return (
    <aside className="fixed inset-y-0 right-0 z-50 w-full lg:w-[480px] bg-card lg:border-l border-border shadow-2xl flex flex-col" aria-label="User details">
      <div className="flex items-center justify-between p-4 border-b border-border-dim">
        <h2 className="font-semibold text-text truncate">{data?.user?.name || data?.user?.email || 'User'}</h2>
        <button onClick={onClose} className="btn btn-icon btn-secondary" aria-label="Close"><X className="w-4 h-4" /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading || !data ? <LoadingSpinner /> : (
          <>
            <div className="text-sm text-text-sec space-y-1">
              <div>{data.user.email}</div>
              <div className="text-xs text-text-muted">Joined {day(data.user.joined)} · last sign-in {day(data.user.last_login)} · {data.user.favourite_teams.length} favourite teams · weekly limit {data.user.weekly_limit ? naira(data.user.weekly_limit) : 'none'}</div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={toggle} className="btn btn-secondary btn-sm">{data.user.is_active ? 'Disable account' : 'Enable account'}</button>
              <button onClick={reset} className="btn btn-secondary btn-sm">Set temporary password</button>
            </div>
            {temp && <p className="text-sm p-2 rounded bg-surface border border-border-dim">Temporary password: <code className="text-brand">{temp}</code> (shown once; give it to the user and ask them to change it)</p>}
            {msg && <p className="text-sm text-red-400">{msg}</p>}
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-text-muted mb-2">Bets ({data.bets.length})</div>
              <ul className="space-y-2">
                {data.bets.map((b: any) => (
                  <li key={b.id} className="p-3 bg-surface rounded-lg border border-border-dim text-xs">
                    <div className="flex justify-between gap-2 mb-1">
                      <span className="text-text font-semibold">
                        <span className={`mr-1 px-1.5 py-0.5 rounded ${b.status === 'won' ? 'bg-green-500/20 text-green-500' : b.status === 'lost' ? 'bg-red-500/20 text-red-400' : 'bg-card text-text-muted'}`}>{String(b.status).toUpperCase()}</span>
                        {naira(b.stake)} @ {b.odds.toFixed(2)} · {b.bookmaker}{b.source === 'extension' ? ' (extension)' : ''}
                      </span>
                      <span className={b.profit > 0 ? 'text-green-500' : b.profit < 0 ? 'text-red-400' : 'text-text-muted'}>{naira(b.profit)}</span>
                    </div>
                    <div className="text-text-muted">{day(b.placedAt)}{b.ticketId ? ` · ticket ${b.ticketId}` : ''}{b.bookingCode ? ` · code ${b.bookingCode}` : ''}</div>
                    <ul className="mt-1 text-text-sec">{b.selections.map((s: any, i: number) => <li key={i}>• {s.label} · {s.match}</li>)}</ul>
                  </li>
                ))}
                {!data.bets.length && <li className="text-sm text-text-muted">No bets saved.</li>}
              </ul>
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
