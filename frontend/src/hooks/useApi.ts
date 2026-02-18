'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leaguesApi, teamsApi, matchesApi, predictionsApi } from '@/lib/api';

// Query keys
export const queryKeys = {
  leagues: {
    all: ['leagues'] as const,
    detail: (code: string) => ['leagues', code] as const,
    standings: (code: string) => ['leagues', code, 'standings'] as const,
    seasons: (code: string) => ['leagues', code, 'seasons'] as const,
    stats: (code: string) => ['leagues', code, 'stats'] as const,
  },
  teams: {
    all: ['teams'] as const,
    detail: (id: number) => ['teams', id] as const,
    stats: (id: number) => ['teams', id, 'stats'] as const,
    fixtures: (id: number) => ['teams', id, 'fixtures'] as const,
    form: (id: number) => ['teams', id, 'form'] as const,
    h2h: (teamId: number, opponentId: number) =>
      ['teams', teamId, 'h2h', opponentId] as const,
  },
  matches: {
    all: ['matches'] as const,
    detail: (id: number) => ['matches', id] as const,
    upcoming: ['matches', 'upcoming'] as const,
    today: ['matches', 'today'] as const,
    live: ['matches', 'live'] as const,
    results: ['matches', 'results'] as const,
    withPredictions: ['matches', 'with-predictions'] as const,
  },
  predictions: {
    all: ['predictions'] as const,
    detail: (id: number) => ['predictions', id] as const,
    upcoming: ['predictions', 'upcoming'] as const,
    valueBets: ['predictions', 'value-bets'] as const,
    stats: ['predictions', 'stats'] as const,
    dailyPicks: ['predictions', 'daily-picks'] as const,
    modelInfo: ['predictions', 'model-info'] as const,
  },
};

// League hooks
export function useLeagues(params?: Parameters<typeof leaguesApi.getAll>[0]) {
  return useQuery({
    queryKey: [...queryKeys.leagues.all, params],
    queryFn: () => leaguesApi.getAll(params),
  });
}

export function useLeague(code: string) {
  return useQuery({
    queryKey: queryKeys.leagues.detail(code),
    queryFn: () => leaguesApi.getByCode(code),
    enabled: !!code,
  });
}

export function useLeagueStandings(code: string) {
  return useQuery({
    queryKey: queryKeys.leagues.standings(code),
    queryFn: () => leaguesApi.getStandings(code),
    enabled: !!code,
  });
}

export function useLeagueSeasons(code: string) {
  return useQuery({
    queryKey: queryKeys.leagues.seasons(code),
    queryFn: () => leaguesApi.getSeasons(code),
    enabled: !!code,
  });
}

export function useLeagueStats(code: string) {
  return useQuery({
    queryKey: queryKeys.leagues.stats(code),
    queryFn: () => leaguesApi.getStats(code),
    enabled: !!code,
  });
}

// Team hooks
export function useTeams(params?: Parameters<typeof teamsApi.getAll>[0]) {
  return useQuery({
    queryKey: [...queryKeys.teams.all, params],
    queryFn: () => teamsApi.getAll(params),
  });
}

export function useTeam(id: number) {
  return useQuery({
    queryKey: queryKeys.teams.detail(id),
    queryFn: () => teamsApi.getById(id),
    enabled: !!id,
  });
}

export function useTeamStats(id: number) {
  return useQuery({
    queryKey: queryKeys.teams.stats(id),
    queryFn: () => teamsApi.getStats(id),
    enabled: !!id,
  });
}

export function useTeamFixtures(id: number) {
  return useQuery({
    queryKey: queryKeys.teams.fixtures(id),
    queryFn: () => teamsApi.getFixtures(id),
    enabled: !!id,
  });
}

export function useTeamForm(id: number) {
  return useQuery({
    queryKey: queryKeys.teams.form(id),
    queryFn: () => teamsApi.getForm(id),
    enabled: !!id,
  });
}

export function useH2H(teamId: number, opponentId: number) {
  return useQuery({
    queryKey: queryKeys.teams.h2h(teamId, opponentId),
    queryFn: () => teamsApi.getH2H(teamId, opponentId),
    enabled: !!teamId && !!opponentId,
  });
}

// Match hooks
export function useMatches(params?: Parameters<typeof matchesApi.getAll>[0]) {
  return useQuery({
    queryKey: [...queryKeys.matches.all, params],
    queryFn: () => matchesApi.getAll(params),
  });
}

export function useMatch(id: number) {
  return useQuery({
    queryKey: queryKeys.matches.detail(id),
    queryFn: () => matchesApi.getById(id),
    enabled: !!id,
  });
}

export function useUpcomingMatches() {
  return useQuery({
    queryKey: queryKeys.matches.upcoming,
    queryFn: () => matchesApi.getUpcoming(),
    refetchInterval: 60000, // Refresh every minute
  });
}

export function useTodayMatches() {
  return useQuery({
    queryKey: queryKeys.matches.today,
    queryFn: () => matchesApi.getToday(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useLiveMatches() {
  return useQuery({
    queryKey: queryKeys.matches.live,
    queryFn: () => matchesApi.getLive(),
    refetchInterval: 15000, // Refresh every 15 seconds for live matches
  });
}

export function useMatchResults(params?: Parameters<typeof matchesApi.getResults>[0]) {
  return useQuery({
    queryKey: [...queryKeys.matches.results, params],
    queryFn: () => matchesApi.getResults(params),
  });
}

export function useMatchesWithPredictions(
  params?: Parameters<typeof matchesApi.getWithPredictions>[0]
) {
  return useQuery({
    queryKey: [...queryKeys.matches.withPredictions, params],
    queryFn: () => matchesApi.getWithPredictions(params),
  });
}

export function useMatchPrediction(matchId: number) {
  return useQuery({
    queryKey: [...queryKeys.matches.detail(matchId), 'prediction'],
    queryFn: () => matchesApi.getPrediction(matchId),
    enabled: !!matchId,
  });
}

// Prediction hooks
export function usePredictions(params?: Parameters<typeof predictionsApi.getAll>[0]) {
  return useQuery({
    queryKey: [...queryKeys.predictions.all, params],
    queryFn: () => predictionsApi.getAll(params),
  });
}

export function usePrediction(id: number) {
  return useQuery({
    queryKey: queryKeys.predictions.detail(id),
    queryFn: () => predictionsApi.getById(id),
    enabled: !!id,
  });
}

export function useUpcomingPredictions(
  params?: Parameters<typeof predictionsApi.getUpcoming>[0]
) {
  return useQuery({
    queryKey: [...queryKeys.predictions.upcoming, params],
    queryFn: () => predictionsApi.getUpcoming(params),
    refetchInterval: 300000, // Refresh every 5 minutes
  });
}

export function useValueBets(params?: Parameters<typeof predictionsApi.getValueBets>[0]) {
  return useQuery({
    queryKey: [...queryKeys.predictions.valueBets, params],
    queryFn: () => predictionsApi.getValueBets(params),
  });
}

export function usePredictionStats(params?: { days?: number }) {
  return useQuery({
    queryKey: [...queryKeys.predictions.stats, params],
    queryFn: () => predictionsApi.getStats(params),
  });
}

export function useDailyPicks(params?: { date?: string }) {
  return useQuery({
    queryKey: [...queryKeys.predictions.dailyPicks, params],
    queryFn: () => predictionsApi.getDailyPicks(params),
    refetchInterval: 300000,
  });
}

export function useModelInfo() {
  return useQuery({
    queryKey: queryKeys.predictions.modelInfo,
    queryFn: () => predictionsApi.getModelInfo(),
    staleTime: 3600000, // Cache for 1 hour
  });
}

export function useWeeklyAvailability() {
  return useQuery({
    queryKey: ['predictions', 'weekly-availability'],
    queryFn: () => predictionsApi.getWeeklyAvailability(),
    staleTime: 300000, // Cache for 5 minutes
  });
}

// Mutation hooks
export function useGeneratePrediction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: predictionsApi.generate,
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: queryKeys.predictions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.predictions.upcoming });
    },
  });
}
