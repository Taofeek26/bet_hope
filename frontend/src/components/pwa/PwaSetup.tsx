'use client';

import { useEffect } from 'react';
import { usePwa, isStandalone, pushSupported, updatePush } from '@/lib/pwa';
import { useFavoritesStore } from '@/lib/store';

/** Registers the service worker, catches the install prompt, keeps push teams in sync. */
export function PwaSetup() {
  const { setInstallEvent, setInstalled } = usePwa();
  const favoriteTeams = useFavoritesStore((s) => s.favoriteTeams);

  useEffect(() => {
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
    setInstalled(isStandalone());
    const onPrompt = (e: Event) => { e.preventDefault(); setInstallEvent(e); };
    const onInstalled = () => { setInstalled(true); setInstallEvent(null); };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => { window.removeEventListener('beforeinstallprompt', onPrompt); window.removeEventListener('appinstalled', onInstalled); };
  }, [setInstallEvent, setInstalled]);

  // Favourite teams decide who gets "your team plays today" alerts.
  useEffect(() => {
    if (!pushSupported() || Notification.permission !== 'granted') return;
    let prefs = {};
    try { prefs = JSON.parse(localStorage.getItem('bethope_push_prefs') || '{}'); } catch { /* defaults */ }
    updatePush(favoriteTeams, prefs).catch(() => {});
  }, [favoriteTeams]);

  return null;
}
