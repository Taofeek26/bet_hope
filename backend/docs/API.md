# Bet_Hope API Documentation

## Overview

RESTful API built with Django REST Framework providing football predictions and match data.

**Base URL:** `https://api.bet-hope.com/api/v1/`

---

## Authentication

### JWT Authentication

All endpoints require JWT authentication unless marked as public.

**Obtain Token:**
```http
POST /api/v1/auth/token/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "your_password"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Refresh Token:**
```http
POST /api/v1/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Using Token:**
```http
GET /api/v1/predictions/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## Rate Limiting

| Tier | Requests/Hour | Requests/Day |
|------|---------------|--------------|
| Free | 100 | 1,000 |
| Basic | 1,000 | 10,000 |
| Pro | 10,000 | 100,000 |

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640000000
```

---

## Endpoints

### Predictions

#### Get Upcoming Predictions

Returns predictions for all scheduled matches.

```http
GET /api/v1/predictions/upcoming/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| league | int | Filter by league ID |
| date | date | Filter by match date (YYYY-MM-DD) |
| date_from | date | Start date range |
| date_to | date | End date range |
| min_confidence | float | Minimum confidence score (0-1) |
| page | int | Page number |
| page_size | int | Results per page (max 100) |

**Response:**
```json
{
    "count": 45,
    "next": "https://api.bet-hope.com/api/v1/predictions/upcoming/?page=2",
    "previous": null,
    "results": [
        {
            "id": 12345,
            "match": {
                "id": 67890,
                "home_team": {
                    "id": 1,
                    "name": "Arsenal",
                    "short_name": "ARS",
                    "logo_url": "https://..."
                },
                "away_team": {
                    "id": 2,
                    "name": "Chelsea",
                    "short_name": "CHE",
                    "logo_url": "https://..."
                },
                "league": {
                    "id": 1,
                    "name": "Premier League",
                    "country": "England"
                },
                "match_date": "2024-01-15",
                "kickoff_time": "15:00:00",
                "kickoff_utc": "2024-01-15T15:00:00Z",
                "venue": "Emirates Stadium",
                "matchweek": 21
            },
            "prediction": {
                "home_win_probability": 0.5234,
                "draw_probability": 0.2512,
                "away_win_probability": 0.2254,
                "predicted_score": "2-1",
                "confidence_score": 0.7123,
                "prediction_strength": "STRONG",
                "recommended_outcome": "HOME"
            },
            "key_factors": [
                "Arsenal excellent home form (W4-D1-L0)",
                "Chelsea missing 2 key defenders",
                "H2H at Emirates favors Arsenal (60%)"
            ],
            "model_version": "20240110_030000",
            "created_at": "2024-01-10T04:00:00Z"
        }
    ]
}
```

---

#### Get Match Prediction

Returns detailed prediction for a specific match.

```http
GET /api/v1/predictions/match/{match_id}/
```

**Response:**
```json
{
    "id": 12345,
    "match": {
        "id": 67890,
        "home_team": {
            "id": 1,
            "name": "Arsenal",
            "short_name": "ARS",
            "logo_url": "https://...",
            "form": "WWDWW",
            "league_position": 1,
            "points": 52
        },
        "away_team": {
            "id": 2,
            "name": "Chelsea",
            "short_name": "CHE",
            "logo_url": "https://...",
            "form": "WLDWL",
            "league_position": 8,
            "points": 35
        },
        "league": {
            "id": 1,
            "name": "Premier League",
            "country": "England"
        },
        "match_date": "2024-01-15",
        "kickoff_time": "15:00:00",
        "kickoff_utc": "2024-01-15T15:00:00Z",
        "venue": "Emirates Stadium",
        "matchweek": 21,
        "referee": "Michael Oliver"
    },
    "prediction": {
        "home_win_probability": 0.5234,
        "draw_probability": 0.2512,
        "away_win_probability": 0.2254,
        "confidence_score": 0.7123,
        "prediction_strength": "STRONG",
        "recommended_outcome": "HOME",
        "scoreline_probabilities": {
            "1-0": 0.12,
            "2-0": 0.10,
            "2-1": 0.15,
            "1-1": 0.11,
            "0-0": 0.08,
            "0-1": 0.06,
            "0-2": 0.04
        },
        "predicted_score": {
            "home": 2,
            "away": 1
        }
    },
    "analysis": {
        "key_factors": [
            "Arsenal excellent home form (W4-D1-L0 last 5)",
            "Chelsea missing Reece James and Ben Chilwell",
            "H2H at Emirates: Arsenal 60% win rate",
            "Arsenal averaging 2.4 goals/game at home"
        ],
        "home_team_strengths": [
            "Strong attacking play (2.1 xG avg)",
            "Solid home record (W7-D2-L1)",
            "Full strength squad available"
        ],
        "away_team_weaknesses": [
            "Poor away form (W2-D3-L5)",
            "Defensive injuries"
        ],
        "head_to_head": {
            "total_matches": 15,
            "home_wins": 8,
            "draws": 4,
            "away_wins": 3,
            "last_meeting": {
                "date": "2023-05-02",
                "score": "3-1",
                "venue": "Emirates Stadium"
            }
        }
    },
    "model_version": "20240110_030000",
    "created_at": "2024-01-10T04:00:00Z"
}
```

---

#### Get League Predictions

Returns all predictions for a specific league.

```http
GET /api/v1/predictions/league/{league_id}/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| matchweek | int | Filter by matchweek |
| date_from | date | Start date |
| date_to | date | End date |

---

#### Get Today's Predictions

Returns predictions for today's matches.

```http
GET /api/v1/predictions/today/
```

---

#### Get Prediction History

Returns historical predictions with outcomes.

```http
GET /api/v1/predictions/history/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| league | int | Filter by league |
| is_correct | bool | Filter by prediction accuracy |
| date_from | date | Start date |
| date_to | date | End date |

**Response:**
```json
{
    "count": 1500,
    "results": [
        {
            "id": 11111,
            "match": {
                "id": 55555,
                "home_team": "Liverpool",
                "away_team": "Man City",
                "home_score": 2,
                "away_score": 2,
                "match_date": "2024-01-10"
            },
            "prediction": {
                "home_win_probability": 0.35,
                "draw_probability": 0.30,
                "away_win_probability": 0.35,
                "recommended_outcome": "HOME",
                "confidence_score": 0.45
            },
            "actual_outcome": "DRAW",
            "is_correct": false,
            "created_at": "2024-01-08T04:00:00Z"
        }
    ]
}
```

---

### Matches

#### List Matches

```http
GET /api/v1/matches/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| league | int | Filter by league ID |
| team | int | Filter by team ID |
| status | string | scheduled, live, finished |
| season | string | e.g., "2023-2024" |
| date_from | date | Start date |
| date_to | date | End date |

**Response:**
```json
{
    "count": 380,
    "results": [
        {
            "id": 67890,
            "home_team": {
                "id": 1,
                "name": "Arsenal",
                "logo_url": "https://..."
            },
            "away_team": {
                "id": 2,
                "name": "Chelsea",
                "logo_url": "https://..."
            },
            "league": {
                "id": 1,
                "name": "Premier League"
            },
            "match_date": "2024-01-15",
            "kickoff_time": "15:00:00",
            "status": "scheduled",
            "home_score": null,
            "away_score": null,
            "season": "2023-2024",
            "matchweek": 21,
            "venue": "Emirates Stadium"
        }
    ]
}
```

---

#### Get Match Details

```http
GET /api/v1/matches/{match_id}/
```

**Response:**
```json
{
    "id": 67890,
    "home_team": {
        "id": 1,
        "name": "Arsenal",
        "short_name": "ARS",
        "logo_url": "https://...",
        "stadium": "Emirates Stadium"
    },
    "away_team": {
        "id": 2,
        "name": "Chelsea",
        "short_name": "CHE",
        "logo_url": "https://..."
    },
    "league": {
        "id": 1,
        "name": "Premier League",
        "country": "England"
    },
    "match_date": "2024-01-15",
    "kickoff_time": "15:00:00",
    "kickoff_utc": "2024-01-15T15:00:00Z",
    "status": "finished",
    "home_score": 2,
    "away_score": 1,
    "home_halftime_score": 1,
    "away_halftime_score": 0,
    "season": "2023-2024",
    "matchweek": 21,
    "venue": "Emirates Stadium",
    "attendance": 60234,
    "referee": "Michael Oliver",
    "statistics": {
        "possession_home": 58.5,
        "possession_away": 41.5,
        "shots_home": 15,
        "shots_away": 10,
        "shots_on_target_home": 6,
        "shots_on_target_away": 4,
        "corners_home": 7,
        "corners_away": 3,
        "fouls_home": 12,
        "fouls_away": 14,
        "yellow_cards_home": 2,
        "yellow_cards_away": 3,
        "xg_home": 2.15,
        "xg_away": 0.95
    }
}
```

---

#### Get Live Matches

```http
GET /api/v1/matches/live/
```

**Response:**
```json
{
    "count": 5,
    "results": [
        {
            "id": 67890,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "home_score": 1,
            "away_score": 0,
            "minute": 67,
            "status": "live",
            "events": [
                {
                    "minute": 34,
                    "type": "goal",
                    "team": "home",
                    "player": "Bukayo Saka"
                }
            ]
        }
    ]
}
```

---

### Teams

#### List Teams

```http
GET /api/v1/teams/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| league | int | Filter by league |
| search | string | Search by name |

---

#### Get Team Details

```http
GET /api/v1/teams/{team_id}/
```

**Response:**
```json
{
    "id": 1,
    "name": "Arsenal",
    "short_name": "ARS",
    "logo_url": "https://...",
    "league": {
        "id": 1,
        "name": "Premier League"
    },
    "founded": 1886,
    "stadium": "Emirates Stadium",
    "stadium_capacity": 60704,
    "city": "London",
    "website": "https://www.arsenal.com",
    "current_season": {
        "position": 1,
        "points": 52,
        "matches_played": 21,
        "wins": 16,
        "draws": 4,
        "losses": 1,
        "goals_for": 45,
        "goals_against": 18,
        "goal_difference": 27,
        "form": "WWDWW"
    }
}
```

---

#### Get Team Form

```http
GET /api/v1/teams/{team_id}/form/
```

**Response:**
```json
{
    "team_id": 1,
    "team_name": "Arsenal",
    "form_string": "WWDWW",
    "last_5_matches": [
        {
            "match_id": 67880,
            "opponent": "Fulham",
            "result": "W",
            "score": "2-1",
            "date": "2024-01-08",
            "venue": "home"
        }
    ],
    "stats": {
        "points_last_5": 13,
        "goals_scored_last_5": 10,
        "goals_conceded_last_5": 3,
        "clean_sheets_last_5": 2,
        "xg_last_5": 11.2,
        "xga_last_5": 4.5
    },
    "home_form": {
        "form_string": "WWWW",
        "points_last_5_home": 12,
        "goals_scored": 12,
        "goals_conceded": 2
    },
    "away_form": {
        "form_string": "DWLW",
        "points_last_5_away": 7,
        "goals_scored": 6,
        "goals_conceded": 5
    }
}
```

---

#### Get Team Fixtures

```http
GET /api/v1/teams/{team_id}/fixtures/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | upcoming, completed |
| limit | int | Number of fixtures |

---

#### Get Team Players

```http
GET /api/v1/teams/{team_id}/players/
```

**Response:**
```json
{
    "team_id": 1,
    "team_name": "Arsenal",
    "squad": [
        {
            "id": 101,
            "name": "Bukayo Saka",
            "position": "Right Winger",
            "position_category": "FWD",
            "shirt_number": 7,
            "nationality": "England",
            "age": 22,
            "injury_status": "fit",
            "market_value": 120000000
        },
        {
            "id": 102,
            "name": "Martin Odegaard",
            "position": "Attacking Midfielder",
            "position_category": "MID",
            "shirt_number": 8,
            "nationality": "Norway",
            "age": 25,
            "injury_status": "injured",
            "injury_description": "Ankle injury",
            "injury_expected_return": "2024-02-01",
            "market_value": 100000000
        }
    ],
    "injured_players": 2,
    "suspended_players": 0
}
```

---

### Leagues

#### List Leagues

```http
GET /api/v1/leagues/
```

**Response:**
```json
{
    "count": 20,
    "results": [
        {
            "id": 1,
            "name": "Premier League",
            "country": "England",
            "logo_url": "https://...",
            "current_season": "2023-2024",
            "current_matchweek": 21,
            "is_active": true
        }
    ]
}
```

---

#### Get League Standings

```http
GET /api/v1/leagues/{league_id}/standings/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| season | string | Season (default: current) |

**Response:**
```json
{
    "league": {
        "id": 1,
        "name": "Premier League"
    },
    "season": "2023-2024",
    "standings": [
        {
            "position": 1,
            "team": {
                "id": 1,
                "name": "Arsenal",
                "logo_url": "https://..."
            },
            "matches_played": 21,
            "wins": 16,
            "draws": 4,
            "losses": 1,
            "goals_for": 45,
            "goals_against": 18,
            "goal_difference": 27,
            "points": 52,
            "form": "WWDWW",
            "next_match": {
                "opponent": "Chelsea",
                "date": "2024-01-15",
                "venue": "home"
            }
        }
    ]
}
```

---

#### Get League Fixtures

```http
GET /api/v1/leagues/{league_id}/fixtures/
```

---

#### Get League Top Scorers

```http
GET /api/v1/leagues/{league_id}/top-scorers/
```

**Response:**
```json
{
    "league_id": 1,
    "season": "2023-2024",
    "top_scorers": [
        {
            "rank": 1,
            "player": {
                "id": 201,
                "name": "Erling Haaland",
                "team": "Manchester City"
            },
            "goals": 18,
            "assists": 4,
            "matches_played": 20,
            "minutes_played": 1650,
            "goals_per_90": 0.98
        }
    ]
}
```

---

### Analytics

#### Get Model Performance

```http
GET /api/v1/analytics/model-performance/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| league | int | Filter by league |
| period | string | 7d, 30d, 90d, all |

**Response:**
```json
{
    "model_version": "20240110_030000",
    "period": "30d",
    "overall": {
        "total_predictions": 450,
        "correct_predictions": 285,
        "accuracy": 0.633,
        "log_loss": 0.912,
        "brier_score": 0.182
    },
    "by_outcome": {
        "home": {
            "predictions": 200,
            "correct": 140,
            "accuracy": 0.70
        },
        "draw": {
            "predictions": 100,
            "correct": 35,
            "accuracy": 0.35
        },
        "away": {
            "predictions": 150,
            "correct": 110,
            "accuracy": 0.73
        }
    },
    "by_confidence": {
        "high": {
            "threshold": 0.7,
            "predictions": 120,
            "accuracy": 0.75
        },
        "medium": {
            "threshold": 0.55,
            "predictions": 200,
            "accuracy": 0.62
        },
        "low": {
            "predictions": 130,
            "accuracy": 0.52
        }
    },
    "by_league": [
        {
            "league_id": 1,
            "league_name": "Premier League",
            "predictions": 100,
            "accuracy": 0.65
        }
    ],
    "trend": [
        {
            "week": "2024-W01",
            "predictions": 45,
            "accuracy": 0.64
        }
    ]
}
```

---

## Webhooks

### Subscribe to Events

```http
POST /api/v1/webhooks/
```

**Request:**
```json
{
    "url": "https://your-server.com/webhook",
    "events": ["prediction.created", "match.finished"],
    "leagues": [1, 2, 3],
    "secret": "your_webhook_secret"
}
```

**Events:**
- `prediction.created` - New prediction generated
- `match.started` - Match kicked off
- `match.finished` - Match ended
- `model.updated` - New model deployed

**Webhook Payload:**
```json
{
    "event": "prediction.created",
    "timestamp": "2024-01-10T04:00:00Z",
    "data": {
        "prediction_id": 12345,
        "match_id": 67890,
        "home_team": "Arsenal",
        "away_team": "Chelsea"
    },
    "signature": "sha256=..."
}
```

---

## Error Responses

### Standard Error Format

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid request parameters",
        "details": [
            {
                "field": "date_from",
                "message": "Invalid date format. Use YYYY-MM-DD"
            }
        ]
    }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| UNAUTHORIZED | 401 | Invalid or missing token |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMITED | 429 | Rate limit exceeded |
| VALIDATION_ERROR | 400 | Invalid request data |
| SERVER_ERROR | 500 | Internal server error |

---

## SDKs

### Python

```python
from bet_hope import BetHopeClient

client = BetHopeClient(api_key="your_api_key")

# Get predictions
predictions = client.predictions.upcoming(league=1)

# Get match details
match = client.matches.get(67890)

# Get team form
form = client.teams.form(team_id=1)
```

### JavaScript

```javascript
import { BetHopeClient } from '@bet-hope/sdk';

const client = new BetHopeClient({ apiKey: 'your_api_key' });

// Get predictions
const predictions = await client.predictions.upcoming({ league: 1 });

// Get match details
const match = await client.matches.get(67890);
```

---

## Changelog

### v1.0.0 (2024-01)
- Initial release
- Core prediction endpoints
- Match and team data
- League standings
