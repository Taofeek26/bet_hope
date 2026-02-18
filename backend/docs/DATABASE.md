# Bet_Hope Database Documentation

## Overview

Bet_Hope uses PostgreSQL 16 as the primary database with pgvector extension for document embeddings.

---

## Database Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Core      │  │    ML       │  │     Vector          │ │
│  │   Schema    │  │   Schema    │  │     Schema          │ │
│  ├─────────────┤  ├─────────────┤  ├─────────────────────┤ │
│  │ leagues     │  │ predictions │  │ document_embeddings │ │
│  │ teams       │  │ model_metrics│ │                     │ │
│  │ players     │  │ features    │  │                     │ │
│  │ matches     │  │             │  │                     │ │
│  │ statistics  │  │             │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Complete Schema

### leagues

Primary table for football competitions.

```sql
CREATE TABLE leagues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    api_league_id VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    priority_rank INTEGER DEFAULT 100,
    season_start_month INTEGER DEFAULT 8,
    season_end_month INTEGER DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_leagues_active ON leagues(is_active);
CREATE INDEX idx_leagues_priority ON leagues(priority_rank);
```

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| name | VARCHAR(100) | Full league name |
| country | VARCHAR(100) | Country of the league |
| api_league_id | VARCHAR(50) | External API identifier |
| logo_url | VARCHAR(500) | URL to league logo |
| is_active | BOOLEAN | Whether to sync data for this league |
| priority_rank | INTEGER | Processing priority (lower = higher priority) |
| season_start_month | INTEGER | Month when season starts (1-12) |
| season_end_month | INTEGER | Month when season ends (1-12) |

---

### teams

Football clubs/teams.

```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    api_team_id VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(500),
    founded INTEGER,
    stadium VARCHAR(200),
    stadium_capacity INTEGER,
    city VARCHAR(100),
    website VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_teams_league ON teams(league_id);
CREATE INDEX idx_teams_name ON teams(name);
```

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| league_id | INTEGER | Foreign key to leagues |
| name | VARCHAR(200) | Full team name |
| short_name | VARCHAR(50) | Abbreviated name (e.g., "ARS") |
| api_team_id | VARCHAR(50) | External API identifier |
| logo_url | VARCHAR(500) | URL to team crest/logo |
| founded | INTEGER | Year team was founded |
| stadium | VARCHAR(200) | Home stadium name |
| stadium_capacity | INTEGER | Stadium seating capacity |

---

### players

Player information and status.

```sql
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    api_player_id VARCHAR(50) UNIQUE,
    position VARCHAR(50),
    position_category VARCHAR(20), -- GK, DEF, MID, FWD
    shirt_number INTEGER,
    date_of_birth DATE,
    nationality VARCHAR(100),
    height_cm INTEGER,
    weight_kg INTEGER,
    preferred_foot VARCHAR(10),
    market_value_euros BIGINT,
    contract_until DATE,

    -- Injury tracking
    injury_status VARCHAR(50) DEFAULT 'fit',
    injury_type VARCHAR(100),
    injury_description TEXT,
    injury_date DATE,
    injury_expected_return DATE,

    -- Status
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_players_team ON players(team_id);
CREATE INDEX idx_players_position ON players(position_category);
CREATE INDEX idx_players_injury ON players(injury_status);
```

**Injury Status Values:**
- `fit` - Available for selection
- `injured` - Currently injured
- `doubtful` - Fitness doubt
- `suspended` - Serving suspension
- `international` - On international duty

---

### matches

Match fixtures and results.

```sql
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    home_team_id INTEGER NOT NULL REFERENCES teams(id),
    away_team_id INTEGER NOT NULL REFERENCES teams(id),
    api_match_id VARCHAR(50) NOT NULL UNIQUE,

    -- Timing
    season VARCHAR(20) NOT NULL,
    matchweek INTEGER,
    match_date DATE NOT NULL,
    kickoff_time TIME,
    kickoff_utc TIMESTAMP WITH TIME ZONE,

    -- Status
    status VARCHAR(50) DEFAULT 'scheduled',

    -- Results
    home_score INTEGER,
    away_score INTEGER,
    home_halftime_score INTEGER,
    away_halftime_score INTEGER,

    -- Metadata
    referee VARCHAR(200),
    venue VARCHAR(200),
    attendance INTEGER,

    -- Outcome (calculated)
    outcome VARCHAR(10), -- HOME, AWAY, DRAW

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT different_teams CHECK (home_team_id != away_team_id)
);

CREATE INDEX idx_matches_league ON matches(league_id);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_season ON matches(season);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_matches_kickoff ON matches(kickoff_utc);
```

**Status Values:**
- `scheduled` - Not yet started
- `live` - Currently in progress
- `halftime` - Half-time break
- `finished` - Match completed
- `postponed` - Match postponed
- `cancelled` - Match cancelled
- `suspended` - Match suspended

---

### match_statistics

Detailed match statistics.

```sql
CREATE TABLE match_statistics (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE UNIQUE,

    -- Possession (percentages)
    possession_home DECIMAL(5,2),
    possession_away DECIMAL(5,2),

    -- Shots
    shots_home INTEGER DEFAULT 0,
    shots_away INTEGER DEFAULT 0,
    shots_on_target_home INTEGER DEFAULT 0,
    shots_on_target_away INTEGER DEFAULT 0,
    shots_blocked_home INTEGER DEFAULT 0,
    shots_blocked_away INTEGER DEFAULT 0,

    -- Set pieces
    corners_home INTEGER DEFAULT 0,
    corners_away INTEGER DEFAULT 0,
    free_kicks_home INTEGER DEFAULT 0,
    free_kicks_away INTEGER DEFAULT 0,

    -- Discipline
    fouls_home INTEGER DEFAULT 0,
    fouls_away INTEGER DEFAULT 0,
    yellow_cards_home INTEGER DEFAULT 0,
    yellow_cards_away INTEGER DEFAULT 0,
    red_cards_home INTEGER DEFAULT 0,
    red_cards_away INTEGER DEFAULT 0,

    -- Other
    offsides_home INTEGER DEFAULT 0,
    offsides_away INTEGER DEFAULT 0,
    saves_home INTEGER DEFAULT 0,
    saves_away INTEGER DEFAULT 0,

    -- Advanced metrics
    xg_home DECIMAL(5,2),
    xg_away DECIMAL(5,2),
    xga_home DECIMAL(5,2),
    xga_away DECIMAL(5,2),

    -- Passing
    passes_home INTEGER,
    passes_away INTEGER,
    pass_accuracy_home DECIMAL(5,2),
    pass_accuracy_away DECIMAL(5,2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

### season_statistics

League table / standings data.

```sql
CREATE TABLE season_statistics (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    league_id INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    season VARCHAR(20) NOT NULL,

    -- Overall record
    matches_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    goals_for INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    goal_difference INTEGER GENERATED ALWAYS AS (goals_for - goals_against) STORED,
    points INTEGER DEFAULT 0,

    -- Position
    league_position INTEGER,
    previous_position INTEGER,

    -- Form (last 5 matches: W/D/L)
    form VARCHAR(10),

    -- Home record
    home_played INTEGER DEFAULT 0,
    home_wins INTEGER DEFAULT 0,
    home_draws INTEGER DEFAULT 0,
    home_losses INTEGER DEFAULT 0,
    home_goals_for INTEGER DEFAULT 0,
    home_goals_against INTEGER DEFAULT 0,

    -- Away record
    away_played INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,
    away_draws INTEGER DEFAULT 0,
    away_losses INTEGER DEFAULT 0,
    away_goals_for INTEGER DEFAULT 0,
    away_goals_against INTEGER DEFAULT 0,

    -- Advanced
    xg_for DECIMAL(6,2),
    xg_against DECIMAL(6,2),
    clean_sheets INTEGER DEFAULT 0,
    failed_to_score INTEGER DEFAULT 0,

    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team_id, season)
);

CREATE INDEX idx_season_stats_league_season ON season_statistics(league_id, season);
CREATE INDEX idx_season_stats_position ON season_statistics(league_position);
```

---

### head_to_head

Historical head-to-head records between teams.

```sql
CREATE TABLE head_to_head (
    id SERIAL PRIMARY KEY,
    team_a_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    team_b_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Overall record
    total_matches INTEGER DEFAULT 0,
    team_a_wins INTEGER DEFAULT 0,
    team_b_wins INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,

    -- Goals
    team_a_goals INTEGER DEFAULT 0,
    team_b_goals INTEGER DEFAULT 0,

    -- At team A's home
    matches_at_a INTEGER DEFAULT 0,
    team_a_home_wins INTEGER DEFAULT 0,
    team_b_away_wins INTEGER DEFAULT 0,
    draws_at_a INTEGER DEFAULT 0,

    -- At team B's home
    matches_at_b INTEGER DEFAULT 0,
    team_b_home_wins INTEGER DEFAULT 0,
    team_a_away_wins INTEGER DEFAULT 0,
    draws_at_b INTEGER DEFAULT 0,

    last_match_date DATE,
    last_match_id INTEGER REFERENCES matches(id),

    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team_a_id, team_b_id),
    CONSTRAINT ordered_teams CHECK (team_a_id < team_b_id)
);
```

---

### predictions

ML model predictions for matches.

```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,

    -- Probabilities (must sum to 1.0)
    home_win_probability DECIMAL(6,5) NOT NULL,
    draw_probability DECIMAL(6,5) NOT NULL,
    away_win_probability DECIMAL(6,5) NOT NULL,

    -- Score predictions
    predicted_home_score DECIMAL(4,2),
    predicted_away_score DECIMAL(4,2),
    most_likely_scoreline VARCHAR(10),

    -- Confidence
    confidence_score DECIMAL(5,4) NOT NULL,
    prediction_strength VARCHAR(20), -- STRONG, MODERATE, WEAK

    -- Recommended outcome
    recommended_outcome VARCHAR(10), -- HOME, DRAW, AWAY

    -- Model info
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50), -- xgboost, ensemble, etc.

    -- Feature snapshot
    features_json JSONB,

    -- Explanation
    key_factors TEXT[],
    explanation TEXT,

    -- Validation (filled after match)
    is_correct BOOLEAN,
    actual_outcome VARCHAR(10),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_probabilities CHECK (
        home_win_probability >= 0 AND home_win_probability <= 1 AND
        draw_probability >= 0 AND draw_probability <= 1 AND
        away_win_probability >= 0 AND away_win_probability <= 1 AND
        ABS((home_win_probability + draw_probability + away_win_probability) - 1) < 0.001
    )
);

CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_predictions_created ON predictions(created_at);
CREATE INDEX idx_predictions_model ON predictions(model_version);
CREATE INDEX idx_predictions_correct ON predictions(is_correct) WHERE is_correct IS NOT NULL;
```

---

### model_metrics

Model performance tracking.

```sql
CREATE TABLE model_metrics (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    league_id INTEGER REFERENCES leagues(id),

    -- Evaluation period
    evaluation_date DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Sample size
    total_predictions INTEGER NOT NULL,

    -- Accuracy metrics
    correct_predictions INTEGER,
    accuracy DECIMAL(5,4),

    -- By outcome
    home_predictions INTEGER,
    home_correct INTEGER,
    draw_predictions INTEGER,
    draw_correct INTEGER,
    away_predictions INTEGER,
    away_correct INTEGER,

    -- Probabilistic metrics
    log_loss DECIMAL(10,6),
    brier_score DECIMAL(10,6),

    -- Calibration
    calibration_error DECIMAL(10,6),

    -- ROI simulation
    roi_flat_stake DECIMAL(8,4),
    roi_kelly DECIMAL(8,4),

    -- Confidence analysis
    high_confidence_accuracy DECIMAL(5,4),
    low_confidence_accuracy DECIMAL(5,4),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_metrics_version ON model_metrics(model_version);
CREATE INDEX idx_model_metrics_date ON model_metrics(evaluation_date);
CREATE INDEX idx_model_metrics_league ON model_metrics(league_id);
```

---

### documents

News articles and reports for AI analysis.

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,

    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,

    -- Source
    source_url VARCHAR(1000) UNIQUE,
    source_name VARCHAR(200),
    author VARCHAR(200),

    -- Classification
    document_type VARCHAR(50) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',

    -- Timing
    published_at TIMESTAMP WITH TIME ZONE,

    -- Entities (stored as arrays of IDs)
    teams_mentioned INTEGER[],
    players_mentioned INTEGER[],
    leagues_mentioned INTEGER[],
    matches_mentioned INTEGER[],

    -- Analysis results
    sentiment_score DECIMAL(5,4), -- -1.0 to 1.0
    sentiment_label VARCHAR(20), -- positive, negative, neutral
    relevance_score DECIMAL(5,4),

    -- Processing status
    is_processed BOOLEAN DEFAULT false,
    is_embedded BOOLEAN DEFAULT false,
    processing_error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_published ON documents(published_at);
CREATE INDEX idx_documents_processed ON documents(is_processed);
CREATE INDEX idx_documents_teams ON documents USING GIN(teams_mentioned);
```

**Document Types:**
- `injury_report` - Player injury updates
- `match_preview` - Pre-match analysis
- `press_conference` - Manager quotes
- `transfer_news` - Transfer updates
- `tactical_analysis` - Formation/tactics
- `match_report` - Post-match analysis

---

### document_embeddings

Vector embeddings for semantic search (requires pgvector).

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Embedding
    embedding vector(384) NOT NULL, -- Dimension depends on model

    -- Model info
    model_name VARCHAR(100) NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(document_id, model_name)
);

-- HNSW index for fast similarity search
CREATE INDEX idx_embeddings_vector ON document_embeddings
USING hnsw (embedding vector_cosine_ops);
```

---

## Materialized Views

### upcoming_matches_view

Frequently accessed view for upcoming fixtures.

```sql
CREATE MATERIALIZED VIEW upcoming_matches_view AS
SELECT
    m.id,
    m.match_date,
    m.kickoff_time,
    m.kickoff_utc,
    m.season,
    m.matchweek,
    l.id as league_id,
    l.name as league_name,
    l.country as league_country,
    ht.id as home_team_id,
    ht.name as home_team_name,
    ht.logo_url as home_team_logo,
    at.id as away_team_id,
    at.name as away_team_name,
    at.logo_url as away_team_logo,
    hss.league_position as home_position,
    hss.form as home_form,
    ass.league_position as away_position,
    ass.form as away_form,
    p.home_win_probability,
    p.draw_probability,
    p.away_win_probability,
    p.confidence_score,
    p.recommended_outcome
FROM matches m
JOIN leagues l ON m.league_id = l.id
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id
LEFT JOIN season_statistics hss ON hss.team_id = ht.id AND hss.season = m.season
LEFT JOIN season_statistics ass ON ass.team_id = at.id AND ass.season = m.season
LEFT JOIN predictions p ON p.match_id = m.id
WHERE m.status = 'scheduled'
  AND m.match_date >= CURRENT_DATE
ORDER BY m.kickoff_utc;

CREATE INDEX idx_upcoming_matches_date ON upcoming_matches_view(match_date);
CREATE INDEX idx_upcoming_matches_league ON upcoming_matches_view(league_id);

-- Refresh every 15 minutes via Celery
```

---

## Functions & Triggers

### Update timestamp trigger

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_leagues_updated_at BEFORE UPDATE ON leagues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ... etc for other tables
```

### Calculate match outcome

```sql
CREATE OR REPLACE FUNCTION calculate_match_outcome()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.home_score IS NOT NULL AND NEW.away_score IS NOT NULL THEN
        IF NEW.home_score > NEW.away_score THEN
            NEW.outcome = 'HOME';
        ELSIF NEW.home_score < NEW.away_score THEN
            NEW.outcome = 'AWAY';
        ELSE
            NEW.outcome = 'DRAW';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER set_match_outcome BEFORE INSERT OR UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION calculate_match_outcome();
```

---

## Indexes Summary

### Performance-Critical Indexes

```sql
-- Match queries
CREATE INDEX idx_matches_upcoming ON matches(kickoff_utc)
    WHERE status = 'scheduled';
CREATE INDEX idx_matches_league_season ON matches(league_id, season);
CREATE INDEX idx_matches_team_date ON matches(home_team_id, match_date);

-- Prediction queries
CREATE INDEX idx_predictions_recent ON predictions(created_at DESC);
CREATE INDEX idx_predictions_confident ON predictions(confidence_score DESC)
    WHERE confidence_score > 0.6;

-- Form calculation queries
CREATE INDEX idx_matches_team_form ON matches(home_team_id, match_date DESC);
```

---

## Backup Strategy

```bash
# Daily backup
pg_dump -Fc bet_hope > backup_$(date +%Y%m%d).dump

# Restore
pg_restore -d bet_hope backup_20240115.dump
```

---

## Migration Strategy

Using Django migrations for schema changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

All schema changes should be backwards compatible when possible.
