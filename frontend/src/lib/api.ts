import axios from 'axios';
import type {
  League,
  Season,
  Team,
  TeamStats,
  Match,
  Prediction,
  ValueBet,
  StandingsEntry,
  PredictionStats,
} from '@/types';

// Create axios instance
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
      }
    }
    return Promise.reject(error);
  }
);

// Helper to extract results from paginated response
const extractResults = <T>(data: T[] | { results: T[] }): T[] => {
  if (Array.isArray(data)) return data;
  if (data && 'results' in data) return data.results;
  return [];
};

// League endpoints
export const leaguesApi = {
  getAll: async (params?: { country?: string; tier?: number; active?: boolean }) => {
    const { data } = await api.get<{ results: League[] } | League[]>('/leagues/', { params });
    return extractResults(data);
  },

  getByCode: async (code: string) => {
    const { data } = await api.get<League>(`/leagues/${code}/`);
    return data;
  },

  getStandings: async (code: string) => {
    const { data } = await api.get<{
      league: League;
      season: Season;
      standings: StandingsEntry[];
    }>(`/leagues/${code}/standings/`);
    return data;
  },

  getSeasons: async (code: string) => {
    const { data } = await api.get<{ league: League; seasons: Season[] }>(
      `/leagues/${code}/seasons/`
    );
    return data;
  },

  getStats: async (code: string) => {
    const { data } = await api.get(`/leagues/${code}/stats/`);
    return data;
  },
};

// Team endpoints
export const teamsApi = {
  getAll: async (params?: { league?: string; search?: string }) => {
    const { data } = await api.get<{ results: Team[] } | Team[]>('/teams/', { params });
    return extractResults(data);
  },

  getById: async (id: number) => {
    const { data } = await api.get<Team>(`/teams/${id}/`);
    return data;
  },

  getStats: async (id: number) => {
    const { data } = await api.get<{ team: Team; seasons: TeamStats[] }>(
      `/teams/${id}/stats/`
    );
    return data;
  },

  getFixtures: async (id: number) => {
    const { data } = await api.get<{
      team: Team;
      past_matches: Match[];
      upcoming_matches: Match[];
    }>(`/teams/${id}/fixtures/`);
    return data;
  },

  getForm: async (id: number) => {
    const { data } = await api.get(`/teams/${id}/form/`);
    return data;
  },

  getH2H: async (teamId: number, opponentId: number) => {
    const { data } = await api.get(`/teams/${teamId}/h2h/${opponentId}/`);
    return data;
  },
};

// Match endpoints
export const matchesApi = {
  getAll: async (params?: {
    league?: string;
    season?: string;
    team?: number;
    date_from?: string;
    date_to?: string;
    status?: string;
  }) => {
    const { data } = await api.get<{ results: Match[] } | Match[]>('/matches/', { params });
    return extractResults(data);
  },

  getById: async (id: number) => {
    const { data } = await api.get<Match>(`/matches/${id}/`);
    return data;
  },

  getUpcoming: async () => {
    const { data } = await api.get<{
      start_date: string;
      end_date: string;
      total_matches: number;
      matches_by_date: Record<string, Match[]>;
    }>('/matches/upcoming/');
    return data;
  },

  getToday: async () => {
    const { data } = await api.get<{
      date: string;
      scheduled: Match[];
      live: Match[];
      finished: Match[];
    }>('/matches/today/');
    return data;
  },

  getResults: async (params?: { days?: number; league?: string; page?: number }) => {
    const { data } = await api.get('/matches/results/', { params });
    return data;
  },

  getLive: async () => {
    const { data } = await api.get<{ count: number; matches: Match[] }>('/matches/live/');
    return data;
  },

  getWithPredictions: async (params?: { min_confidence?: number }) => {
    const { data } = await api.get('/matches/with_predictions/', { params });
    return data;
  },

  getPrediction: async (id: number) => {
    const { data } = await api.get(`/matches/${id}/prediction/`);
    return data;
  },
};

// Prediction endpoints
export const predictionsApi = {
  getAll: async (params?: {
    league?: string;
    date_from?: string;
    date_to?: string;
    min_confidence?: number;
  }) => {
    const { data } = await api.get<{ results: Prediction[] } | Prediction[]>('/predictions/', { params });
    return extractResults(data);
  },

  getById: async (id: number) => {
    const { data } = await api.get<Prediction>(`/predictions/${id}/`);
    return data;
  },

  generate: async (match: {
    home_team_id: number;
    away_team_id: number;
    match_date: string;
    season_code?: string;
  }) => {
    const { data } = await api.post<Prediction>('/predictions/generate/', match);
    return data;
  },

  getUpcoming: async (params?: { days?: number; min_confidence?: number; include_finished?: boolean }) => {
    const { data } = await api.get('/predictions/upcoming/', { params });
    return data;
  },

  getRecent: async (params?: { days_back?: number; days_forward?: number; include_finished?: boolean; min_confidence?: number }) => {
    const { data } = await api.get('/predictions/recent/', { params });
    return data;
  },

  getValueBets: async (params?: { days?: number; date?: string }) => {
    const { data } = await api.get<{ total: number; value_bets: ValueBet[] }>(
      '/predictions/value_bets/',
      { params }
    );
    return data;
  },

  getStats: async (params?: { days?: number }) => {
    const { data } = await api.get<PredictionStats>('/predictions/stats/', { params });
    return data;
  },

  getDailyPicks: async (params?: { date?: string }) => {
    const { data } = await api.get('/predictions/daily_picks/', { params });
    return data;
  },

  getModelInfo: async () => {
    const { data } = await api.get('/predictions/model_info/');
    return data;
  },

  getWeeklyAvailability: async () => {
    const { data } = await api.get<{
      start_date: string;
      days: Array<{
        date: string;
        day_offset: number;
        total_matches: number;
        high_confidence: number;
      }>;
    }>('/predictions/weekly_availability/');
    return data;
  },
};

// AI Recommendations endpoints
export const aiApi = {
  getProviders: async () => {
    const { data } = await api.get<{ providers: string[]; default: string }>(
      '/ai-recommendations/providers/'
    );
    return data;
  },

  generate: async (params: {
    prediction_id: number;
    provider?: 'openai' | 'anthropic' | 'google';
    include_rag?: boolean;
  }) => {
    // AI generation can take up to 60 seconds due to OpenAI API calls
    const { data } = await api.post('/ai-recommendations/generate/', params, {
      timeout: 120000, // 2 minute timeout for AI generation
    });
    return data;
  },

  getForPrediction: async (predictionId: number) => {
    const { data } = await api.get(`/ai-recommendations/for-prediction/${predictionId}/`);
    return data;
  },

  getAll: async (params?: { prediction_id?: number; provider?: string }) => {
    const { data } = await api.get('/ai-recommendations/', { params });
    return data;
  },
};

// Sync/Task Status endpoints
export const syncApi = {
  getTaskStatus: async () => {
    const { data } = await api.get<{
      overall_health: 'healthy' | 'partial' | 'warning' | 'unknown';
      summary: {
        healthy: number;
        stale: number;
        unknown: number;
        total: number;
      };
      last_checked: string;
      groups: Array<{
        group: string;
        tasks: Array<{
          key: string;
          name: string;
          schedule: string;
          last_run: string | null;
          time_ago: string | null;
          last_status: string | null;
          health: 'healthy' | 'stale' | 'unknown';
        }>;
      }>;
    }>('/sync/task_status/');
    return data;
  },

  getApiStatus: async () => {
    const { data } = await api.get('/sync/api_status/');
    return data;
  },
};

// Documents endpoints
export const documentsApi = {
  getAll: async (params?: { type?: string; search?: string }) => {
    const { data } = await api.get('/documents/', { params });
    return data;
  },

  upload: async (doc: {
    title: string;
    content: string;
    document_type: string;
    source_url?: string;
    author?: string;
    team_ids?: number[];
    league_ids?: number[];
  }) => {
    const { data } = await api.post('/documents/upload/', doc);
    return data;
  },

  search: async (query: string, topK?: number) => {
    const { data } = await api.get('/documents/search/', {
      params: { q: query, top_k: topK },
    });
    return data;
  },
};

export default api;
