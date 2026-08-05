'use client';

import { useEffect, useRef } from 'react';
import { useSettings } from '@/contexts/SettingsContext';
import { useLiveMatches, useDailyPicks, useValueBets } from '@/hooks/useApi';

// Settings > Notifications. There's no email/push backend in this
// deployment, so these use the browser's own Notification API — real
// alerts, scoped to what's actually observable client-side: a match going
// live, a new high-confidence pick appearing, a new value bet appearing.
// Fires only while a tab is open and permission is granted; that's an
// honest boundary given what infrastructure actually exists, not a
// simulation of push notifications the app can't really deliver.
function notify(title: string, body: string) {
  if (typeof window === 'undefined' || !('Notification' in window)) return;
  if (Notification.permission !== 'granted') return;
  new Notification(title, { body, icon: '/favicon.ico' });
}

export function NotificationWatcher() {
  const { settings } = useSettings();
  const { data: liveMatches } = useLiveMatches();
  const { data: dailyPicks } = useDailyPicks();
  const { data: valueBets } = useValueBets();

  const seenLiveIds = useRef<Set<number>>(new Set());
  const seenPickIds = useRef<Set<number>>(new Set());
  const seenValueBetIds = useRef<Set<string>>(new Set());
  const initialized = useRef(false);

  useEffect(() => {
    if (settings.matchNotifications && typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'default') {
        Notification.requestPermission();
      }
    }
  }, [settings.matchNotifications]);

  useEffect(() => {
    if (!liveMatches?.matches) return;
    const currentIds = new Set<number>(liveMatches.matches.map((m: any) => m.id));

    // Skip the very first tick — otherwise every match already live when
    // the tab opens fires a notification, which isn't "new" to the user.
    if (initialized.current && settings.matchNotifications) {
      for (const m of liveMatches.matches) {
        if (!seenLiveIds.current.has(m.id)) {
          notify('Match is live', `${m.home_team?.name || m.home_team} vs ${m.away_team?.name || m.away_team} just kicked off`);
        }
      }
    }
    seenLiveIds.current = currentIds;
    initialized.current = true;
  }, [liveMatches, settings.matchNotifications]);

  const picksInitialized = useRef(false);
  useEffect(() => {
    if (!dailyPicks?.picks) return;
    const currentIds = new Set<number>(dailyPicks.picks.map((p: any) => p.prediction?.id).filter(Boolean));

    if (picksInitialized.current && settings.predictionAlerts) {
      for (const p of dailyPicks.picks) {
        const id = p.prediction?.id;
        if (id && !seenPickIds.current.has(id)) {
          notify(
            'New high-confidence pick',
            `${p.match?.home_team} vs ${p.match?.away_team} — ${p.prediction?.outcome} (${Math.round((p.prediction?.confidence || 0) * 100)}%)`
          );
        }
      }
    }
    seenPickIds.current = currentIds;
    picksInitialized.current = true;
  }, [dailyPicks, settings.predictionAlerts]);

  const valueBetsInitialized = useRef(false);
  useEffect(() => {
    if (!valueBets?.value_bets) return;
    const currentIds = new Set<string>(
      valueBets.value_bets.map((b: any) => `${b.match?.id}-${b.market}`)
    );

    if (valueBetsInitialized.current && settings.valueBetAlerts) {
      for (const b of valueBets.value_bets) {
        const id = `${b.match?.id}-${b.market}`;
        if (!seenValueBetIds.current.has(id)) {
          notify('New value bet', `${b.market} — edge +${Math.round((b.edge || 0) * 100)}%`);
        }
      }
    }
    seenValueBetIds.current = currentIds;
    valueBetsInitialized.current = true;
  }, [valueBets, settings.valueBetAlerts]);

  return null;
}
