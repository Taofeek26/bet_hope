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
| Charts | Recharts |
| Animation | Framer Motion |

### Infrastructure

| Component | Technology |
|-----------|------------|
| Frontend hosting | Vercel |
| Backend hosting | AWS EC2 (Docker Compose) |
| ML tasks | AWS Lambda + API Gateway (SAM) |
| Containers | Docker + Docker Compose |
| Web Server | Nginx + Gunicorn |
| CI/CD | GitHub Actions + GHCR |

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

Full, current reference lists live in `backend/.env.example` and
`frontend/.env.example` (copy to `.env`/`.env.local`) — the essentials:

### Backend (`backend/.env`)

```bash
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/bet_hope
REDIS_URL=redis://localhost:6379/0
FOOTBALL_DATA_ORG_KEY=your-key
API_FOOTBALL_KEY=your-key
```

### Frontend (`frontend/.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
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

### Local Development (Docker)

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

---

## Production Deployment (AWS + Vercel)

The app is split across three targets, chosen to stay cheap and avoid a
NAT Gateway (see [`docs/AWS_COST_ESTIMATOR.md`](docs/AWS_COST_ESTIMATOR.md)
for the full cost reasoning):

| Component | Where | Why |
|-----------|-------|-----|
| Frontend (Next.js) | Vercel | Zero-config for Next.js, free tier covers most hobby traffic |
| Backend (Django + Postgres + Redis + Celery) | AWS EC2 (Docker Compose) | Needs a persistent DB connection; cheapest way to run Postgres/Redis without RDS/ElastiCache |
| ML tasks (train/predict/export/sync) | AWS Lambda + API Gateway | Genuinely serverless, ~$0.50-1/mo, no idle cost |

```
┌─────────────────────┐        ┌──────────────────────────────────────────┐
│       Vercel         │        │              AWS (us-east-1)              │
│   Next.js Frontend   │        │                                            │
│                       │  HTTP  │  ┌──────────────────────────────────────┐ │
│  api.yourdomain.com ─┼───────▶│  │  EC2 (t3.medium) — Docker Compose     │ │
│  or *.vercel.app      │        │  │  nginx → Django (Gunicorn) + Celery   │ │
└───────────────────────┘        │  │  Postgres (pgvector) + Redis          │ │
                                  │  └──────────────────┬───────────────────┘ │
                                  │                      │ private VPC        │
                                  │  ┌───────────────────▼──────────────────┐ │
                                  │  │  Lambda (VPC-attached, no NAT)        │ │
                                  │  │  train / predict / export             │ │
                                  │  └────────────────────────────────────────┘ │
                                  │  ┌────────────────────────────────────────┐ │
                                  │  │  Lambda (no VPC, has internet)         │ │
                                  │  │  sync → dispatches to EC2 via SSM      │ │
                                  │  └────────────────────────────────────────┘ │
                                  │  API Gateway (HTTP API) fronts both Lambdas │
                                  └────────────────────────────────────────────┘
```

No RDS, no ElastiCache, no ALB, no NAT Gateway anywhere in this setup.

### 1. Backend + ML infrastructure (AWS, via SAM)

Everything AWS-side is defined in [`infrastructure/template.yaml`](infrastructure/template.yaml)
and deployed with the AWS SAM CLI — never hand-edit resources in the console.

```bash
cd infrastructure
sam build

# First deploy — generates DBPassword and TasksApiKey yourself first:
#   openssl rand -hex 32   (run twice, once for each)
# Find your default VPC/subnet/route table:
#   aws ec2 describe-vpcs --filters Name=is-default,Values=true
#   aws ec2 describe-subnets --filters Name=default-for-az,Values=true
#   aws ec2 describe-route-tables

sam deploy --guided \
  --parameter-overrides \
    KeyPairName=your-ec2-keypair \
    DBPassword=<generated-above> \
    TasksApiKey=<generated-above> \
    LambdaVpcId=vpc-xxxxxxxx \
    LambdaSubnetId=subnet-xxxxxxxx \
    LambdaRouteTableId=rtb-xxxxxxxx
```

**Important:** `DBPassword` and `TasksApiKey` are `NoEcho` parameters — when
`sam deploy --guided` asks to save arguments to `samconfig.toml`, decline
(or manually strip them afterward). `samconfig.toml` is committed to this
repo for the non-secret parameters only.

This provisions the EC2 instance, S3 buckets, and both Lambda functions.
First boot takes a few minutes; SSH in and check `/var/log/user-data.log`
if something looks wrong. See [`docs/AWS_MINIMAL_DEPLOYMENT.md`](docs/AWS_MINIMAL_DEPLOYMENT.md)
for the detailed walkthrough (DNS, first-time `.env.prod` setup, etc).

### 2. Backend app deploys (GitHub Actions)

Once the EC2 instance exists, application code deploys via
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) on every push
to `main`: builds the Django image, pushes to GHCR, SSHes into EC2, and
runs `docker compose up -d --force-recreate` + migrations. Requires these
GitHub Secrets: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`.

Model training runs separately via
[`.github/workflows/train-model.yml`](.github/workflows/train-model.yml)
(nightly cron) — exports data from EC2, trains on the GitHub Actions
runner, commits the resulting model files, then activates the new version.

### 3. Frontend (Vercel)

1. Import the repo in the [Vercel dashboard](https://vercel.com/new) with
   root directory set to `frontend/`.
2. Set environment variables: `NEXT_PUBLIC_API_URL` (your EC2 API URL,
   e.g. `http://<elastic-ip>/api` or `https://api.yourdomain.com/api`),
   `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_APP_URL`.
3. Push to `main` — Vercel deploys automatically from there on, including
   preview deployments per branch/PR.
4. Back on the EC2 side, set `CORS_ALLOWED_ORIGINS` in `backend/.env.prod`
   to your actual Vercel URL(s), and `CORS_ALLOWED_ORIGIN_REGEXES` if you
   want Vercel's preview-deployment URLs to work too (see `.env.prod.example`).

### Calling the Lambda `/tasks/*` endpoints

All four routes (`/tasks/train`, `/tasks/predict`, `/tasks/export`,
`/tasks/sync`) require an `X-Api-Key` header matching the `TasksApiKey`
parameter you deployed with — they're on a public API Gateway URL with no
other auth:

```bash
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/tasks/train \
  -H "X-Api-Key: <your-tasks-api-key>"
```

### Local development

```bash
docker compose up -d
docker compose exec backend python manage.py migrate
```

See [Quick Start](#quick-start) above for the full local setup.

### Troubleshooting

**502 Bad Gateway** — check `docker compose -f docker-compose.prod.yml ps`
on the EC2 box; usually means the `backend` container crashed on boot
(check `docker compose logs backend`).

**400 Bad Request / DisallowedHost** — `DJANGO_ALLOWED_HOSTS` in
`backend/.env.prod` doesn't include the host you're hitting.

**CORS errors from the Vercel frontend** — `CORS_ALLOWED_ORIGINS` in
`backend/.env.prod` doesn't include your exact Vercel URL (must match
scheme + host exactly, no trailing slash).

**`relation "vector" does not exist` / pgvector errors** — the extension
wasn't created; run:
```bash
docker compose -f docker-compose.prod.yml exec db psql -U bet_hope -d bet_hope -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Lambda can't reach Postgres** — confirm `LambdaVpcId`/`LambdaSubnetId`
match the VPC your EC2 instance actually launched into (usually your
account's default VPC), and that `DBPassword` matches `DB_PASSWORD` in
`backend/.env.prod` on the EC2 box.

**`sam build` fails compiling pandas/numpy from source** — this means pip
resolved a version with no prebuilt wheel for the Lambda's Python version.
The Makefile in `backend/ml-layer/` pins `--python-version 3.13` for
exactly this reason; don't bump the Lambda runtime without checking
`pip download --platform manylinux2014_x86_64 --python-version <version>
--implementation cp --only-binary=:all: pandas numpy scikit-learn xgboost`
succeeds first (scientific Python packages lag several months behind new
CPython releases for prebuilt Linux wheels).


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

### Phase 4: Production ✅
- [x] Docker Compose configuration
- [x] CI/CD pipeline (GitHub Actions + GHCR)
- [x] AWS EC2 + Lambda + Vercel deployment
- [ ] Real-time updates (WebSocket)
- [ ] Email notifications

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contact

For questions or bug reports, open an issue on GitHub.

