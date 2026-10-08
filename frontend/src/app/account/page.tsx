'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { UserCircle2, LogOut, ShieldCheck } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { accountApi } from '@/lib/api';
import { useMyBets } from '@/lib/mybets';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

const err = (e: any, fallback: string) => e?.response?.data?.error || e?.response?.data?.detail || fallback;

/** Sign in / create account, and the signed-in user's profile (Phase 7). */
export default function AccountPage() {
  const { user, loading } = useAuth();
  return (
    <>
      <div className="content-header">
        <h1>{user ? 'My account' : 'Sign in'}</h1>
        <p>{user ? 'Your bets, favourites and limits are saved to your account and follow you to any device.' : 'Save your bets, favourites and limits to an account, so they follow you to any phone or computer.'}</p>
      </div>
      {loading ? <LoadingSpinner /> : user ? <Profile /> : <SignIn />}
    </>
  );
}

function SignIn() {
  const { login, register } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setMsg('');
    try {
      if (mode === 'in') await login(email, password);
      else await register(email, password, name);
      router.push('/my-bets');
    } catch (e2: any) {
      setMsg(mode === 'in' ? (e2?.response?.status === 401 ? 'Wrong email or password, or the account is disabled.' : err(e2, 'Could not sign in')) : err(e2, 'Could not create the account'));
    } finally { setBusy(false); }
  };
  return (
    <div className="card max-w-md">
      <div className="flex gap-2 mb-4">
        <button onClick={() => setMode('in')} className={`btn btn-sm ${mode === 'in' ? 'btn-primary' : 'btn-secondary'}`}>Sign in</button>
        <button onClick={() => setMode('up')} className={`btn btn-sm ${mode === 'up' ? 'btn-primary' : 'btn-secondary'}`}>Create account</button>
      </div>
      <form onSubmit={submit} className="space-y-3">
        {mode === 'up' && (
          <label className="block text-sm"><span className="text-text-muted">Name (optional)</span>
            <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} className="input w-full mt-1" autoComplete="name" />
          </label>
        )}
        <label className="block text-sm"><span className="text-text-muted">Email</span>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input w-full mt-1" autoComplete="email" />
        </label>
        <label className="block text-sm"><span className="text-text-muted">Password{mode === 'up' ? ' (at least 8 characters, not all numbers)' : ''}</span>
          <input type="password" required minLength={mode === 'up' ? 8 : 1} value={password} onChange={(e) => setPassword(e.target.value)} className="input w-full mt-1" autoComplete={mode === 'up' ? 'new-password' : 'current-password'} />
        </label>
        {msg && <p className="text-sm text-red-400">{msg}</p>}
        <button disabled={busy} className="btn btn-primary w-full">{busy ? 'Please wait…' : mode === 'in' ? 'Sign in' : 'Create account'}</button>
      </form>
      <p className="text-xs text-text-muted mt-4">
        {mode === 'up'
          ? 'Bets and favourites already saved on this device are added to your new account. We store your email, a hashed password and what you save in the app. Bet Hope admins can see your email and saved bets. You can delete your account at any time. 18+ only.'
          : 'Forgot your password? Ask the Bet Hope admin for a temporary one (there is no email reset yet).'}
      </p>
    </div>
  );
}

function Profile() {
  const { user, logout, setUser } = useAuth();
  const bets = useMyBets((s) => s.bets);
  const router = useRouter();
  const [name, setName] = useState(user?.name || '');
  const [oldPw, setOldPw] = useState(''); const [newPw, setNewPw] = useState('');
  const [delPw, setDelPw] = useState('');
  const [msg, setMsg] = useState<{ t: string; ok: boolean } | null>(null);
  if (!user) return null;
  const saveName = async () => { try { setUser(await accountApi.update({ name } as any)); setMsg({ t: 'Saved', ok: true }); } catch (e) { setMsg({ t: err(e, 'Could not save'), ok: false }); } };
  const changePw = async () => { try { await accountApi.changePassword(oldPw, newPw); setOldPw(''); setNewPw(''); setMsg({ t: 'Password changed', ok: true }); } catch (e) { setMsg({ t: err(e, 'Could not change password'), ok: false }); } };
  const del = async () => {
    if (!confirm('Delete your account and all saved bets? This cannot be undone.')) return;
    try { await accountApi.deleteAccount(delPw); logout(); router.push('/'); } catch (e) { setMsg({ t: err(e, 'Could not delete'), ok: false }); }
  };
  return (
    <div className="content-grid">
      <div className="col-span-6">
        <div className="card">
          <div className="card-header">
            <div className="card-icon"><UserCircle2 className="w-5 h-5" /></div>
            <div className="min-w-0">
              <h2 className="card-title truncate">{user.name || user.email}</h2>
              <p className="card-desc truncate">{user.email} · since {new Date(user.joined).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</p>
            </div>
          </div>
          <p className="text-sm text-text-sec mb-4">{bets.length} bet{bets.length === 1 ? '' : 's'} saved · <Link href="/my-bets" className="text-brand">My bets</Link></p>
          {user.is_staff && (
            <Link href="/admin" className="btn btn-secondary btn-sm mb-4"><ShieldCheck className="w-4 h-4" /> Admin: all users</Link>
          )}
          <label className="block text-sm mb-3"><span className="text-text-muted">Name</span>
            <div className="flex gap-2 mt-1"><input value={name} onChange={(e) => setName(e.target.value)} className="input flex-1" maxLength={60} /><button onClick={saveName} className="btn btn-secondary btn-sm">Save</button></div>
          </label>
          <button onClick={() => { logout(); router.push('/'); }} className="btn btn-secondary btn-sm"><LogOut className="w-4 h-4" /> Sign out</button>
          <p className="text-[11px] text-text-muted mt-2">Signing out removes your bets and favourites from this device; they stay in your account.</p>
        </div>
      </div>
      <div className="col-span-6">
        <div className="card">
          <h2 className="card-title mb-3">Change password</h2>
          <div className="space-y-2">
            <input type="password" placeholder="Current password" value={oldPw} onChange={(e) => setOldPw(e.target.value)} className="input w-full" autoComplete="current-password" />
            <input type="password" placeholder="New password" value={newPw} onChange={(e) => setNewPw(e.target.value)} className="input w-full" autoComplete="new-password" />
            <button onClick={changePw} disabled={!oldPw || newPw.length < 8} className="btn btn-secondary btn-sm">Change password</button>
          </div>
        </div>
        <div className="card">
          <h2 className="card-title mb-2 text-red-400">Delete account</h2>
          <p className="text-xs text-text-muted mb-2">Removes your account, saved bets and favourites from Bet Hope for good.</p>
          <div className="flex gap-2">
            <input type="password" placeholder="Password" value={delPw} onChange={(e) => setDelPw(e.target.value)} className="input flex-1" autoComplete="current-password" />
            <button onClick={del} disabled={!delPw} className="btn btn-sm bg-red-500/15 text-red-400 border border-red-500/30">Delete</button>
          </div>
        </div>
        {msg && <p className={`text-sm ${msg.ok ? 'text-green-500' : 'text-red-400'}`}>{msg.t}</p>}
      </div>
    </div>
  );
}
