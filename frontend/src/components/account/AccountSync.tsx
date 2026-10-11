'use client';

import { useEffect, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { accountApi } from '@/lib/api';
import { useMyBets } from '@/lib/mybets';
import { useFavoritesStore } from '@/lib/store';

/**
 * Keeps the signed-in user's My bets, favourites and weekly limit on the
 * server (Phase 7). On sign-in, anything saved on this device is merged into
 * the account; after that, every change is sent. On sign-out the device copy
 * is cleared, so the next person on a shared phone starts empty.
 */
export function AccountSync() {
  const { user, load } = useAuth();
  const ready = useRef(false);

  useEffect(() => { load(); }, [load]);

  // Sign-out (button, or an expired session): clear this device's personal data.
  useEffect(() => {
    const clear = () => {
      ready.current = false;
      useMyBets.setState({ bets: [], weeklyLimit: null });
      useFavoritesStore.setState({ favoriteTeams: [], favoriteLeagues: [] } as any);
      useAuth.getState().setUser(null);
    };
    window.addEventListener('bethope-signed-out', clear);
    return () => window.removeEventListener('bethope-signed-out', clear);
  }, []);

  // Sign-in: merge device + account.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    useAuth.getState().setSyncing(true);
    (async () => {
      try {
        const server = await accountApi.bets();
        const local = useMyBets.getState().bets;
        const ids = new Set(server.map((b: any) => b.id));
        const toUpload = local.filter((b) => !ids.has(b.id));
        if (toUpload.length) await accountApi.saveBets(toUpload);
        const merged = [...server, ...toUpload].sort((a: any, b: any) => Date.parse(b.placedAt) - Date.parse(a.placedAt));
        const fav = useFavoritesStore.getState() as any;
        const teams = Array.from(new Set([...(user.favourite_teams || []), ...(fav.favoriteTeams || [])]));
        const leagues = Array.from(new Set([...(user.favourite_leagues || []), ...(fav.favoriteLeagues || [])]));
        const limit = user.weekly_limit ?? useMyBets.getState().weeklyLimit;
        await accountApi.update({ favourite_teams: teams, favourite_leagues: leagues, weekly_limit: limit } as any);
        if (cancelled) return;
        useMyBets.setState({ bets: merged as any, weeklyLimit: limit ?? null });
        useFavoritesStore.setState({ favoriteTeams: teams, favoriteLeagues: leagues } as any);
        ready.current = true;
      } catch { /* offline: try again on next load */ }
      finally { useAuth.getState().setSyncing(false); }
    })();
    return () => { cancelled = true; };
  }, [user]);

  // After that: push every change.
  useEffect(() => {
    const unBets = useMyBets.subscribe((s, prev) => {
      if (!ready.current || !useAuth.getState().user) return;
      const before = new Set(prev.bets.map((b) => b.id));
      const added = s.bets.filter((b) => !before.has(b.id));
      const removed = prev.bets.filter((b) => !s.bets.some((x) => x.id === b.id));
      if (added.length) accountApi.saveBets(added).catch(() => {});
      for (const r of removed) accountApi.deleteBet(r.id).catch(() => {});
      if (s.weeklyLimit !== prev.weeklyLimit) accountApi.update({ weekly_limit: s.weeklyLimit } as any).catch(() => {});
    });
    const unFav = useFavoritesStore.subscribe((s: any, prev: any) => {
      if (!ready.current || !useAuth.getState().user) return;
      if (s.favoriteTeams !== prev.favoriteTeams || s.favoriteLeagues !== prev.favoriteLeagues) {
        accountApi.update({ favourite_teams: s.favoriteTeams, favourite_leagues: s.favoriteLeagues } as any).catch(() => {});
      }
    });
    return () => { unBets(); unFav(); };
  }, []);

  return null;
}
