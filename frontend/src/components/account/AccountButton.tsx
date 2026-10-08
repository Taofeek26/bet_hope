'use client';

import Link from 'next/link';
import { UserCircle2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';

/** Top-bar account entry (Phase 7): initial when signed in, icon otherwise. */
export function AccountButton() {
  const { user } = useAuth();
  const label = user ? (user.name || user.email).trim() : '';
  return (
    <Link href="/account" aria-label={user ? `My account (${label})` : 'Sign in'} title={user ? label : 'Sign in'}
      className="h-9 w-9 rounded-full flex items-center justify-center border border-border-dim hover:border-brand/60 flex-shrink-0">
      {user ? <span className="text-sm font-bold text-brand">{label.charAt(0).toUpperCase()}</span> : <UserCircle2 className="w-5 h-5 text-text-muted" />}
    </Link>
  );
}
