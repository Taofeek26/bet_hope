# Bet_Hope — Oracle Cloud → AWS Migration Plan

> **Author:** Generated from full project audit  
> **Date:** July 10, 2026  
> **Current Host:** Oracle Cloud Free Tier (145.241.188.142)  
> **Target Host:** AWS (ECS Fargate)

---

## 1. Current Architecture (Oracle Cloud)

```
┌─────────────────────────────────────────────────────────┐
│                 Oracle Cloud VM (Ubuntu)                 │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  nginx   │  │ backend  │  │ frontend │  │ flower │ │
│  │  :80/443 │  │gunicorn │  │Next.js   │  │ :5555  │ │
│  │          │  │  :8000   │  │  :3000   │  │        │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │
│       │             │             │             │       │
│  ┌────┴─────┐  ┌────┴─────┐  ┌───┴──────┐             │
│  │ postgres │  │  redis   │  │ celery   │             │
│  │ pgvector │  │   :6379  │  │ worker   │             │
│  │  :5432   │  │          │  │+beat     │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                         │
│  Docker Compose (docker-compose.prod.yml)               │
│  GHCR images: ghcr.io/taofeek26/bet-hope-*              │
└─────────────────────────────────────────────────────────┘
```

### What runs where (Oracle):

| Service | Container | Port | Image |
|---------|-----------|------|-------|
| PostgreSQL 16 + pgvector | `db` | 5432 | `pgvector/pgvector:pg15` |
| Redis 7 | `redis` | 6379 | `redis:7-alpine` |
| Django + Gunicorn | `backend` | 8000 | `ghcr.io/taofeek26/bet-hope-backend:latest` |
| Celery Worker | `celery` | — | Same as backend |
| Celery Beat | `celery-beat` | — | Same as backend |
| Next.js | `frontend` | 3000 | `ghcr.io/taofeek26/bet-hope-frontend:latest` |
| Nginx | `nginx` | 80/443 | `nginx:alpine` |
| Flower | `flower` | 5555 | Same as backend |

### What's in the CI/CD:
- **GitHub Actions** triggers on push to `main`
- Builds backend & frontend Docker images → pushes to GHCR
- SSHs into Oracle server (145.241.188.142)
- Pulls new images, stops/restarts containers, runs migrations
- Also has a separate `train-model.yml` workflow that exports data from Oracle, trains on GitHub runners, pushes model back to repo

---

## 2. Target Architecture (AWS)

```
┌─────────────────────────────────────────────────────────────────┐
│                           AWS (us-east-1)                       │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    VPC (10.0.0.0/16)                      │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Public Subnets (2 AZs)                  │  │  │
│  │  │                                                     │  │  │
│  │  │   ┌──────────┐                                      │  │  │
│  │  │   │   ALB    │  (bet-hope-alb)                      │  │  │
│  │  │   │ :80/443  │  HTTPS via ACM cert                  │  │  │
│  │  │   └────┬─────┘                                      │  │  │
│  │  │        │                                             │  │  │
│  │  └────────┼────────────────────────────────────────────┘  │  │
│  │           │                                                │  │
│  │  ┌────────┼────────────────────────────────────────────┐  │  │
│  │  │        │       Private Subnets (2 AZs)               │  │  │
│  │  │        │                                             │  │  │
│  │  │   ┌────┴──────────────────────────────────────┐     │  │  │
│  │  │   │              ECS Fargate Cluster           │     │  │  │
│  │  │   │                                           │     │  │  │
│  │  │   │  ┌──────────────┐  ┌──────────────────┐  │     │  │  │
│  │  │   │  │ backend-svc  │  │ frontend-svc     │  │     │  │  │
│  │  │   │  │ (gunicorn)   │  │ (Next.js)        │  │     │  │  │
│  │  │   │  │ 2 tasks      │  │ 2 tasks          │  │     │  │  │
│  │  │   │  └──────────────┘  └──────────────────┘  │     │  │  │
│  │  │   │                                           │     │  │  │
│  │  │   │  ┌──────────────┐  ┌──────────────────┐  │     │  │  │
│  │  │   │  │ celery-svc   │  │ celery-beat-svc  │  │     │  │  │
│  │  │   │  │ (worker)     │  │ (scheduler)      │  │     │  │  │
│  │  │   │  │ 2 tasks      │  │ 1 task           │  │     │  │  │
│  │  │   │  └──────────────┘  └──────────────────┘  │     │  │  │
│  │  │   └──────────────────────────────────────────┘     │  │  │
│  │  │                                                     │  │  │
│  │  │   ┌──────────────┐  ┌──────────────────────┐       │  │  │
│  │  │   │ RDS          │  │ ElastiCache Redis    │       │  │  │
│  │  │   │ PostgreSQL   │  │ (serverless or       │       │  │  │
│  │  │   │ 16 + pgvector│  │  cache.t4g.micro)    │       │  │  │
│  │  │   └──────────────┘  └──────────────────────┘       │  │  │
│  │  │                                                     │  │  │
│  │  │   ┌──────────────┐                                 │  │  │
│  │  │   │  S3 Bucket   │  (static + media + backups)     │  │  │
│  │  │   └──────────────┘                                 │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                ECR (Container Registry)                    │  │
│  │  bet-hope-backend  │  bet-hope-frontend                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Why ECS Fargate (not EC2):

| Factor | EC2 (Docker Compose) | ECS Fargate |
|--------|---------------------|-------------|
| Server management | You patch/secure/scale | AWS handles it |
| Auto-recovery | Manual (or systemd) | Built-in — dead tasks auto-replaced |
| Scaling | Manual resize | Auto-scale on CPU/memory |
| Logging | Docker log files | Native CloudWatch |
| Secrets | .env on disk | AWS Secrets Manager |
| Cost (small) | ~$20/mo (t3.small) | ~$35/mo (0.5 vCPU × 4 tasks) |
| DB/Redis | Containers | RDS + ElastiCache (HA, backups) |

### Why RDS + ElastiCache (not Docker containers):

- RDS: automated backups, point-in-time recovery, pgvector support via extension
- ElastiCache: fully managed Redis, automatic failover, no swap headaches
- The Oracle server uses 2GB swap to survive — RDS handles memory properly

---

## 3. Service-by-Service Migration Map

| Oracle (Docker) | AWS Service | Notes |
|-----------------|-------------|-------|
| `db` (pgvector/pgvector:pg15) | **RDS PostgreSQL 16.3** | Enable `pgvector` extension post-creation |
| `redis` (redis:7-alpine) | **ElastiCache Redis 7** | Serverless or `cache.t4g.micro` node |
| `backend` (Django + gunicorn) | **ECS Fargate Service** | Same Dockerfile, different entrypoints |
| `celery` (worker) | **ECS Fargate Service** | Same image, `celery worker` command |
| `celery-beat` (scheduler) | **ECS Fargate Service** | Same image, `celery beat` command |
| `frontend` (Next.js) | **ECS Fargate Service** | Same Dockerfile |
| `nginx` (reverse proxy) | **ALB** (Application Load Balancer) | ALB handles routing + SSL termination |
| `flower` (Celery monitor) | **ECS Fargate Service** (optional) | Internal-only, not exposed publicly |
| Static files (`/static/`, `/media/`) | **S3 + CloudFront** (or EFS) | Migrate from Whitenoise to django-storages |
| ML model files (`models/`) | **S3** or **EFS** | Mounted to backend + celery tasks |
| GitHub Container Registry | **ECR** (Elastic Container Registry) | Private, same region as ECS |
| SSL (Let's Encrypt) | **ACM** (AWS Certificate Manager) | Auto-renewing, free |

---

## 4. Migration Steps (Ordered)

### Phase 0: Prerequisites (you do this once)

```
AWS Account setup:
  ☐ Ensure you have an AWS account with admin access
  ☐ Install & configure AWS CLI: aws configure
  ☐ Install Terraform or AWS CDK (recommended: Terraform)
  ☐ Register a domain in Route 53 (or use existing domain)
```

### Phase 1: Infrastructure (Terraform/CDK)

```
☐ 1. Create VPC with 2 public + 2 private subnets (across 2 AZs)
☐ 2. Create RDS PostgreSQL 16.3 instance (db.t4g.micro or db.t4g.small)
     - Enable pgvector extension: CREATE EXTENSION vector;
     - Set master username/password in Secrets Manager
     - Configure security group: allow ECS tasks on port 5432
☐ 3. Create ElastiCache Redis 7 cluster
     - cache.t4g.micro single node (or serverless)
     - Security group: allow ECS tasks on port 6379
☐ 4. Create ECR repositories:
     - bet-hope-backend
     - bet-hope-frontend
☐ 5. Create S3 bucket for static/media/backups
     - Enable versioning
     - Lifecycle policy for old versions
☐ 6. Create ECS Cluster (Fargate, no EC2)
☐ 7. Create Task Definitions (4 types — see below)
☐ 8. Create ALB with target groups + HTTPS listener
     - Request ACM certificate for your domain
     - Route / → frontend target group
     - Route /api/*, /admin/*, /health/* → backend target group
     - Route /static/* → S3 (or backend with EFS)
☐ 9. Create CloudWatch Log Groups for each service
☐ 10. Set up Route 53 A record → ALB
```

### Phase 2: ECS Task Definitions

All 4 task types use the **same ECR image** (`bet-hope-backend:latest`) with different commands:

#### Task 1: Backend (Django + Gunicorn)
```json
{
  "family": "bet-hope-backend",
  "cpu": "512",
  "memory": "1024",
  "command": ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"],
  "portMappings": [{"containerPort": 8000}],
  "environment": [
    {"name": "DJANGO_SETTINGS_MODULE", "value": "config.settings.production"},
    {"name": "DJANGO_ENV", "value": "production"}
  ],
  "secrets": [
    {"name": "DJANGO_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "REDIS_URL", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "CELERY_BROKER_URL", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "API_FOOTBALL_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "FOOTBALL_DATA_ORG_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
  ]
}
```

#### Task 2: Celery Worker
```json
{
  "family": "bet-hope-celery",
  "cpu": "512",
  "memory": "1024",
  "command": ["celery", "-A", "config", "worker", "-l", "info", "-Q", "default,data_sync,ml,predictions,analytics", "--concurrency=2"],
  "environment": [/* same env vars, minus port mappings */]
}
```

#### Task 3: Celery Beat
```json
{
  "family": "bet-hope-celery-beat",
  "cpu": "256",
  "memory": "512",
  "command": ["celery", "-A", "config", "beat", "-l", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler"],
  "environment": [/* same env vars */],
  "desiredCount": 1  // MUST be exactly 1
}
```

#### Task 4: Frontend (Next.js)
```json
{
  "family": "bet-hope-frontend",
  "cpu": "256",
  "memory": "512",
  "command": ["node", "server.js"],
  "portMappings": [{"containerPort": 3000}],
  "environment": [
    {"name": "NEXT_PUBLIC_API_URL", "value": "https://api.yourdomain.com/api/v1"}
  ]
}
```

### Phase 3: Container Image Changes

#### Backend Dockerfile — no changes needed
The existing multi-stage Dockerfile works on ECS. Minor additions:

```dockerfile
# Add after existing HEALTHCHECK:
# Use Django's check framework for better health checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python manage.py check --deploy || exit 1
```

#### Frontend Dockerfile — needs `NEXT_PUBLIC_API_URL` injected
```dockerfile
# The Dockerfile already accepts ARG NEXT_PUBLIC_API_URL ✓
# ECS will pass this as an environment variable
```

#### Static & Media files — switch from Whitenoise to S3

Add to `requirements.txt`:
```
django-storages[s3]>=1.14.0
boto3>=1.34.0
```

Add to `backend/config/settings/production.py`:
```python
# S3 Static/Media Storage
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_DEFAULT_ACL = None
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

### Phase 4: Secrets & Environment Variables

Create these in **AWS Secrets Manager** (one secret per env-var, or one JSON blob):

```json
{
  "DJANGO_SECRET_KEY": "<generate-50-char-random>",
  "DJANGO_DEBUG": "False",
  "DJANGO_ALLOWED_HOSTS": "yourdomain.com,api.yourdomain.com,localhost",
  "DATABASE_URL": "postgres://bet_hope:<password>@<rds-endpoint>:5432/bet_hope",
  "REDIS_URL": "redis://<elasticache-endpoint>:6379/0",
  "CELERY_BROKER_URL": "redis://<elasticache-endpoint>:6379/0",
  "CELERY_RESULT_BACKEND": "django-db",
  "OPENAI_API_KEY": "sk-...",
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "API_FOOTBALL_KEY": "...",
  "FOOTBALL_DATA_ORG_KEY": "...",
  "AWS_STORAGE_BUCKET_NAME": "bet-hope-static",
  "AWS_S3_REGION_NAME": "us-east-1",
  "CORS_ALLOWED_ORIGINS": "https://yourdomain.com",
  "SECURE_SSL_REDIRECT": "true",
  "SESSION_COOKIE_SECURE": "true",
  "CSRF_COOKIE_SECURE": "true",
  "SENTRY_DSN": "https://..."
}
```

### Phase 5: CI/CD Update (GitHub Actions)

Replace the Oracle SSH deploy with ECS deploy:

```yaml
# .github/workflows/deploy-aws.yml
name: Build and Deploy to AWS

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_BACKEND: bet-hope-backend
  ECR_FRONTEND: bet-hope-frontend

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # OIDC for AWS

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::<account-id>:role/github-actions-deploy
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build & push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: |
            ${{ steps.login.outputs.registry }}/${{ env.ECR_BACKEND }}:latest
            ${{ steps.login.outputs.registry }}/${{ env.ECR_BACKEND }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build & push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: |
            ${{ steps.login.outputs.registry }}/${{ env.ECR_FRONTEND }}:latest
            ${{ steps.login.outputs.registry }}/${{ env.ECR_FRONTEND }}:${{ github.sha }}
          build-args: |
            NEXT_PUBLIC_API_URL=${{ vars.API_URL }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster bet-hope --service backend --force-new-deployment
          aws ecs update-service --cluster bet-hope --service celery --force-new-deployment
          aws ecs update-service --cluster bet-hope --service celery-beat --force-new-deployment
          aws ecs update-service --cluster bet-hope --service frontend --force-new-deployment
          
          # Wait for deployments to stabilize
          aws ecs wait services-stable --cluster bet-hope --services backend frontend

      - name: Run migrations
        run: |
          aws ecs run-task --cluster bet-hope --task-definition bet-hope-migrate \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[${{ secrets.PRIVATE_SUBNETS }}],securityGroups=[${{ secrets.SECURITY_GROUP }}],assignPublicIp=DISABLED}"
```

### Phase 6: Data Migration (Oracle → AWS RDS)

```bash
# 1. SSH into Oracle server and dump database
ssh ubuntu@145.241.188.142
cd /opt/bet_hope
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U bet_hope bet_hope > /tmp/bet_hope_dump.sql

# 2. Copy dump to your local machine
scp ubuntu@145.241.188.142:/tmp/bet_hope_dump.sql .

# 3. Restore to AWS RDS (after RDS is up + pgvector extension enabled)
psql -h <rds-endpoint> -U bet_hope -d bet_hope -f bet_hope_dump.sql

# 4. Verify
psql -h <rds-endpoint> -U bet_hope -d bet_hope -c "SELECT count(*) FROM matches_match;"
psql -h <rds-endpoint> -U bet_hope -d bet_hope -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

### Phase 7: ML Model Files

Current location: `backend/models/` (committed to git, deployed with image)

Options:
1. **Keep in Docker image** (simplest — already works, models are baked in)
2. **Move to S3 + download on startup** (better for large models, decouples model from image)

If choosing S3:
```python
# Add to backend entrypoint script
import boto3
s3 = boto3.client('s3')
s3.download_file('bet-hope-models', 'latest/model.pkl', '/app/ml/artifacts/model.pkl')
```

### Phase 8: DNS Cutover

```
1. Deploy everything to AWS (backend + frontend + celery + DB + Redis)
2. Test via ALB DNS name: https://bet-hope-alb-xxx.us-east-1.elb.amazonaws.com
3. Verify:
   - Frontend loads, API calls work
   - Predictions generate correctly (check Celery flower)
   - Admin panel works
   - Celery Beat schedule runs
4. Update Route 53 A record to point to ALB
5. Wait for DNS propagation (~5 min)
6. Monitor CloudWatch logs for errors
7. Keep Oracle server running for 48h as rollback option
8. After 48h stable: terminate Oracle VM
```

---

## 5. Cost Estimate (Monthly)

| Service | Spec | Est. Monthly |
|---------|------|--------------|
| ECS Fargate — Backend (2 tasks) | 0.5 vCPU, 1GB | ~$16 |
| ECS Fargate — Celery (2 tasks) | 0.5 vCPU, 1GB | ~$16 |
| ECS Fargate — Celery Beat (1 task) | 0.25 vCPU, 0.5GB | ~$4 |
| ECS Fargate — Frontend (2 tasks) | 0.25 vCPU, 0.5GB | ~$8 |
| RDS PostgreSQL | db.t4g.micro, 20GB | ~$18 |
| ElastiCache Redis | cache.t4g.micro | ~$13 |
| ALB | 1 ALB | ~$18 |
| S3 (static + backups) | ~5GB | ~$1 |
| ECR | ~2GB | ~$1 |
| CloudWatch Logs | ~5GB/mo | ~$3 |
| Route 53 | 1 hosted zone | ~$0.50 |
| **TOTAL** | | **~$98/mo** |

### Cost-cutting options:
- Use **ElastiCache Serverless** (pay-per-request, cheaper for low traffic)
- Use **RDS t4g.micro with burst credits** (free-tier eligible first year if new account)
- **Single AZ** deployment instead of multi-AZ (not recommended for prod but saves 50%)
- Combine celery + celery-beat into one service (reduce to ~$80/mo)
- **Spot Fargate** for celery workers (30-50% cheaper, risk of interruption acceptable)

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Celery beat running duplicate tasks | Medium | High | `desiredCount: 1` with ECS service + no auto-scaling |
| ECS task failing to pull ECR image | Low | Medium | VPC endpoints for ECR + S3 (no NAT Gateway needed) |
| Database migration corruption | Low | High | Take RDS snapshot before migration; test on staging first |
| pgvector extension not enabled | Low | High | Enable in RDS parameter group + verify post-restore |
| Cold start latency (Fargate) | Low | Low | Keep min 1 task running; health check grace period 60s |
| OpenAI API key exposed in logs | Low | High | Use Secrets Manager, never log env vars, Sentry PII scrubbing |
| S3 static files 403 after migration | Medium | Medium | Set bucket policy + CloudFront OAC; test collectstatic |

---

## 7. Quick Reference: Key Commands After Migration

```bash
# Deploy updated code
git push origin main  # CI/CD handles ECR build + ECS deploy

# Run management commands (one-off Fargate task)
aws ecs run-task --cluster bet-hope \
  --task-definition bet-hope-backend \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={...}" \
  --overrides '{"containerOverrides":[{"name":"backend","command":["python","manage.py","migrate"]}]}'

# View logs
aws logs tail /ecs/bet-hope-backend --follow

# Database backup (RDS snapshot)
aws rds create-db-snapshot --db-instance-identifier bet-hope-db --db-snapshot-identifier bet-hope-$(date +%Y%m%d)

# Check service status
aws ecs describe-services --cluster bet-hope --services backend celery celery-beat frontend \
  --query 'services[*].[serviceName,desiredCount,runningCount,status]'
```

---

## 8. Files to Create/Modify

### New files needed:
- `infrastructure/` — Terraform or CDK code for all AWS resources
- `.github/workflows/deploy-aws.yml` — new CI/CD pipeline
- `backend/config/settings/aws.py` — optional: AWS-specific overrides

### Files to modify:
| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `boto3`, `django-storages[s3]` |
| `backend/config/settings/production.py` | Add S3 storage backend |
| `backend/Dockerfile` | Add migration entrypoint script (optional) |
| `frontend/Dockerfile` | No change needed |
| `frontend/.env.example` | Update `NEXT_PUBLIC_API_URL` to production domain |
| `nginx/nginx.conf` | ⚠️ **No longer needed** — ALB replaces nginx |

### Files to archive/remove:
- `scripts/oracle-cloud-setup.sh` — Oracle-specific
- `nginx/nginx.conf` — Replaced by ALB
- `docker-compose.prod.yml` — Replaced by ECS task definitions (keep for reference)
- `deploy.sh` — Oracle deploy script (keep for reference)

---

## 9. Timeline

| Phase | Duration | Effort |
|-------|----------|--------|
| Phase 0: Prerequisites | 1 day | You |
| Phase 1: Infrastructure (Terraform) | 2-3 days | You + Terraform |
| Phase 2: Task definitions | 1 day | You |
| Phase 3: Image tweaks | 0.5 day | You |
| Phase 4: Secrets setup | 0.5 day | You |
| Phase 5: CI/CD | 1 day | You |
| Phase 6: Data migration | 1 day | You |
| Phase 7: ML model handling | 0.5 day | You |
| Phase 8: DNS cutover | 1 day | You |
| **TOTAL** | **~8-10 days** | |

---

## 10. Questions to Decide Before Starting

1. **Domain:** Do you have a domain for Bet_Hope? Route 53 or external?
2. **SSL:** Want to use AWS ACM (free, auto-renew) or bring your own?
3. **Budget:** OK with ~$100/mo? Or need cost optimization (single-AZ, spot)?
4. **Staging environment:** Want a staging ECS cluster for testing before prod cutover?
5. **ML model storage:** Keep models in Docker image or move to S3?
6. **Multi-AZ:** Need high availability (multi-AZ RDS) or OK with single-AZ?
7. **Terraform vs CDK:** Preference for infra-as-code tool?