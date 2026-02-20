# Changelog

All notable changes to the Bet_Hope project are documented here.

## [1.0.2] - 2026-02-20

### CI/CD

**New Features:**
- Added GitHub Actions workflow for automatic deployment on push to main
- Deployment triggers on every push to main branch
- Supports manual workflow dispatch

---

## [1.0.1] - 2026-02-18

### Docker Configuration Fixes

**Bug Fixes:**
- Fixed database connection by adding `DATABASE_URL` support in settings
- Fixed missing serializer exports (`PredictionRequestSerializer`, `BatchPredictionRequestSerializer`, `ModelVersionSerializer`)
- Removed unused `HeadToHeadSerializer` import from teams view
- Fixed dependency conflict: pinned `django-filter<25.0` for Django 5.0 compatibility
- Added missing AI dependencies: `anthropic>=0.18.0`, `google-generativeai>=0.3.0`

**Docker Improvements:**
- Frontend now uses port 3001 (to avoid conflicts with existing services)
- Removed obsolete `version` attribute from docker-compose.yml
- Added `frontend_node_modules` volume for better caching
- Frontend runs in development mode with hot reload
- Fixed backend Dockerfile casing (`as` → `AS`)
- Added `output: 'standalone'` to next.config.js for production builds

**Database:**
- Created initial migrations for all apps (leagues, teams, players, matches, predictions, analytics, documents)
- Migrations auto-run on container startup

---

## [1.0.0] - 2026-02-18

### Initial Release

#### Backend (Django + Python)

**Core Infrastructure:**
- Django 5.x project scaffold with modular app structure
- PostgreSQL 16 with pgvector extension for vector embeddings
- Redis for caching and Celery message broker
- Celery + Celery Beat for background task processing
- JWT authentication with refresh tokens
- CORS configuration for frontend integration

**Database Models:**
- `apps.core` - Base models (TimeStampedModel, SyncedModel)
- `apps.leagues` - League and Season models
- `apps.teams` - Team, TeamSeasonStats, HeadToHead models
- `apps.players` - Player model (placeholder)
- `apps.matches` - Match, MatchStatistics, MatchOdds models
- `apps.predictions` - Prediction, ModelVersion models
- `apps.analytics` - ModelMetrics, DailyStats models
- `apps.documents` - Document, DocumentChunk, AIRecommendation, EmbeddingCache models

**Data Ingestion:**
- `FootballDataProvider` - Downloads free CSV data from football-data.co.uk
  - Supports 20 major leagues
  - 10 years of historical data (2015-2025)
  - Match results, statistics, and betting odds
- `UnderstatProvider` - Scrapes xG data from Understat
  - Expected Goals (xG, xGA, xPTS)
  - Shot-level data
  - Player xG statistics
- Automatic caching and incremental sync

**ML Pipeline:**
- `apps.ml_pipeline.features`:
  - `TeamFeatureBuilder` - Form, xG, season stats extraction
  - `MatchFeatureBuilder` - Combined features + H2H + context
  - `FeatureExtractor` - Orchestration with disk caching
- `apps.ml_pipeline.training`:
  - `ModelTrainer` - XGBoost training with hyperparameter tuning
  - `ModelEvaluator` - Comprehensive evaluation + betting ROI simulation
- `apps.ml_pipeline.inference`:
  - `MatchPredictor` - Production inference with batch predictions

**Celery Tasks:**
- `sync_football_data` - Full data sync from Football-Data.co.uk
- `sync_understat_xg` - xG data sync from Understat
- `daily_data_sync` - Daily automated sync
- `update_team_form` - Form calculation updates
- `generate_predictions_task` - Batch prediction generation
- `retrain_model_task` - Model retraining task

**REST API (`apps.api`):**
- `/api/v1/leagues/` - League CRUD + standings, seasons, stats
- `/api/v1/teams/` - Team CRUD + stats, fixtures, form, H2H
- `/api/v1/matches/` - Match CRUD + upcoming, today, live, results
- `/api/v1/predictions/` - Predictions + generate, value bets, stats
- `/api/v1/ai-recommendations/` - AI analysis endpoints
- `/api/v1/documents/` - Document management + RAG search

**AI & RAG System:**
- Vector embeddings with pgvector (1536 dimensions)
- Document chunking with configurable size/overlap
- Embedding caching to reduce API calls
- Multi-provider AI support:
  - OpenAI (GPT-4, text-embedding-3-small)
  - Anthropic (Claude 3)
  - Google (Gemini Pro)
- RAG-enhanced recommendations using document context
- Structured analysis output (recommendation, risk, factors)

#### Frontend (Next.js 14 + TypeScript)

**Core Setup:**
- Next.js 14 with App Router
- TypeScript strict mode
- Tailwind CSS with custom dark theme
- React Query for server state management
- Zustand for client state management

**Components:**
- Layout: `Header`, `Sidebar` (responsive)
- UI: `Card`, `Badge`, `ProbabilityBar`, `LoadingSpinner`
- Predictions: `DailyPicks`, `PredictionStats`, `AIRecommendation`
- Matches: `LiveMatches`, `UpcomingMatches`

**API Integration:**
- `lib/api.ts` - Axios client with interceptors
- `hooks/useApi.ts` - React Query hooks for all endpoints
- `lib/store.ts` - Zustand stores (app, favorites, live matches)
- `lib/utils.ts` - Utility functions (formatting, colors)

**Features:**
- Dashboard with live matches, daily picks, upcoming fixtures
- Probability visualizations (stacked bar, progress bar)
- Team form indicators (W/D/L badges)
- AI recommendation panel with provider selection
- Model performance tracking

#### DevOps

**Docker:**
- `docker-compose.yml` - Full stack orchestration
  - PostgreSQL 16 with pgvector
  - Redis 7
  - Django backend
  - Celery worker + beat
  - Next.js frontend

**Configuration Files:**
- `.env.example` - Environment variables template
- `requirements.txt` - Python dependencies
- `package.json` - Node dependencies
- `tailwind.config.js` - Tailwind configuration
- `tsconfig.json` - TypeScript configuration

### Supported Leagues (20)

| Tier | League | Country | Code |
|------|--------|---------|------|
| 1 | Premier League | England | E0 |
| 1 | La Liga | Spain | SP1 |
| 1 | Serie A | Italy | I1 |
| 1 | Bundesliga | Germany | D1 |
| 1 | Ligue 1 | France | F1 |
| 2 | Eredivisie | Netherlands | N1 |
| 2 | Primeira Liga | Portugal | P1 |
| 2 | Pro League | Belgium | B1 |
| 2 | Super Lig | Turkey | T1 |
| 2 | Super League | Greece | G1 |
| 2 | Primera Division | Argentina | ARG |
| 2 | Serie A | Brazil | BRA |
| 3 | Championship | England | E1 |
| 3 | La Liga 2 | Spain | SP2 |
| 3 | Serie B | Italy | I2 |
| 3 | 2. Bundesliga | Germany | D2 |
| 3 | Ligue 2 | France | F2 |
| 4 | Premiership | Scotland | SC0 |
| 4 | League One | England | E2 |
| 4 | League Two | England | E3 |

### Data Sources

All data sources are **completely free** with no payment required:

1. **Football-Data.co.uk** (Primary)
   - CSV downloads with 10+ years of data
   - Match results, statistics, betting odds
   - URL: https://www.football-data.co.uk

2. **Understat** (xG Data)
   - Expected Goals (xG, xGA, xPTS)
   - Shot-level data
   - URL: https://understat.com

3. **FBref via SoccerData** (Additional stats)
   - Comprehensive team/player statistics
   - Python package: soccerdata

---

## How to Run

See [README.md](./README.md) for detailed setup instructions.

Quick start:
```bash
# Start all services with Docker
docker compose up -d --build

# Run migrations (first time)
docker compose exec backend python manage.py migrate

# Access:
# - Backend API: http://localhost:8000/api/v1/
# - Frontend:    http://localhost:3001
# - Flower:      http://localhost:5555

# Or run manually:
# Terminal 1: Backend
cd backend && python manage.py migrate && python manage.py runserver

# Terminal 2: Celery
cd backend && celery -A config worker -l info

# Terminal 3: Frontend
cd frontend && npm install && npm run dev
```

## Future Enhancements

- [ ] User authentication and profiles
- [ ] Email notifications for predictions
- [ ] Mobile app (React Native)
- [ ] Additional AI models (Llama, Mistral)
- [ ] Real-time odds integration
- [ ] Telegram bot integration
