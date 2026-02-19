import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { League, Match } from '@/types';

// App state store
interface AppState {
  // Selected league
  selectedLeague: string | null;
  setSelectedLeague: (code: string | null) => void;

  // Sidebar state
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // Theme
  theme: 'dark' | 'light';
  toggleTheme: () => void;

  // Filters
  confidenceFilter: number;
  setConfidenceFilter: (value: number) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      selectedLeague: null,
      setSelectedLeague: (code) => set({ selectedLeague: code }),

      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      theme: 'dark',
      toggleTheme: () =>
        set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),

      confidenceFilter: 0.5,
      setConfidenceFilter: (value) => set({ confidenceFilter: value }),
    }),
    {
      name: 'bet-hope-storage',
      partialize: (state) => ({
        selectedLeague: state.selectedLeague,
        theme: state.theme,
        confidenceFilter: state.confidenceFilter,
      }),
    }
  )
);

// Favorites store
interface FavoritesState {
  favoriteTeams: number[];
  favoriteLeagues: string[];
  addFavoriteTeam: (id: number) => void;
  removeFavoriteTeam: (id: number) => void;
  toggleFavoriteTeam: (id: number) => void;
  addFavoriteLeague: (code: string) => void;
  removeFavoriteLeague: (code: string) => void;
  toggleFavoriteLeague: (code: string) => void;
}

export const useFavoritesStore = create<FavoritesState>()(
  persist(
    (set) => ({
      favoriteTeams: [],
      favoriteLeagues: [],

      addFavoriteTeam: (id) =>
        set((state) => ({
          favoriteTeams: [...state.favoriteTeams, id],
        })),

      removeFavoriteTeam: (id) =>
        set((state) => ({
          favoriteTeams: state.favoriteTeams.filter((t) => t !== id),
        })),

      toggleFavoriteTeam: (id) =>
        set((state) => ({
          favoriteTeams: state.favoriteTeams.includes(id)
            ? state.favoriteTeams.filter((t) => t !== id)
            : [...state.favoriteTeams, id],
        })),

      addFavoriteLeague: (code) =>
        set((state) => ({
          favoriteLeagues: [...state.favoriteLeagues, code],
        })),

      removeFavoriteLeague: (code) =>
        set((state) => ({
          favoriteLeagues: state.favoriteLeagues.filter((l) => l !== code),
        })),

      toggleFavoriteLeague: (code) =>
        set((state) => ({
          favoriteLeagues: state.favoriteLeagues.includes(code)
            ? state.favoriteLeagues.filter((l) => l !== code)
            : [...state.favoriteLeagues, code],
        })),
    }),
    {
      name: 'bet-hope-favorites',
    }
  )
);

// Live matches store (non-persisted)
interface LiveMatchesState {
  liveMatches: Match[];
  setLiveMatches: (matches: Match[]) => void;
  updateMatch: (id: number, data: Partial<Match>) => void;
}

export const useLiveMatchesStore = create<LiveMatchesState>((set) => ({
  liveMatches: [],
  setLiveMatches: (matches) => set({ liveMatches: matches }),
  updateMatch: (id, data) =>
    set((state) => ({
      liveMatches: state.liveMatches.map((m) =>
        m.id === id ? { ...m, ...data } : m
      ),
    })),
}));
