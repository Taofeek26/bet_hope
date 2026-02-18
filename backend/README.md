# Bet_Hope Backend

## Django + ML API Server

Django REST Framework backend with Machine Learning prediction engine.

---

## Project Structure

```
backend/
│
├── config/                      # Django project configuration
│   ├── settings/
│   │   ├── base.py             # Base settings
│   │   ├── development.py      # Dev settings
│   │   ├── production.py       # Production settings
│   │   └── testing.py          # Test settings
│   ├── urls.py                  # Root URL configuration
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py                # Celery configuration
│
├── apps/                        # Django applications
│   ├── core/                    # Shared utilities & base models
│   ├── accounts/                # User authentication
│   ├── leagues/                 # League management
│   ├── teams/                   # Team management
│   ├── players/                 # Player management
│   ├── matches/                 # Match data & statistics
│   ├── predictions/             # ML predictions
│   ├── data_ingestion/          # External API sync
│   └── analytics/               # Model performance
│
├── ml/                          # Machine Learning module
│   ├── features/                # Feature engineering
│   ├── models/                  # ML model definitions
│   ├── training/                # Training pipeline
│   ├── inference/               # Prediction serving
│   └── artifacts/               # Trained models storage
│
├── ai/                          # Document AI module
│   ├── embeddings/              # Text embeddings
│   ├── processing/              # Document processing
│   └── search/                  # Semantic search
│
├── tasks/                       # Celery background tasks
│   ├── data_sync.py
│   ├── predictions.py
│   ├── training.py
│   └── documents.py
│
├── tests/                       # Test suite
├── scripts/                     # Utility scripts
├── docs/                        # Documentation
│
├── manage.py
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis 7

### Installation

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed initial leagues
python manage.py seed_leagues

# Run development server
python manage.py runserver
```

### Running Celery

```bash
# Terminal 1: Celery worker
celery -A config worker -l info

# Terminal 2: Celery beat (scheduler)
celery -A config beat -l info

# Terminal 3: Flower (monitoring - optional)
celery -A config flower
```

---

## Django Apps

### `apps.core`
Shared utilities, base models, custom exceptions.

### `apps.accounts`
User authentication with JWT.

### `apps.leagues`
League configuration and management.

```python
# Models
League(name, country, api_league_id, is_active, priority_rank)
```

### `apps.teams`
Team data and season statistics.

```python
# Models
Team(league, name, short_name, logo_url, stadium)
SeasonStatistics(team, season, position, points, form)
```

### `apps.players`
Player information and injury tracking.

```python
# Models
Player(team, name, position, injury_status, market_value)
```

### `apps.matches`
Match fixtures, results, and statistics.

```python
# Models
Match(home_team, away_team, league, match_date, status, score)
MatchStatistics(match, possession, shots, xg, corners)
```

### `apps.predictions`
ML predictions for matches.

```python
# Models
Prediction(match, home_win_prob, draw_prob, away_win_prob, confidence)
```

### `apps.data_ingestion`
External API connectors and data sync.

### `apps.analytics`
Model performance tracking and metrics.

---

## API Endpoints

### Authentication

```
POST /api/v1/auth/token/           # Obtain JWT token
POST /api/v1/auth/token/refresh/   # Refresh token
POST /api/v1/auth/register/        # User registration
```

### Predictions

```
GET  /api/v1/predictions/upcoming/           # All upcoming predictions
GET  /api/v1/predictions/today/              # Today's predictions
GET  /api/v1/predictions/match/{id}/         # Single match prediction
GET  /api/v1/predictions/league/{id}/        # Predictions by league
GET  /api/v1/predictions/history/            # Historical predictions
```

### Matches

```
GET  /api/v1/matches/                        # List matches
GET  /api/v1/matches/{id}/                   # Match details
GET  /api/v1/matches/live/                   # Live matches
```

### Teams

```
GET  /api/v1/teams/                          # List teams
GET  /api/v1/teams/{id}/                     # Team details
GET  /api/v1/teams/{id}/form/                # Team form
GET  /api/v1/teams/{id}/fixtures/            # Team fixtures
GET  /api/v1/teams/{id}/players/             # Team squad
```

### Leagues

```
GET  /api/v1/leagues/                        # List leagues
GET  /api/v1/leagues/{id}/                   # League details
GET  /api/v1/leagues/{id}/standings/         # League table
GET  /api/v1/leagues/{id}/fixtures/          # League fixtures
GET  /api/v1/leagues/{id}/top-scorers/       # Top scorers
```

### Analytics

```
GET  /api/v1/analytics/model-performance/    # Model metrics
GET  /api/v1/analytics/prediction-accuracy/  # Accuracy by league
```

---

## ML Module

### Feature Engineering

```python
# ml/features/
├── form_features.py          # Last 5/10 match form
├── historical_features.py    # Head-to-head records
├── team_features.py          # League position, xG
├── player_features.py        # Injuries, suspensions
├── contextual_features.py    # Home/away, rest days
└── document_features.py      # News sentiment
```

### Model Training

```bash
# Train model manually
python manage.py train_model --seasons 3 --test-size 0.2

# Or via Celery task
from tasks.training import retrain_model
retrain_model.delay()
```

### Prediction Generation

```bash
# Generate predictions for upcoming matches
python manage.py generate_predictions --days 7

# Or via Celery task
from tasks.predictions import generate_predictions
generate_predictions.delay()
```

---

## Celery Tasks

### Task Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_live_matches` | Every 15 min | Update live match scores |
| `sync_fixtures` | Every 6 hours | Update fixture list |
| `sync_historical_data` | Daily 3:00 AM | Sync historical data |
| `retrain_model` | Daily 4:00 AM | Retrain ML model |
| `generate_predictions` | Every 4 hours | Generate predictions |
| `ingest_documents` | Every 2 hours | Process news articles |

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov=ml

# Run specific tests
pytest tests/test_api/
pytest tests/test_ml/
```

---

## Management Commands

```bash
# Seed leagues
python manage.py seed_leagues

# Backfill historical data
python manage.py backfill_historical --seasons 3

# Train model
python manage.py train_model

# Generate predictions
python manage.py generate_predictions

# Evaluate model
python manage.py evaluate_model --period 30

# Sync data
python manage.py sync_data --league PL
```

---

## Docker

### Build

```bash
docker build -t bet-hope-backend .
```

### Run

```bash
docker run -p 8000:8000 --env-file .env bet-hope-backend
```

---

## Documentation

| File | Description |
|------|-------------|
| `docs/DATABASE.md` | Database schema & ERD |
| `docs/ML_PIPELINE.md` | ML architecture & training |
| `docs/API.md` | Full API reference |

---

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection |
| `REDIS_URL` | Redis connection |
| `FOOTBALL_DATA_API_KEY` | Football-Data.org API key |
| `API_FOOTBALL_KEY` | API-Football key |
