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

## Production Deployment (Oracle Cloud)

### Architecture (Production)

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGINX (Port 80/443)                      │
│                    Reverse Proxy & Load Balancer                 │
└─────────────────────┬───────────────────────┬───────────────────┘
                      │                       │
          ┌───────────▼───────────┐ ┌────────▼────────┐
          │    Next.js Frontend   │ │  Django Backend │
          │       (Port 3000)     │ │   (Port 8000)   │
          └───────────────────────┘ └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
          ┌─────────▼─────────┐   ┌─────────▼─────────┐   ┌─────────▼─────────┐
          │ PostgreSQL+pgvector│   │      Redis        │   │   Celery Workers  │
          │     (Port 5432)    │   │   (Port 6379)     │   │   (Background)    │
          └────────────────────┘   └───────────────────┘   └───────────────────┘
```

### Services (Production)

| Service | Port | Description |
|---------|------|-------------|
| nginx | 80/443 | Reverse proxy, SSL termination |
| frontend | 3000 | Next.js app (SSG/SSR) |
| backend | 8000 | Django API + Gunicorn |
| celery | - | Background workers (2 concurrent) |
| celery-beat | - | Task scheduler |
| db | 5432 | PostgreSQL 15 + pgvector |
| redis | 6379 | Cache & message broker |

### Server Requirements

- **OS**: Ubuntu 22.04 LTS
- **RAM**: 1GB minimum (with 2GB swap)
- **Storage**: 20GB+
- **Ports**: 80, 443, 22 (SSH)

### Initial Server Setup

```bash
# SSH into your server
ssh ubuntu@<your-server-ip>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Create swap (required for 1GB RAM servers)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Logout and login again for docker group to take effect
exit
```

### First-Time Deployment

```bash
# SSH back into server
ssh ubuntu@<your-server-ip>

# Clone repository
git clone <repository-url> /opt/bet_hope
cd /opt/bet_hope

# Create production environment file
cat > backend/.env.prod << 'EOF'
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<generate-a-secure-random-key>
DEBUG=false
DJANGO_ALLOWED_HOSTS=<your-server-ip>,yourdomain.com,localhost,127.0.0.1

DATABASE_URL=postgres://bet_hope:secure_password_change_me@db:5432/bet_hope
DB_PASSWORD=secure_password_change_me
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

ML_MODEL_PATH=/app/ml/artifacts
PYTORCH_ENABLE_MPS_FALLBACK=1

# API Keys (add your keys)
API_FOOTBALL_KEY=your_api_key
OPENAI_API_KEY=your_openai_key
EOF

# Start production containers
docker compose -f docker-compose.prod.yml up -d --build

# Enable pgvector extension (first time only)
docker compose -f docker-compose.prod.yml exec db psql -U bet_hope -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Restart backend to run migrations
docker compose -f docker-compose.prod.yml restart backend celery celery-beat

# Verify all services are running
docker compose -f docker-compose.prod.yml ps

# Test endpoints
curl http://<your-server-ip>/           # Frontend
curl http://<your-server-ip>/api/       # Backend API
curl http://<your-server-ip>/health/    # Health check
```

---

## CI/CD Pipeline (GitHub Actions + GHCR)

The project uses GitHub Actions for automated deployments. Images are built in GitHub Actions and pushed to GitHub Container Registry (GHCR), then pulled on the server.

### How It Works

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Push to main   │────▶│  GitHub Actions  │────▶│  Pull on Server  │
│                  │     │  Build & Push    │     │  & Restart       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │      GHCR        │
                     │  Image Registry  │
                     └──────────────────┘
```

### Benefits

| Aspect | Old (build on server) | New (GHCR) |
|--------|----------------------|------------|
| Deploy time | 15-20 min | 1-2 min |
| Server memory | High (5GB+ for build) | Low (just pull) |
| Consistency | Variable | Identical images |
| Caching | None | Docker layer cache |

### One-Time Setup

#### 1. Create GitHub Personal Access Token (PAT)

1. Go to GitHub → **Settings** → **Developer Settings** → **Personal Access Tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `GHCR_TOKEN_BET_HOPE`
4. Select scopes:
   - `read:packages`
   - `write:packages`
5. Click **Generate token** and copy it

#### 2. Add Repository Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `SSH_HOST` | `145.241.188.142` | Server IP address |
| `SSH_USER` | `ubuntu` | SSH username |
| `SSH_PRIVATE_KEY` | (your private key) | SSH private key for server |
| `SSH_PORT` | `22` | SSH port (optional) |
| `GHCR_TOKEN` | (PAT from step 1) | Token for pulling images |
| `BACKEND_URL` | `https://yourdomain.com` | API URL for frontend |

#### 3. Server Setup (First Time Only)

SSH into your server and configure Docker to pull from GHCR:

```bash
ssh ubuntu@<your-server-ip>

# Login to GHCR (use your GitHub username and PAT)
echo "<your-ghcr-token>" | docker login ghcr.io -u <your-github-username> --password-stdin

# Set environment variables for image names
cat >> /opt/bet_hope/.env << 'EOF'
BACKEND_IMAGE=ghcr.io/taofeek26/bet-hope-backend:latest
FRONTEND_IMAGE=ghcr.io/taofeek26/bet-hope-frontend:latest
EOF
```

### Automated Deployment

After setup, deployments are automatic:

```bash
# Just push to main - GitHub Actions handles the rest
git add .
git commit -m "Your changes"
git push origin main

# GitHub Actions will:
# 1. Build backend image (~5-10 min, cached)
# 2. Build frontend image (~2-3 min, cached)
# 3. Push images to GHCR
# 4. SSH to server
# 5. Pull new images
# 6. Restart containers
# 7. Run migrations
```

### Manual Deployment (Alternative)

If you need to deploy manually or GitHub Actions fails:

```bash
# Option 1: Build locally and transfer (for slow connections)
# Build images locally for linux/amd64
docker buildx build --platform linux/amd64 -t bet_hope-backend:latest ./backend --load
docker buildx build --platform linux/amd64 -t bet_hope-frontend:latest ./frontend --load

# Save to tar
docker save bet_hope-backend:latest -o backend.tar
docker save bet_hope-frontend:latest -o frontend.tar

# Transfer to server (use rsync for large files)
rsync -avz --progress backend.tar ubuntu@<server-ip>:/opt/bet_hope/
scp frontend.tar ubuntu@<server-ip>:/opt/bet_hope/

# On server: load and restart
ssh ubuntu@<server-ip>
cd /opt/bet_hope
docker load -i backend.tar
docker load -i frontend.tar
docker compose -f docker-compose.prod.yml up -d
rm backend.tar frontend.tar

# Option 2: Pull from GHCR manually
ssh ubuntu@<server-ip>
cd /opt/bet_hope
git pull origin main
docker pull ghcr.io/taofeek26/bet-hope-backend:latest
docker pull ghcr.io/taofeek26/bet-hope-frontend:latest
docker compose -f docker-compose.prod.yml up -d
```

### Monitoring Deployments

#### Check GitHub Actions Status
- Go to repository → **Actions** tab
- View workflow runs and logs

#### Check Server Status
```bash
ssh ubuntu@<server-ip>
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail 50
```

### Troubleshooting CI/CD

#### GitHub Actions Fails to Push to GHCR
```
Error: denied: permission_denied
```
- Ensure `GITHUB_TOKEN` has `packages: write` permission
- Check workflow has `permissions: packages: write`

#### Server Can't Pull Images
```
Error: unauthorized: authentication required
```
```bash
# Re-login to GHCR on server
echo "<your-ghcr-token>" | docker login ghcr.io -u <username> --password-stdin
```

#### SSH Connection Fails
- Verify `SSH_PRIVATE_KEY` secret is correct (include full key with headers)
- Check server firewall allows port 22
- Verify `SSH_USER` has access to `/opt/bet_hope`

---

## Manual Deployment (Legacy)

If not using CI/CD, you can still deploy manually:

### Quick Deploy Commands

```bash
# SSH into server
ssh ubuntu@<your-server-ip>
cd /opt/bet_hope

# Pull and rebuild (slow - builds on server)
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build

# Or just restart (if images already exist)
docker compose -f docker-compose.prod.yml up -d
```

### View Production Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f celery
docker compose -f docker-compose.prod.yml logs -f nginx

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail 100 backend
```

---

## Production Operations

### Create Admin User

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### Seed Initial Data

```bash
# Seed leagues
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_leagues

# Backfill historical data
docker compose -f docker-compose.prod.yml exec backend python manage.py backfill_historical --seasons 3
```

### Run Database Migrations

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Access Django Shell

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py shell
```

### Access Database

```bash
docker compose -f docker-compose.prod.yml exec db psql -U bet_hope
```

---

## Troubleshooting Production

### 502 Bad Gateway
Nginx can't reach backend (usually after container recreation):
```bash
docker compose -f docker-compose.prod.yml restart nginx
```

### 400 Bad Request (ALLOWED_HOSTS)
```bash
# Check current setting
docker compose -f docker-compose.prod.yml exec backend env | grep ALLOWED

# Fix: Update backend/.env.prod
DJANGO_ALLOWED_HOSTS=<your-server-ip>,yourdomain.com,localhost

# Restart
docker compose -f docker-compose.prod.yml restart backend celery celery-beat
```

### 301 Redirect Loop (SSL not configured)
```bash
# Ensure these are in backend/.env.prod:
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false

# Restart
docker compose -f docker-compose.prod.yml restart backend
```

### pgvector Extension Missing
```bash
# Error: type "vector" does not exist
docker compose -f docker-compose.prod.yml exec db psql -U bet_hope -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose -f docker-compose.prod.yml restart backend
```

### Out of Memory
```bash
# Check swap
free -h

# Enable swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Container Won't Start
```bash
docker compose -f docker-compose.prod.yml logs <service-name>
```

---

## SSL/HTTPS Setup

### Using Let's Encrypt

```bash
# Install certbot
sudo apt install certbot -y

# Stop nginx temporarily
docker compose -f docker-compose.prod.yml stop nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
sudo chown $USER:$USER nginx/ssl/*.pem

# Update nginx.conf (uncomment SSL server block)
# Update backend/.env.prod:
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_HSTS_SECONDS=31536000

# Restart
docker compose -f docker-compose.prod.yml up -d
```

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
- [x] CI/CD pipeline (GitHub Actions + GHCR)
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

Proprietary - All rights reserved.

---

## Contact

For questions, open an issue or contact the development team.
