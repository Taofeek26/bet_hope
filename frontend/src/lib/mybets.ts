import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { SlipSelection } from '@/lib/betslip';

// My bets (Phase 6): bets you actually placed at your bookmaker, kept on
// this device and settled from the final scores. No account, nothing sent.
export interface PlacedBet {
  id: string;
  placedAt: string;
  bookmaker: string;
  stake: number;          // naira
  odds: number;           // total odds you got
  selections: SlipSelection[];
}

export type LegResult = 'won' | 'lost' | 'void' | 'pending';

interface MyBetsState {
  bets: PlacedBet[];
  weeklyLimit: number | null;  // naira, set by the user
  add: (b: Omit<PlacedBet, 'id' | 'placedAt'>) => void;
  remove: (id: string) => void;
  setWeeklyLimit: (n: number | null) => void;
}

export const useMyBets = create<MyBetsState>()(
  persist(
    (set) => ({
      bets: [],
      weeklyLimit: null,
      add: (b) => set((s) => ({ bets: [{ ...b, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, placedAt: new Date().toISOString() }, ...s.bets] })),
      remove: (id) => set((s) => ({ bets: s.bets.filter((b) => b.id !== id) })),
      setWeeklyLimit: (weeklyLimit) => set({ weeklyLimit }),
    }),
    { name: 'bethope-mybets' },
  ),
);

/**
 * Settle one selection from the final score. Keys match lib/betslip and the
 * backend markets (apps/predictions/markets.py).
 */
export function legResult(key: string, home: number | null | undefined, away: number | null | undefined, status?: string): LegResult {
  if (status === 'postponed' || status === 'cancelled') return 'void';
  if (status !== 'finished' || home == null || away == null) return 'pending';
  const h = home, a = away, t = h + a;
  const win = (c: boolean): LegResult => (c ? 'won' : 'lost');
  switch (key) {
    case '1': return win(h > a);
    case 'X': return win(h === a);
    case '2': return win(a > h);
    case '1X': return win(h >= a);
    case '12': return win(h !== a);
    case 'X2': return win(a >= h);
    case 'DNB1': return h === a ? 'void' : win(h > a);
    case 'DNB2': return h === a ? 'void' : win(a > h);
    case 'GG': return win(h > 0 && a > 0);
    case 'NG': return win(!(h > 0 && a > 0));
    case 'HCS': return win(a === 0);
    case 'ACS': return win(h === 0);
  }
  let m = key.match(/^([OU])(\d+\.5)$/);
  if (m) return win(m[1] === 'O' ? t > Number(m[2]) : t < Number(m[2]));
  m = key.match(/^([HA])O(\d+\.5)$/);
  if (m) return win((m[1] === 'H' ? h : a) > Number(m[2]));
  m = key.match(/^CS(\d+)-(\d+)$/);
  if (m) return win(h === Number(m[1]) && a === Number(m[2]));
  return 'pending';
}

/** A bet: lost if any leg lost; won when every leg is won or void (void legs count as odds 1). */
export function betResult(legs: LegResult[]): LegResult {
  if (legs.includes('lost')) return 'lost';
  if (legs.includes('pending')) return 'pending';
  if (legs.every((l) => l === 'void')) return 'void';
  return 'won';
}
