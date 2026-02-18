# Bet_Hope

## AI-Powered Football Match Prediction Platform

> A full-stack production-grade platform that leverages Machine Learning and AI to predict football match outcomes across the world's top leagues.

---

## Project Structure

```
Bet_Hope/
│
├── README.md                    # This file - Project overview
├── docker-compose.yml           # Full stack orchestration
├── .gitignore                   # Git ignore rules
│
├── backend/                     # Django + ML Backend
│   ├── config/                  # Django project settings
│   ├── apps/                    # Django applications
│   ├── ml/                      # Machine Learning module
│   ├── ai/                      # Document AI module
│   ├── tasks/                   # Celery background tasks
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # Backend container
│   └── docs/                    # Backend documentation
│
├── frontend/                    # Next.js Frontend
│   ├── src/                     # Source code
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── lib/                 # Utilities & API client
│   │   ├── stores/              # State management
│   │   └── types/               # TypeScript types
│   ├── public/                  # Static assets
│   ├── package.json             # Node dependencies
│   ├── Dockerfile               # Frontend container
│   └── README.md                # Frontend documentation
│
└── shared/                      # Shared resources
    ├── types/                   # Shared TypeScript types
    └── assets/                  # Shared design assets
```

---

## Quick Reference (Common Commands)

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f backend

# Check status
docker compose ps

# Restart after code changes
docker compose restart backend celery celery-beat

# Rebuild backend (after requirements.txt changes)
docker compose build backend && docker compose up -d

# Access URLs
# Frontend:  http://localhost:3001
# Backend:   http://localhost:8000/api/v1/
# Flower:    http://localhost:5555
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16
- Redis 7
- Docker & Docker Compose (optional)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/bet-hope.git
cd bet-hope

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Start all services
docker compose up -d --build

# Run migrations (first time only)
docker compose exec backend python manage.py migrate

# Access the services:
# Backend API: http://localhost:8000/api/v1/
# Frontend:    http://localhost:3001
# Flower:      http://localhost:5555
```

### Option 2: Manual Setup

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## Technology Stack

### Backend (Django)

| Layer | Technology |
|-------|------------|
| Framework | Django 5.x + DRF |
| Database | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis + Celery |
| ML | XGBoost + Scikit-learn |
| AI/NLP | Sentence Transformers + HuggingFace |

### Frontend (Next.js)

| Layer | Technology |
|-------|------------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State | Zustand / React Query |
| Charts | Recharts / Chart.js |

### Infrastructure

| Component | Technology |
|-----------|------------|
| Containers | Docker + Docker Compose |
| Web Server | Nginx + Gunicorn |
| Monitoring | Prometheus + Grafana |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                   │
│                          (Next.js + React)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  Pages:                                                                 │
│  • Dashboard          • Match Details       • League Standings          │
│  • Predictions        • Team Profiles       • Model Analytics           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                    │
│                       (Django REST Framework)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   REST API   │  │  ML Service  │  │  Data Sync   │  │ Document AI │ │
│  │   Endpoints  │  │  Predictions │  │  Celery Jobs │  │  Embeddings │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
            │ PostgreSQL  │  │    Redis    │  │  External   │
            │  + pgvector │  │    Cache    │  │    APIs     │
            └─────────────┘  └─────────────┘  └─────────────┘
```

---

## Core Features

### Match Predictions
- Win/Draw/Loss probabilities
- Predicted scorelines
- Confidence scores (0-1)
- Key influencing factors
- Historical accuracy tracking

### Data Pipeline
- Auto-sync from Football-Data.org & API-Football
- 15-min live updates during matches
- Daily historical data refresh
- Weekly model retraining

### Document AI & RAG
- **News Scraping**: Auto-scrapes football news from ESPN, BBC Sport, Sky Sports
- **Betting Guides**: Built-in strategy documents for RAG context
- **Vector Embeddings**: pgvector for semantic search
- **AI Recommendations**: RAG-enhanced analysis using OpenAI, Claude, or Gemini

### Scheduled Background Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| Data Sync | 4:00 AM UTC | Download latest match data |
| Model Training | 5:00 AM UTC | Retrain prediction models |
| Generate Predictions | Every 6 hours | Update match predictions |
| Update Results | Every 3 hours | Fetch completed match results |
| **Morning News Scrape** | 6:00 AM UTC | Scrape football news RSS feeds |
| **Evening News Scrape** | 6:00 PM UTC | Scrape football news RSS feeds |
| Document Refresh | 4:30 AM UTC | Full document refresh pipeline |
| Embed Documents | 4:45 AM UTC | Generate embeddings for RAG |
| Cleanup Old News | 5:30 AM UTC | Remove news older than 7 days |
| Weekly Cleanup | Sunday 3:00 AM | Clean up old data and embeddings |

### Multi-League Support
- **Tier 1:** Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- **Tier 2:** Eredivisie, Primeira Liga, Championship
- **International:** Champions League, Europa League

---

## Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Backend README | `backend/README.md` | Django setup & API reference |
| Frontend README | `frontend/README.md` | Next.js setup & components |
| Database Schema | `backend/docs/DATABASE.md` | PostgreSQL schema & ERD |
| ML Pipeline | `backend/docs/ML_PIPELINE.md` | Feature engineering & training |
| API Reference | `backend/docs/API.md` | REST API endpoints |

---

## Development Workflow

### Branch Strategy

```
main           → Production-ready code
├── develop    → Integration branch
│   ├── feature/predictions-v2
│   ├── feature/live-updates
│   └── fix/prediction-accuracy
└── release/*  → Release candidates
```

### Commit Convention

```
feat(predictions): add confidence score breakdown
fix(api): correct pagination in matches endpoint
docs(readme): update installation steps
```

---

## Environment Variables

### Backend (`backend/.env`)

```bash
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/bet_hope
REDIS_URL=redis://localhost:6379/0
FOOTBALL_DATA_API_KEY=your-key
```

### Frontend (`frontend/.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

---

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/predictions/upcoming/` | GET | Upcoming match predictions |
| `/api/v1/predictions/match/{id}/` | GET | Single match prediction |
| `/api/v1/predictions/value-bets/` | GET | Value bet suggestions |
| `/api/v1/matches/` | GET | List matches |
| `/api/v1/matches/live/` | GET | Live matches |
| `/api/v1/leagues/{id}/standings/` | GET | League table |
| `/api/v1/teams/{id}/form/` | GET | Team form analysis |
| `/api/v1/ai-recommendations/generate/` | POST | Generate AI recommendation |
| `/api/v1/ai-recommendations/providers/` | GET | List available AI providers |
| `/api/v1/documents/` | GET | List documents for RAG |
| `/api/v1/documents/stats/` | GET | Document statistics |
| `/api/v1/documents/search/?q=query` | GET | Search documents (vector similarity) |
| `/api/v1/documents/refresh/` | POST | Trigger document refresh |
| `/api/v1/documents/scrape-news/` | POST | Scrape latest football news |
| `/api/v1/documents/upload/` | POST | Upload new document |

Full API documentation: `backend/docs/API.md`

---

## Deployment

### Docker Commands

#### Start All Services
```bash
# Start all services in detached mode
docker compose up -d

# Or with full path (macOS)
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

#### Stop All Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes database data)
docker compose down -v
```

#### Start/Stop Individual Services
```bash
# Start only backend and frontend
docker compose up -d backend frontend

# Stop only backend
docker compose stop backend

# Restart backend
docker compose restart backend

# Restart celery workers (after code changes)
docker compose restart celery celery-beat
```

#### Rebuild After Code Changes
```bash
# Rebuild and restart backend
docker compose build backend && docker compose up -d backend

# Rebuild all services
docker compose build && docker compose up -d
```

#### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f celery
```

#### Check Service Status
```bash
docker compose ps
```

### Services (Development)

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| frontend | 3001 | http://localhost:3001 | Next.js app (dev mode) |
| backend | 8000 | http://localhost:8000/api/v1/ | Django API |
| celery | - | - | Background workers |
| celery-beat | - | - | Task scheduler |
| flower | 5555 | http://localhost:5555 | Celery monitoring |
| postgres | 5432 | - | PostgreSQL + pgvector |
| redis | 6379 | - | Cache & queue |

### Services (Production)

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80/443 | Reverse proxy |
| frontend | 3000 | Next.js app |
| backend | 8000 | Django API |
| celery | - | Background workers |
| celery-beat | - | Task scheduler |
| postgres | 5432 | Database |
| redis | 6379 | Cache & queue |

---

## Roadmap

### Phase 1: Foundation ✅
- [x] Project structure
- [x] Django models & API
- [x] Data ingestion pipeline (Football-Data.co.uk, Understat)
- [x] Basic frontend pages

### Phase 2: ML Core ✅
- [x] Feature engineering (Team, Match, H2H features)
- [x] XGBoost model training with hyperparameter tuning
- [x] Prediction API with value bet detection
- [x] Frontend integration with React Query

### Phase 3: AI & RAG ✅
- [x] Document AI with vector embeddings (pgvector)
- [x] Multi-provider AI (OpenAI, Claude, Gemini)
- [x] RAG-enhanced recommendations
- [x] AI analysis UI component

### Phase 4: Production (In Progress)
- [x] Docker Compose configuration
- [ ] Real-time updates (WebSocket)
- [ ] Email notifications
- [ ] CI/CD pipeline

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## License

Proprietary - All rights reserved.

---

## Contact

For questions, open an issue or contact the development team.
