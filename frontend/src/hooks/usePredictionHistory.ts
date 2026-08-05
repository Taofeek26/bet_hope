'use client';

import { useSettings } from '@/contexts/SettingsContext';

// Settings > Data & Privacy > Save Prediction History. There's no
// prediction detail route to hook a "viewed" event off of, so this tracks
// a real, deliberate interaction instead — generating AI analysis for a
// prediction — rather than a vague "rendered in a list" event that isn't
// meaningfully "history."
const STORAGE_KEY = 'bethope_prediction_history';
const MAX_ENTRIES = 200;

export interface PredictionHistoryEntry {
  predictionId: number;
  homeTeam?: string;
  awayTeam?: string;
  viewedAt: string;
}

export function readPredictionHistory(): PredictionHistoryEntry[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

export function clearPredictionHistory() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function usePredictionHistory() {
  const { settings } = useSettings();

  const record = (predictionId: number, homeTeam?: string, awayTeam?: string) => {
    if (!settings.savePredictionHistory || typeof window === 'undefined') return;
    const existing = readPredictionHistory().filter((e) => e.predictionId !== predictionId);
    const next = [{ predictionId, homeTeam, awayTeam, viewedAt: new Date().toISOString() }, ...existing].slice(
      0,
      MAX_ENTRIES
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  return { record, history: readPredictionHistory() };
}
