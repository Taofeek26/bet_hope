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
  AIRecommendation,
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

// Response interceptor (Phase 7): an expired sign-in is refreshed once with
// the refresh token; if that fails the user is signed out and the request is
// retried without a token (public pages must keep working).
let refreshing: Promise<string | null> | null = null;
async function refreshAccess(): Promise<string | null> {
  const refresh = typeof window !== 'undefined' ? localStorage.getItem('refresh') : null;
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${api.defaults.baseURL}/auth/token/refresh/`, { refresh });
    localStorage.setItem('token', data.access);
    if (data.refresh) localStorage.setItem('refresh', data.refresh);
    return data.access;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const cfg = error.config || {};
    if (error.response?.status === 401 && typeof window !== 'undefined' && !cfg._retried && !String(cfg.url || '').includes('/auth/token')) {
      cfg._retried = true;
      refreshing = refreshing || refreshAccess().finally(() => { refreshing = null; });
      const access = await refreshing;
      if (access) {
        cfg.headers = { ...(cfg.headers || {}), Authorization: `Bearer ${access}` };
      } else {
        localStorage.removeItem('token');
        localStorage.removeItem('refresh');
        window.dispatchEvent(new Event('bethope-signed-out'));
        if (cfg.headers) delete cfg.headers.Authorization;
      }
      return api.request(cfg);
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
    // page_size: the API pages at 20 by default, which dropped leagues past #20 (API-07)
    const { data } = await api.get<{ results: League[] } | League[]>('/leagues/', { params: { page_size: 100, ...params } });
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
    const { data } = await api.get<{ results: Team[] } | Team[]>('/teams/', { params: { page_size: 100, ...params } });
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

  getUpcoming: async (params?: { days?: number; league?: string }) => {
    const { data } = await api.get<{
      start_date: string;
      end_date: string;
      total_matches: number;
      matches_by_date: Record<string, Match[]>;
    }>('/matches/upcoming/', { params });
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
    const { data } = await api.get<{ count: number; matches: Match[]; covered: string[]; updated_every_minutes: number }>('/matches/live/');
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
    // A busy Saturday has 100+ matches; page_size keeps the whole day in one response (API-07)
    const { data } = await api.get<{ results: Prediction[] } | Prediction[]>('/predictions/', { params: { page_size: 500, ...params } });
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

  getPaperBets: async (params?: { days?: number; model_family?: string }) => {
    const { data } = await api.get('/predictions/paper_bets/', { params });
    return data;
  },

  getStats: async (params?: { days?: number; model_family?: string }) => {
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
    provider?: 'openai' | 'anthropic' | 'google' | 'openrouter';
    include_rag?: boolean;
  }) => {
    // AI generation can take up to 60 seconds due to OpenAI API calls
    const { data } = await api.post('/ai-recommendations/generate/', params, {
      timeout: 120000, // 2 minute timeout for AI generation
    });
    return data;
  },

  // Poll target for an async generation (generate returns 202 + id).
  getById: async (id: number) => {
    const { data } = await api.get<AIRecommendation>(`/ai-recommendations/${id}/`);
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

// Accounts (Phase 7)
export interface Me {
  id: number; username: string; email: string; name: string; is_staff: boolean; joined: string;
  favourite_teams: number[]; favourite_leagues: string[]; weekly_limit: number | null;
}
export const accountApi = {
  register: async (username: string, email: string, password: string, name: string) =>
    (await api.post<{ access: string; refresh: string; user: Me }>('/auth/register/', { username, email, password, name })).data,
  me: async () => (await api.get<Me>('/me/')).data,
  update: async (patch: Partial<Me>) => (await api.patch<Me>('/me/update/', patch)).data,
  changePassword: async (old_password: string, new_password: string) => (await api.post('/me/password/', { old_password, new_password })).data,
  deleteAccount: async (password: string) => (await api.post('/me/delete/', { password })).data,
  bets: async () => (await api.get<{ bets: any[] }>('/me/bets/')).data.bets,
  saveBets: async (bets: any[]) => (await api.post('/me/bets/', { bets })).data,
  deleteBet: async (id: string) => (await api.post('/me/bets/delete/', { id })).data,
  adminUsers: async (search?: string) => (await api.get('/admin-users/', { params: search ? { search } : undefined })).data,
  adminUser: async (id: number) => (await api.get(`/admin-users/${id}/`)).data,
  adminSetActive: async (id: number, active: boolean) => (await api.post(`/admin-users/${id}/set_active/`, { active })).data,
  adminResetPassword: async (id: number) => (await api.post(`/admin-users/${id}/reset_password/`)).data as { temporary_password: string },
};

// Auth endpoints
export const authApi = {
  login: async (username: string, password: string) => {
    const { data } = await api.post<{ access: string; refresh: string }>('/auth/token/', {
      username,
      password,
    });
    return data;
  },
};

// Admin task-runner endpoints — trigger sync/train/predict management
// commands and poll their progress. Backed by TaskRun rows in Postgres
// (not Celery — there's no broker in this deployment), so polling survives
// a closed/reopened browser tab as long as the task id is remembered
// (see AdminTasksPanel, which persists it in localStorage).
export type TaskRunStatus = 'pending' | 'running' | 'success' | 'error' | 'timeout';

export interface TaskRun {
  id: string;
  command: string;
  command_display: string;
  args: string[];
  status: TaskRunStatus;
  status_display: string;
  triggered_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  log_tail: string;
  error: string;
}

export const adminTasksApi = {
  trigger: async (command: string, args: string[] = []) => {
    const { data } = await api.post<TaskRun>('/admin-tasks/', { command, args });
    return data;
  },

  getStatus: async (id: string) => {
    const { data } = await api.get<TaskRun>(`/admin-tasks/${id}/`);
    return data;
  },

  list: async () => {
    const { data } = await api.get<TaskRun[]>('/admin-tasks/');
    return data;
  },
};

// Flash feed, acca of the day, yesterday's results (Phase 6)
export const engageApi = {
  flash: async (params?: { match?: number; team?: number; kind?: string; limit?: number; hours?: number; min_importance?: number }) => {
    const { data } = await api.get('/engage/flash/', { params });
    return data as { items: FlashItem[] };
  },
  acca: async () => {
    const { data } = await api.get('/engage/acca/');
    return data;
  },
  results: async (date?: string) => {
    const { data } = await api.get('/engage/results/', { params: date ? { date } : undefined });
    return data;
  },
  pushKey: async () => (await api.get('/engage/push_key/')).data as { public_key: string },
  pushSubscribe: async (subscription: any, teams: number[], prefs: Record<string, boolean>) =>
    (await api.post('/engage/push_subscribe/', { subscription, teams, prefs })).data,
  pushUnsubscribe: async (endpoint: string) => (await api.post('/engage/push_unsubscribe/', { endpoint })).data,
};

export interface FlashItem {
  id: number;
  kind: 'odds_move' | 'news' | 'model_change' | 'results' | 'acca';
  tag: string;
  title: string;
  body: string;
  url: string;
  source: string;
  importance: number;
  published_at: string;
  match: { id: number; label: string; kickoff_at: string | null; match_date: string } | null;
  team: { id: number; name: string } | null;
}

export default api;
