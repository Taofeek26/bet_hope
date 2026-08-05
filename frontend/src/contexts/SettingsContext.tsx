'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export interface AppSettings {
  // General
  defaultView: 'dashboard' | 'predictions' | 'matches';
  predictionsPerPage: 10 | 25 | 50;
  autoRefresh: boolean;
  // Notifications — scoped to what's actually deliverable client-side (the
  // browser Notification API while a tab is open). There's no email/push
  // infrastructure in this deployment, so no "email digest" option here —
  // that would be a toggle for a feature that doesn't exist.
  matchNotifications: boolean;
  predictionAlerts: boolean;
  valueBetAlerts: boolean;
  // Region & Odds
  timezone: string; // IANA name, or 'local' to use the browser's own zone
  oddsFormat: 'decimal' | 'fractional' | 'american';
  dateFormat: 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD';
  // Appearance
  theme: 'dark' | 'light' | 'system';
  compactMode: boolean;
  showAnimations: boolean;
  // Data & Privacy
  savePredictionHistory: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = {
  defaultView: 'dashboard',
  predictionsPerPage: 25,
  autoRefresh: true,
  matchNotifications: true,
  predictionAlerts: true,
  valueBetAlerts: true,
  timezone: 'local',
  oddsFormat: 'decimal',
  dateFormat: 'MM/DD/YYYY',
  theme: 'dark',
  compactMode: false,
  showAnimations: true,
  savePredictionHistory: true,
};

const STORAGE_KEY = 'bethope_settings';

interface SettingsContextType {
  settings: AppSettings;
  updateSetting: <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => void;
  resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

function loadSettings(): AppSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function applyDomEffects(settings: AppSettings) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;

  const resolvedTheme =
    settings.theme === 'system'
      ? window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark'
      : settings.theme;
  root.setAttribute('data-theme', resolvedTheme);
  root.classList.toggle('dark', resolvedTheme === 'dark');
  root.classList.toggle('light', resolvedTheme === 'light');

  root.classList.toggle('compact', settings.compactMode);
  root.classList.toggle('no-animations', !settings.showAnimations);
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const loaded = loadSettings();
    setSettings(loaded);
    applyDomEffects(loaded);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (settings.theme !== 'system' || typeof window === 'undefined') return;
    const mq = window.matchMedia('(prefers-color-scheme: light)');
    const handler = () => applyDomEffects(settings);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.theme]);

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      }
      applyDomEffects(next);
      return next;
    });
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_SETTINGS));
    }
    applyDomEffects(DEFAULT_SETTINGS);
  };

  // Render with defaults until hydrated to avoid a flash of mismatched
  // settings between server-rendered markup and the persisted client state.
  if (!hydrated) {
    return (
      <SettingsContext.Provider value={{ settings: DEFAULT_SETTINGS, updateSetting, resetSettings }}>
        {children}
      </SettingsContext.Provider>
    );
  }

  return (
    <SettingsContext.Provider value={{ settings, updateSetting, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
