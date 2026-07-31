# Bet_Hope — AWS Minimal Deployment Guide (~$22/mo)

> **Philosophy:** Same setup as Oracle, just on AWS. No managed services, no VPC complexity, no monthly-fee traps.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│          EC2 t4g.small (public IP)            │
│          Ubuntu 24.04, 30GB EBS              │
│                                              │
│   ┌──────────────────────────────────────┐   │
│   │         Docker Compose                │   │
│   │                                      │   │
│   │  nginx :80  →  frontend :3000        │   │
│   │             →  backend  :8000        │   │
│   │                                      │   │
│   │  backend (Django + Gunicorn)         │   │
│   │  celery (worker)                     │   │
│   │  celery-beat (scheduler)             │   │
│   │  frontend (Next.js)                  │   │
│   │  postgres (pgvector)                 │   │
│   │  redis                               │   │
│   └──────────────────────────────────────┘   │
│                                              │
│   Static/media: S3 bucket (optional)         │
└──────────────────────────────────────────────┘
```

**No ALB** (public IP direct), **No RDS** (Docker PostgreSQL), **No ElastiCache** (Docker Redis), **No NAT Gateway**, **No VPC endpoints**. Just default VPC (free).

---

## Step-by-Step

### 1. Launch EC2 Instance

```
AWS Console → EC2 → Launch Instance

Name:         bet-hope
AMI:          Ubuntu 24.04 LTS (ARM)
Architecture: 64-bit (Arm)  ← t4g is ARM
Instance:     t4g.small (2 vCPU, 2GB RAM)
Key pair:     Create new → bet-hope-key.pem (download it)
Network:      Default VPC (auto-created, FREE)
              ☑ Auto-assign public IP
Storage:      30 GB gp3
Firewall:     Allow: SSH (22), HTTP (80), HTTPS (443)
              Source: 0.0.0.0/0 for HTTP/HTTPS (public app)
Launch!
```

```
# Instance will get a public IP like: 3.85.x.x
# This is what users hit — no load balancer needed
```

### 2. SSH In & Install Docker

```bash
chmod 400 bet-hope-key.pem
ssh -i bet-hope-key.pem ubuntu@<PUBLIC_IP>

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-v2 -y
```

### 3. Set Up the Project

```bash
mkdir -p /opt/bet_hope
cd /opt/bet_hope

# Clone your repo
git clone https://github.com/taofeek26/bet-hope.git .

# Copy env file (set these up)
cp .env.example .env
nano .env  # ← configure all vars (see below)
```

### 4. Environment Variables (`.env`)

```
# Same as your Oracle .env, but with AWS values

DJANGO_SECRET_KEY=<generate new: openssl rand -hex 32>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<PUBLIC_IP>,yourdomain.com

# DB stays local (Docker container) — same as Oracle
DATABASE_URL=postgres://bet_hope:<password>@db:5432/bet_hope
POSTGRES_DB=bet_hope
POSTGRES_USER=bet_hope
POSTGRES_PASSWORD=<password>

# Redis stays local (Docker container)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# API keys (same as Oracle)
OPENAI_API_KEY=sk-...
API_FOOTBALL_KEY=...
FOOTBALL_DATA_ORG_KEY=...

# Frontend
NEXT_PUBLIC_API_URL=http://<PUBLIC_IP>/api/v1
```

### 5. Start Everything

```bash
cd /opt/bet_hope
docker compose -f docker-compose.prod.yml up -d

# Check
docker compose ps
docker compose logs backend | tail -50

# Run migrations
docker compose exec backend python manage.py migrate

# Collect static
docker compose exec backend python manage.py collectstatic --noinput
```

### 6. Open Firewall (if needed)

By default the EC2 security group from step 1 allows port 80. Verify:

```bash
# Test from your machine
curl http://<PUBLIC_IP>/
curl http://<PUBLIC_IP>/api/v1/health/
```

### 7. (Optional) DNS

```
Route 53 → Create A record → bet-hope.yourdomain.com → <PUBLIC_IP>
```

Then update:
```
# .env
DJANGO_ALLOWED_HOSTS=bet-hope.yourdomain.com,<PUBLIC_IP>
NEXT_PUBLIC_API_URL=https://bet-hope.yourdomain.com/api/v1

# Restart
docker compose -f docker-compose.prod.yml up -d
```

### 8. (Optional) SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot -y

# Get cert (nginx method)
sudo certbot --nginx -d bet-hope.yourdomain.com

# Auto-renewal is enabled by default
# Verify: sudo certbot renew --dry-run
```

---

## CI/CD Update (GitHub Actions)

Replace the Oracle SSH deploy in `.github/workflows/deploy.yml`:

```yaml
# Change the SSH host from Oracle to AWS
- name: Deploy to AWS
  uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.AWS_EC2_HOST }}      # <PUBLIC_IP>
    username: ubuntu
    key: ${{ secrets.AWS_EC2_SSH_KEY }}     # contents of bet-hope-key.pem
    script: |
      cd /opt/bet_hope
      git pull origin main
      docker compose -f docker-compose.prod.yml pull
      docker compose -f docker-compose.prod.yml up -d --force-recreate
      docker compose exec -T backend python manage.py migrate --noinput
      docker compose exec -T backend python manage.py collectstatic --noinput
      docker system prune -f
```

**GitHub Secrets to add:**
- `AWS_EC2_HOST` → your instance public IP
- `AWS_EC2_SSH_KEY` → `cat bet-hope-key.pem`

---

## Cost Breakdown

| Resource | Monthly |
|---|---|
| EC2 t4g.small | $12.26 |
| EBS 30GB gp3 | $2.40 |
| Elastic IP | $0.00 (attached to running instance) |
| S3 5GB | $0.12 |
| Route 53 | $0.50 |
| Data out (~10GB) | ~$0.90 |
| **TOTAL** | **~$22.30** |

### Free Tier (new AWS account, first 12 months):

| Resource | Monthly |
|---|---|
| EC2 t4g.small | FREE (750 hrs) |
| EBS 30GB | FREE |
| Data out 1GB | FREE |
| S3 5GB | ~$0.12 |
| Route 53 | $0.50 |
| **TOTAL** | **~$1.52** |

---

## Why NOT ECS Fargate (for now)

| | EC2 Docker (~$22) | ECS Fargate (~$98) |
|---|---|---|
| Cost | $22/mo | $98/mo (4.5× more) |
| Same as Oracle? | ✅ Identical | ❌ Complete rewrite |
| Migration effort | 1 hour | 8-10 days |
| Managed DB | ❌ (Docker) | ✅ (RDS) |
| Auto-recovery | ❌ (manual) | ✅ (built-in) |
| Auto-scaling | ❌ | ✅ |

**For an open/public app with low traffic:** EC2 is the right call. You can always migrate to ECS later.

---

## Quick Reference

```bash
# Deploy
cd /opt/bet_hope && docker compose -f docker-compose.prod.yml up -d

# Logs
docker compose -f docker-compose.prod.yml logs -f backend

# Restart one service
docker compose -f docker-compose.prod.yml restart backend

# DB backup
docker compose exec db pg_dump -U bet_hope bet_hope > ~/backups/bet_hope_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U bet_hope bet_hope < backup.sql

# Health check
curl http://localhost:8000/health/
```