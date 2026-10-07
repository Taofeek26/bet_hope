import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// The bet slip (Phase 5, step 3): selections the user builds here, then
// copies to their own bookmaker. Kept in this browser only. Nothing is
// staked from Bet Hope.
export interface SlipSelection {
  matchId: number;
  match: string;        // "Arsenal v Leeds"
  kickoff?: string;     // ISO or date
  league?: string;
  // For "Load on SportyBet" (browser extension): find the same match there.
  home?: string;
  away?: string;
  leagueCode?: string;  // E0, SP1, ... (Bet Hope codes)
  kickoffAt?: string | null; // exact UTC kickoff, if known
  group: string;        // "1X2", "GG/NG", "Over/Under", ...
  key: string;          // "1", "GG", "O2.5", ...
  label: string;        // "Arsenal to win"
  probability: number;  // model probability, 0-1
  fairOdds: number;     // 1 / probability
  bestOdds?: number | null;
  yourOdds?: number | null; // price at the user's bookmaker, typed in the slip
}

interface SlipState {
  selections: SlipSelection[];
  open: boolean;
  stake: number;
  // One selection per match: most bookmakers don't allow two picks from the
  // same match in one accumulator, so a new pick replaces the old one.
  toggle: (s: SlipSelection) => void;
  remove: (matchId: number) => void;
  setYourOdds: (matchId: number, odds: number | null) => void;
  setStake: (stake: number) => void;
  clear: () => void;
  setOpen: (open: boolean) => void;
}

export const useBetSlip = create<SlipState>()(
  persist(
    (set) => ({
      selections: [],
      open: false,
      stake: 1000,
      toggle: (s) =>
        set((st) => {
          const same = st.selections.find((x) => x.matchId === s.matchId && x.key === s.key);
          if (same) return { selections: st.selections.filter((x) => x !== same) };
          return { selections: [...st.selections.filter((x) => x.matchId !== s.matchId), s], open: true };
        }),
      remove: (matchId) => set((st) => ({ selections: st.selections.filter((x) => x.matchId !== matchId) })),
      setYourOdds: (matchId, odds) =>
        set((st) => ({ selections: st.selections.map((x) => (x.matchId === matchId ? { ...x, yourOdds: odds } : x)) })),
      setStake: (stake) => set({ stake }),
      clear: () => set({ selections: [] }),
      setOpen: (open) => set({ open }),
    }),
    { name: 'bethope-betslip', partialize: (s) => ({ selections: s.selections, stake: s.stake }) },
  ),
);

export const isInSlip = (sel: SlipSelection[], matchId: number, key: string) =>
  sel.some((x) => x.matchId === matchId && x.key === key);
