# Bet_Hope State Management

## Overview

State management uses a hybrid approach:
- **Zustand** — Client-side state (auth, UI, preferences)
- **React Query (TanStack Query)** — Server state (API data, caching)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STATE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐           ┌─────────────────┐                 │
│  │   ZUSTAND       │           │  REACT QUERY    │                 │
│  │  Client State   │           │  Server State   │                 │
│  ├─────────────────┤           ├─────────────────┤                 │
│  │ • Auth state    │           │ • Predictions   │                 │
│  │ • UI state      │           │ • Matches       │                 │
│  │ • Preferences   │           │ • Leagues       │                 │
│  │ • Filters       │           │ • Teams         │                 │
│  │ • Modal state   │           │ • Analytics     │                 │
│  └─────────────────┘           └─────────────────┘                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Zustand Stores

### Store Structure

```
stores/
├── authStore.ts          # Authentication state
├── uiStore.ts            # UI preferences & modals
├── filtersStore.ts       # Data filters
├── notificationStore.ts  # Notifications/toasts
└── index.ts              # Combined exports
```

---

### Auth Store

Handles user authentication state with persistence.

```typescript
// stores/authStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User } from '@/types';

interface AuthState {
  // State
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (user: User, token: string, refreshToken: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  setLoading: (loading: boolean) => void;
  setTokens: (token: string, refreshToken: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: true,

      // Actions
      login: (user, token, refreshToken) =>
        set({
          user,
          token,
          refreshToken,
          isAuthenticated: true,
          isLoading: false,
        }),

      logout: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
        }),

      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),

      setLoading: (loading) => set({ isLoading: loading }),

      setTokens: (token, refreshToken) => set({ token, refreshToken }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selectors
export const selectUser = (state: AuthState) => state.user;
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated;
export const selectToken = (state: AuthState) => state.token;
```

**Usage:**

```tsx
// In component
import { useAuthStore } from '@/stores/authStore';

function UserProfile() {
  const { user, logout } = useAuthStore();

  return (
    <div>
      <p>Welcome, {user?.name}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

// Using selectors (optimized)
function UserName() {
  const user = useAuthStore(selectUser);
  return <span>{user?.name}</span>;
}
```

---

### UI Store

Manages UI state like sidebars, modals, and theme.

```typescript
// stores/uiStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface ModalState {
  isOpen: boolean;
  type: string | null;
  data: unknown;
}

interface UIState {
  // Theme
  theme: Theme;
  setTheme: (theme: Theme) => void;

  // Sidebar
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Modal
  modal: ModalState;
  openModal: (type: string, data?: unknown) => void;
  closeModal: () => void;

  // Mobile
  isMobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;

  // Notifications panel
  notificationsPanelOpen: boolean;
  toggleNotificationsPanel: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Theme
      theme: 'system',
      setTheme: (theme) => set({ theme }),

      // Sidebar
      sidebarOpen: true,
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Modal
      modal: { isOpen: false, type: null, data: null },
      openModal: (type, data = null) =>
        set({ modal: { isOpen: true, type, data } }),
      closeModal: () =>
        set({ modal: { isOpen: false, type: null, data: null } }),

      // Mobile
      isMobileMenuOpen: false,
      setMobileMenuOpen: (open) => set({ isMobileMenuOpen: open }),

      // Notifications
      notificationsPanelOpen: false,
      toggleNotificationsPanel: () =>
        set((state) => ({
          notificationsPanelOpen: !state.notificationsPanelOpen,
        })),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
```

**Usage:**

```tsx
// Theme toggle
function ThemeToggle() {
  const { theme, setTheme } = useUIStore();

  return (
    <select value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="system">System</option>
    </select>
  );
}

// Modal usage
function MatchList() {
  const { openModal } = useUIStore();

  return (
    <button onClick={() => openModal('match-details', { matchId: 123 })}>
      View Details
    </button>
  );
}

// Modal handler
function ModalManager() {
  const { modal, closeModal } = useUIStore();

  if (!modal.isOpen) return null;

  switch (modal.type) {
    case 'match-details':
      return <MatchDetailsModal data={modal.data} onClose={closeModal} />;
    case 'prediction':
      return <PredictionModal data={modal.data} onClose={closeModal} />;
    default:
      return null;
  }
}
```

---

### Filters Store

Manages filter state for data views.

```typescript
// stores/filtersStore.ts
import { create } from 'zustand';

interface DateRange {
  from: Date | null;
  to: Date | null;
}

interface FiltersState {
  // Predictions filters
  predictionFilters: {
    leagueId: number | null;
    minConfidence: number;
    dateRange: DateRange;
    outcome: 'HOME' | 'DRAW' | 'AWAY' | null;
  };
  setPredictionFilters: (filters: Partial<FiltersState['predictionFilters']>) => void;
  resetPredictionFilters: () => void;

  // Matches filters
  matchFilters: {
    leagueId: number | null;
    teamId: number | null;
    status: string | null;
    dateRange: DateRange;
  };
  setMatchFilters: (filters: Partial<FiltersState['matchFilters']>) => void;
  resetMatchFilters: () => void;

  // League filter (global)
  selectedLeagueId: number | null;
  setSelectedLeague: (id: number | null) => void;
}

const defaultPredictionFilters = {
  leagueId: null,
  minConfidence: 0,
  dateRange: { from: null, to: null },
  outcome: null,
};

const defaultMatchFilters = {
  leagueId: null,
  teamId: null,
  status: null,
  dateRange: { from: null, to: null },
};

export const useFiltersStore = create<FiltersState>((set) => ({
  // Predictions
  predictionFilters: defaultPredictionFilters,
  setPredictionFilters: (filters) =>
    set((state) => ({
      predictionFilters: { ...state.predictionFilters, ...filters },
    })),
  resetPredictionFilters: () =>
    set({ predictionFilters: defaultPredictionFilters }),

  // Matches
  matchFilters: defaultMatchFilters,
  setMatchFilters: (filters) =>
    set((state) => ({
      matchFilters: { ...state.matchFilters, ...filters },
    })),
  resetMatchFilters: () => set({ matchFilters: defaultMatchFilters }),

  // Global league
  selectedLeagueId: null,
  setSelectedLeague: (id) => set({ selectedLeagueId: id }),
}));
```

---

### Notification Store

Toast/notification management.

```typescript
// stores/notificationStore.ts
import { create } from 'zustand';

type NotificationType = 'success' | 'error' | 'warning' | 'info';

interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number;
}

interface NotificationState {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],

  addNotification: (notification) => {
    const id = Math.random().toString(36).slice(2);
    const newNotification = { ...notification, id };

    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));

    // Auto-remove after duration
    const duration = notification.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }));
      }, duration);
    }
  },

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearAll: () => set({ notifications: [] }),
}));

// Helper hook
export function useNotify() {
  const { addNotification } = useNotificationStore();

  return {
    success: (title: string, message?: string) =>
      addNotification({ type: 'success', title, message }),
    error: (title: string, message?: string) =>
      addNotification({ type: 'error', title, message }),
    warning: (title: string, message?: string) =>
      addNotification({ type: 'warning', title, message }),
    info: (title: string, message?: string) =>
      addNotification({ type: 'info', title, message }),
  };
}
```

**Usage:**

```tsx
function SaveButton() {
  const notify = useNotify();

  const handleSave = async () => {
    try {
      await saveData();
      notify.success('Saved!', 'Your changes have been saved.');
    } catch (error) {
      notify.error('Error', 'Failed to save changes.');
    }
  };

  return <button onClick={handleSave}>Save</button>;
}
```

---

## React Query

### Setup

```typescript
// lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes (formerly cacheTime)
      retry: 2,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});
```

```tsx
// app/providers.tsx
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '@/lib/queryClient';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

---

### Query Keys

Centralized query key management.

```typescript
// lib/queryKeys.ts
export const queryKeys = {
  // Predictions
  predictions: {
    all: ['predictions'] as const,
    upcoming: () => [...queryKeys.predictions.all, 'upcoming'] as const,
    today: () => [...queryKeys.predictions.all, 'today'] as const,
    byMatch: (matchId: number) =>
      [...queryKeys.predictions.all, 'match', matchId] as const,
    byLeague: (leagueId: number) =>
      [...queryKeys.predictions.all, 'league', leagueId] as const,
    history: (filters?: PredictionFilters) =>
      [...queryKeys.predictions.all, 'history', filters] as const,
  },

  // Matches
  matches: {
    all: ['matches'] as const,
    list: (filters?: MatchFilters) =>
      [...queryKeys.matches.all, 'list', filters] as const,
    live: () => [...queryKeys.matches.all, 'live'] as const,
    detail: (id: number) => [...queryKeys.matches.all, 'detail', id] as const,
  },

  // Leagues
  leagues: {
    all: ['leagues'] as const,
    list: () => [...queryKeys.leagues.all, 'list'] as const,
    detail: (id: number) => [...queryKeys.leagues.all, 'detail', id] as const,
    standings: (id: number, season?: string) =>
      [...queryKeys.leagues.all, 'standings', id, season] as const,
    fixtures: (id: number) =>
      [...queryKeys.leagues.all, 'fixtures', id] as const,
  },

  // Teams
  teams: {
    all: ['teams'] as const,
    list: (leagueId?: number) =>
      [...queryKeys.teams.all, 'list', leagueId] as const,
    detail: (id: number) => [...queryKeys.teams.all, 'detail', id] as const,
    form: (id: number) => [...queryKeys.teams.all, 'form', id] as const,
    fixtures: (id: number) =>
      [...queryKeys.teams.all, 'fixtures', id] as const,
  },

  // Analytics
  analytics: {
    all: ['analytics'] as const,
    modelPerformance: (period?: string) =>
      [...queryKeys.analytics.all, 'model-performance', period] as const,
  },
};
```

---

### Custom Hooks

#### usePredictions

```typescript
// hooks/usePredictions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { predictionsApi } from '@/lib/api/predictions';
import type { Prediction, PredictionFilters } from '@/types';

// Upcoming predictions
export function useUpcomingPredictions() {
  return useQuery({
    queryKey: queryKeys.predictions.upcoming(),
    queryFn: predictionsApi.getUpcoming,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Today's predictions
export function useTodayPredictions() {
  return useQuery({
    queryKey: queryKeys.predictions.today(),
    queryFn: predictionsApi.getToday,
    staleTime: 5 * 60 * 1000,
  });
}

// Single match prediction
export function useMatchPrediction(matchId: number) {
  return useQuery({
    queryKey: queryKeys.predictions.byMatch(matchId),
    queryFn: () => predictionsApi.getByMatch(matchId),
    enabled: !!matchId,
  });
}

// Predictions by league
export function useLeaguePredictions(leagueId: number) {
  return useQuery({
    queryKey: queryKeys.predictions.byLeague(leagueId),
    queryFn: () => predictionsApi.getByLeague(leagueId),
    enabled: !!leagueId,
  });
}

// Prediction history with filters
export function usePredictionHistory(filters?: PredictionFilters) {
  return useQuery({
    queryKey: queryKeys.predictions.history(filters),
    queryFn: () => predictionsApi.getHistory(filters),
    keepPreviousData: true,
  });
}
```

---

#### useMatches

```typescript
// hooks/useMatches.ts
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { matchesApi } from '@/lib/api/matches';

// Match list with filters
export function useMatches(filters?: MatchFilters) {
  return useQuery({
    queryKey: queryKeys.matches.list(filters),
    queryFn: () => matchesApi.getAll(filters),
    keepPreviousData: true,
  });
}

// Live matches (with polling)
export function useLiveMatches() {
  return useQuery({
    queryKey: queryKeys.matches.live(),
    queryFn: matchesApi.getLive,
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
  });
}

// Single match
export function useMatch(matchId: number) {
  return useQuery({
    queryKey: queryKeys.matches.detail(matchId),
    queryFn: () => matchesApi.getById(matchId),
    enabled: !!matchId,
  });
}
```

---

#### useLeagues

```typescript
// hooks/useLeagues.ts
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { leaguesApi } from '@/lib/api/leagues';

// All leagues
export function useLeagues() {
  return useQuery({
    queryKey: queryKeys.leagues.list(),
    queryFn: leaguesApi.getAll,
    staleTime: 60 * 60 * 1000, // 1 hour (leagues rarely change)
  });
}

// Single league
export function useLeague(leagueId: number) {
  return useQuery({
    queryKey: queryKeys.leagues.detail(leagueId),
    queryFn: () => leaguesApi.getById(leagueId),
    enabled: !!leagueId,
  });
}

// League standings
export function useLeagueStandings(leagueId: number, season?: string) {
  return useQuery({
    queryKey: queryKeys.leagues.standings(leagueId, season),
    queryFn: () => leaguesApi.getStandings(leagueId, season),
    enabled: !!leagueId,
  });
}
```

---

#### useTeams

```typescript
// hooks/useTeams.ts
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';
import { teamsApi } from '@/lib/api/teams';

// Team list
export function useTeams(leagueId?: number) {
  return useQuery({
    queryKey: queryKeys.teams.list(leagueId),
    queryFn: () => teamsApi.getAll(leagueId),
  });
}

// Single team
export function useTeam(teamId: number) {
  return useQuery({
    queryKey: queryKeys.teams.detail(teamId),
    queryFn: () => teamsApi.getById(teamId),
    enabled: !!teamId,
  });
}

// Team form
export function useTeamForm(teamId: number) {
  return useQuery({
    queryKey: queryKeys.teams.form(teamId),
    queryFn: () => teamsApi.getForm(teamId),
    enabled: !!teamId,
  });
}
```

---

### Prefetching

```typescript
// Prefetch on hover
function MatchCard({ match }: { match: Match }) {
  const queryClient = useQueryClient();

  const handleMouseEnter = () => {
    // Prefetch match details on hover
    queryClient.prefetchQuery({
      queryKey: queryKeys.matches.detail(match.id),
      queryFn: () => matchesApi.getById(match.id),
    });
  };

  return (
    <Card onMouseEnter={handleMouseEnter}>
      {/* ... */}
    </Card>
  );
}

// Prefetch on page load
async function prefetchDashboardData(queryClient: QueryClient) {
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: queryKeys.predictions.today(),
      queryFn: predictionsApi.getToday,
    }),
    queryClient.prefetchQuery({
      queryKey: queryKeys.matches.live(),
      queryFn: matchesApi.getLive,
    }),
    queryClient.prefetchQuery({
      queryKey: queryKeys.leagues.list(),
      queryFn: leaguesApi.getAll,
    }),
  ]);
}
```

---

### Optimistic Updates

```typescript
// Example: Favorite a team
export function useFavoriteTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: teamsApi.favorite,
    onMutate: async (teamId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.teams.detail(teamId) });

      // Snapshot previous value
      const previousTeam = queryClient.getQueryData(
        queryKeys.teams.detail(teamId)
      );

      // Optimistically update
      queryClient.setQueryData(
        queryKeys.teams.detail(teamId),
        (old: Team) => ({ ...old, isFavorite: true })
      );

      // Return context
      return { previousTeam };
    },
    onError: (err, teamId, context) => {
      // Rollback on error
      queryClient.setQueryData(
        queryKeys.teams.detail(teamId),
        context?.previousTeam
      );
    },
    onSettled: (data, error, teamId) => {
      // Refetch to ensure sync
      queryClient.invalidateQueries({
        queryKey: queryKeys.teams.detail(teamId),
      });
    },
  });
}
```

---

## WebSocket Integration

Real-time updates for live matches.

```typescript
// hooks/useWebSocket.ts
import { useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';

interface WebSocketMessage {
  type: 'MATCH_UPDATE' | 'PREDICTION_UPDATE' | 'LIVE_SCORE';
  payload: unknown;
}

export function useLiveUpdates() {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'LIVE_SCORE':
          // Update live matches cache
          queryClient.setQueryData(
            queryKeys.matches.live(),
            (old: Match[]) => {
              if (!old) return old;
              return old.map((match) =>
                match.id === message.payload.matchId
                  ? { ...match, ...message.payload }
                  : match
              );
            }
          );
          break;

        case 'MATCH_UPDATE':
          // Invalidate match queries
          queryClient.invalidateQueries({
            queryKey: queryKeys.matches.detail(message.payload.matchId),
          });
          break;

        case 'PREDICTION_UPDATE':
          // Invalidate prediction queries
          queryClient.invalidateQueries({
            queryKey: queryKeys.predictions.all,
          });
          break;
      }
    },
    [queryClient]
  );

  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL!);
    wsRef.current = ws;

    ws.onmessage = handleMessage;
    ws.onclose = () => {
      // Reconnect logic
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          wsRef.current = new WebSocket(process.env.NEXT_PUBLIC_WS_URL!);
        }
      }, 3000);
    };

    return () => {
      ws.close();
    };
  }, [handleMessage]);

  return wsRef.current;
}
```

---

## Best Practices

### 1. Store Separation

```
✅ DO: Separate stores by domain
├── authStore (auth only)
├── uiStore (UI only)
└── filtersStore (filters only)

❌ DON'T: One giant store with everything
```

### 2. Selector Usage

```typescript
// ✅ Use selectors to prevent unnecessary re-renders
const user = useAuthStore((state) => state.user);

// ❌ Don't destructure everything
const { user, token, login, logout, ... } = useAuthStore();
```

### 3. Query Key Consistency

```typescript
// ✅ Use centralized query keys
queryKey: queryKeys.predictions.byMatch(matchId)

// ❌ Don't use inline strings
queryKey: ['predictions', 'match', matchId]
```

### 4. Loading States

```tsx
// ✅ Handle all states
function PredictionsList() {
  const { data, isLoading, isError, error } = usePredictions();

  if (isLoading) return <Skeleton />;
  if (isError) return <Error message={error.message} />;
  if (!data?.length) return <Empty />;

  return <List data={data} />;
}
```

### 5. Invalidation Strategy

```typescript
// ✅ Invalidate related queries after mutations
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.predictions.all });
  queryClient.invalidateQueries({ queryKey: queryKeys.matches.list() });
}
```
