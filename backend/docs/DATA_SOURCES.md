# Data Sources Documentation

## Overview

Bet_Hope uses **Football-Data.co.uk** as the primary free data source for both historical match data and upcoming fixtures. This document covers all data sources, their capabilities, and usage.

---

## Football-Data.co.uk (Primary Source)

**Website**: https://www.football-data.co.uk
**Cost**: FREE
**API Key Required**: No

### Historical Match Data

**URL Format**: `https://www.football-data.co.uk/mmz4281/{season}/{league}.csv`

**Example**: `https://www.football-data.co.uk/mmz4281/2526/E0.csv` (Premier League 2025-26)

**Data Available**:
- Match results (home/away scores, halftime scores)
- Match statistics (shots, corners, fouls, cards)
- Betting odds from multiple bookmakers
- Date range: **1993 to present** (30+ years)

**Season Format**: `YYZZ` where `20YY-20ZZ` (e.g., `2526` = 2025-26 season)

### Upcoming Fixtures

**URL**: `https://www.football-data.co.uk/fixtures.csv`

**Data Available**:
- Upcoming match schedule
- Kickoff times
- Betting odds (pre-match)
- Referee assignments

**Update Frequency**: Updated regularly (check every 1-2 hours for latest fixtures)

---

## Supported Leagues (20 Total)

### Tier 1 - Top 5 European Leagues
| Code | League | Country |
|------|--------|---------|
| E0 | Premier League | England |
| SP1 | La Liga | Spain |
| I1 | Serie A | Italy |
| D1 | Bundesliga | Germany |
| F1 | Ligue 1 | France |

### Tier 2 - Other Major European Leagues
| Code | League | Country |
|------|--------|---------|
| N1 | Eredivisie | Netherlands |
| B1 | Pro League | Belgium |
| P1 | Primeira Liga | Portugal |
| T1 | Super Lig | Turkey |
| G1 | Super League | Greece |
| SC0 | Scottish Premiership | Scotland |

### Tier 3 - Second Division Leagues
| Code | League | Country |
|------|--------|---------|
| E1 | Championship | England |
| SP2 | La Liga 2 | Spain |
| I2 | Serie B | Italy |
| D2 | 2. Bundesliga | Germany |
| F2 | Ligue 2 | France |

### Tier 4 - Additional Leagues
| Code | League | Country |
|------|--------|---------|
| E2 | League One | England |
| E3 | League Two | England |
| SC1 | Scottish Championship | Scotland |
| SC2 | Scottish League One | Scotland |

---

## CSV Column Reference

### Match Data Columns
| Column | Description |
|--------|-------------|
| Date | Match date (DD/MM/YYYY) |
| Time | Kickoff time (HH:MM) |
| HomeTeam | Home team name |
| AwayTeam | Away team name |
| FTHG | Full Time Home Goals |
| FTAG | Full Time Away Goals |
| FTR | Full Time Result (H/D/A) |
| HTHG | Half Time Home Goals |
| HTAG | Half Time Away Goals |

### Statistics Columns
| Column | Description |
|--------|-------------|
| HS / AS | Home/Away Shots |
| HST / AST | Home/Away Shots on Target |
| HC / AC | Home/Away Corners |
| HF / AF | Home/Away Fouls |
| HY / AY | Home/Away Yellow Cards |
| HR / AR | Home/Away Red Cards |

### Odds Columns
| Column | Description |
|--------|-------------|
| B365H/D/A | Bet365 Home/Draw/Away odds |
| BWH/D/A | Betway odds |
| PSH/D/A | Pinnacle odds |
| AvgH/D/A | Average market odds |
| Avg>2.5 / Avg<2.5 | Over/Under 2.5 goals |

---

## Management Commands

### Sync Historical Data
```bash
# Sync all 20 leagues, last 5 seasons (recommended for initial setup)
python manage.py sync_real_data --recent-only

# Sync all available seasons (30+ years, takes longer)
python manage.py sync_real_data

# Sync specific leagues and seasons
python manage.py sync_real_data --leagues E0 SP1 I1 --seasons 2526 2425

# Clear database and resync
python manage.py sync_real_data --clear --recent-only
```

### Sync Upcoming Fixtures
```bash
# Sync fixtures only (fast, run frequently)
python manage.py sync_real_data --fixtures-only

# Sync historical + fixtures
python manage.py sync_real_data --fixtures --recent-only
```

### Train ML Models
```bash
# Train with default settings (Top 5 leagues, last 3 seasons)
python manage.py train_model

# Train with specific leagues
python manage.py train_model --leagues E0 SP1 I1 D1 F1 --seasons 2526 2425 2324

# Train with hyperparameter tuning (slower but better)
python manage.py train_model --tune
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Football-Data.co.uk                          │
├─────────────────────────────────────────────────────────────────┤
│  Historical CSVs          │         Fixtures CSV                │
│  /mmz4281/{season}/{lg}   │         /fixtures.csv               │
└───────────┬───────────────┴──────────────┬──────────────────────┘
            │                              │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FootballDataProvider                          │
│  - download_csv(league, season)                                 │
│  - sync_to_database()                                           │
│  - download_fixtures()                                          │
│  - sync_fixtures()                                              │
└───────────┬───────────────┬──────────────┬──────────────────────┘
            │               │              │
            ▼               ▼              ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Leagues    │   │    Teams     │   │   Matches    │
│   Seasons    │   │              │   │   Stats      │
│              │   │              │   │   Odds       │
└──────────────┘   └──────────────┘   └──────┬───────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ML Pipeline                                 │
│  FeatureExtractor → ModelTrainer → Predictor                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Predictions                                 │
│  - Home/Draw/Away probabilities                                 │
│  - Confidence scores                                            │
│  - Recommended outcomes                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scheduled Tasks (Celery)

Add these to your Celery beat schedule for automated syncing:

```python
# config/celery.py
CELERY_BEAT_SCHEDULE = {
    # Sync fixtures every 2 hours
    'sync-fixtures': {
        'task': 'apps.data_ingestion.tasks.sync_fixtures',
        'schedule': crontab(minute=0, hour='*/2'),
    },
    # Full sync daily at 4 AM
    'sync-daily': {
        'task': 'apps.data_ingestion.tasks.sync_daily',
        'schedule': crontab(minute=0, hour=4),
    },
    # Retrain model weekly on Sunday
    'retrain-model': {
        'task': 'apps.ml_pipeline.tasks.train_model',
        'schedule': crontab(minute=0, hour=5, day_of_week=0),
    },
}
```

---

## Alternative Data Sources (For Reference)

These sources were evaluated but Football-Data.co.uk was chosen for its reliability and free access:

| Source | Type | Cost | Notes |
|--------|------|------|-------|
| **Football-Data.co.uk** | CSV | FREE | Primary source, 20 leagues, 30+ years |
| Understat | Scraping | FREE | xG data, 6 leagues only, async required |
| FBref/soccerdata | Scraping | FREE | Often blocked (403 errors) |
| API-Football | REST API | Paid | Rate limited free tier |
| football-data.org | REST API | Freemium | Limited free requests |

---

## Troubleshooting

### Common Issues

1. **"No data available" for a league/season**
   - Check if the season exists on Football-Data.co.uk
   - Older seasons may not have all leagues

2. **Fixtures not syncing**
   - Clear cache: `rm -rf data/raw/football_data/fixtures.csv`
   - Check if fixtures.csv URL is accessible

3. **BOM character issues in CSV**
   - Provider uses `BytesIO` with `encoding='utf-8-sig'` to handle this

4. **Model accuracy low**
   - Train with more data (more seasons)
   - Include odds features (strong predictors)
   - Use `--tune` flag for hyperparameter optimization

---

## File Locations

```
backend/
├── apps/
│   └── data_ingestion/
│       └── providers/
│           └── football_data.py    # Main data provider
├── data/
│   └── raw/
│       └── football_data/          # Cached CSV files
├── models/                         # Trained ML models
└── cache/
    └── features/                   # Feature cache
```

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-18 | 1.0 | Initial setup with 20 leagues, fixtures support |
