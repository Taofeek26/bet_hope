// Core Types for Bet Hope

export interface League {
  id: number;
  code: string;
  name: string;
  country: string;
  tier: number;
  logo_url?: string;
  is_active: boolean;
  seasons_count?: number;
  teams_count?: number;
  matches_count?: number;
  predictions_count?: number;
}

export interface Season {
  id: number;
  league: League;
  code: string;
  name: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  total_matches: number;
  matches_played: number;
  progress?: number;
}

export interface Team {
  id: number;
  name: string;
  short_name?: string;
  league: League | number;
  league_name?: string;
  logo_url?: string;
  founded?: number;
  stadium?: string;
}

export interface TeamStats {
  id: number;
  season: number;
  season_name: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
  ppg: number;
  xg_for?: number;
  xg_against?: number;
  form_string?: string;
  position?: number;
}

export interface Match {
  id: number;
  season: number;
  home_team: Team;
  away_team: Team;
  match_date: string;
  kickoff_time?: string;
  home_score?: number;
  away_score?: number;
  home_halftime_score?: number;
  away_halftime_score?: number;
  status: MatchStatus;
  home_xg?: number;
  away_xg?: number;
  league_name?: string;
}

export type MatchStatus = 'scheduled' | 'live' | 'finished' | 'postponed' | 'cancelled';

export interface MatchStatistics {
  shots_home: number;
  shots_away: number;
  shots_on_target_home: number;
  shots_on_target_away: number;
  corners_home: number;
  corners_away: number;
  fouls_home: number;
  fouls_away: number;
  yellow_cards_home: number;
  yellow_cards_away: number;
  red_cards_home: number;
  red_cards_away: number;
  possession_home?: number;
  possession_away?: number;
}

export interface MatchOdds {
  home_odds: number;
  draw_odds: number;
  away_odds: number;
  over_25_odds?: number;
  under_25_odds?: number;
  implied_probs?: {
    home: number;
    draw: number;
    away: number;
  };
}

export interface Prediction {
  id: number;
  match_id: number;
  model_version?: string;
  predicted_outcome: 'H' | 'D' | 'A';
  confidence: number;
  probabilities: {
    home: number;
    draw: number;
    away: number;
  };
  predicted_total_goals?: number;
  over_25_prob?: number;
  recommended_bet?: RecommendedBet;
  created_at: string;
}

export interface RecommendedBet {
  outcome: 'H' | 'D' | 'A';
  probability: number;
  confidence: 'high' | 'medium' | 'low';
  fair_odds: number;
}

export interface ValueBet {
  match: {
    id: number;
    home_team: string;
    away_team: string;
    date: string;
    time?: string;
  };
  market: 'home' | 'draw' | 'away' | 'over_2.5' | 'under_2.5';
  model_probability: number;
  market_probability: number;
  edge: number;
  odds: number;
  confidence: number;
  rating: 'strong' | 'moderate' | 'weak';
}

export interface StandingsEntry {
  position: number;
  // Support both nested team object and flat fields
  team?: {
    id: number;
    name: string;
    logo?: string;
  };
  team_id?: number;
  team_name?: string;
  team_logo?: string;
  played: number;
  wins?: number;  // Backend uses 'wins' not 'won'
  won?: number;   // Keep for compatibility
  draws?: number;
  drawn?: number;
  losses?: number;
  lost?: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  form: string;
  matches_played?: number;
}

export interface PredictionStats {
  period: string;
  total_predictions: number;
  correct_predictions: number;
  accuracy: number;
  by_outcome: Record<string, { total: number; correct: number; accuracy: number }>;
  by_confidence: Record<string, { total: number; correct: number; accuracy: number }>;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  results: T[];
}

// Form types
export type FormResult = 'W' | 'D' | 'L';

// AI Recommendation types
export interface AIRecommendation {
  id: number;
  prediction_id: number;
  provider: 'openai' | 'anthropic' | 'google';
  model: string;
  recommendation: string;
  confidence_assessment: string;
  risk_analysis: string;
  key_factors: string[];
  tokens_used: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
}

export interface AIRecommendationResponse {
  status: 'success' | 'error';
  recommendation: string;
  confidence_assessment: string;
  risk_analysis: string;
  key_factors: string[];
  provider: string;
  model: string;
  tokens_used: number;
}
