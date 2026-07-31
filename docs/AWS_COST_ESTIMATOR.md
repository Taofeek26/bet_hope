# Bet_Hope — AWS Cost Estimator

> **Date:** July 10, 2026

---

## Scenario Comparison

| | Minimal (~$22/mo) | Standard (~$55/mo) | HA (~$98/mo) |
|---|---|---|---|
| **Compute** | 1× EC2 t4g.small | 2× Fargate tasks | 4× Fargate tasks |
| **DB** | EC2-hosted Docker | RDS t4g.micro | RDS t4g.micro Multi-AZ |
| **Redis** | EC2-hosted Docker | ElastiCache t4g.micro | ElastiCache Multi-AZ |
| **LB** | None (EC2 public) | ALB | ALB |
| **Uptime** | ~99% (single VM) | 99.5% | 99.95% |
| **Auto-recovery** | ❌ | ✅ | ✅ |

---

## Minimal Cost — $22.30/mo (Recommended for now)

Everything on 1 EC2 instance, same as Oracle but on AWS.

| AWS Service | Spec | Monthly |
|---|---|---|
| EC2 t4g.small (ARM) | 2 vCPU, 2GB RAM | $12.26 |
| EBS gp3 | 30GB | $2.40 |
| Elastic IP (if attached to running instance) | 1 | $0.00 |
| S3 — static/media/backups | 5GB | $0.12 |
| Route 53 hosted zone | 1 zone | $0.50 |
| Data transfer out | 10GB | $0.90 |
| **TOTAL** | | **~$22.30** |

**What this runs on 1 VM:**
- PostgreSQL + pgvector (Docker container)
- Redis 7 (Docker container)
- Django + Gunicorn (Docker container)
- Celery worker + beat (Docker containers)
- Next.js frontend (Docker container)
- Nginx reverse proxy (Docker container)

**Same setup as Oracle** — just `docker compose up` on EC2. Zero architecture changes.

### Free Tier note (first 12 months)
If AWS account is new:
| | Free Tier |
|---|---|
| EC2 t4g.small | **750 hrs/mo = FREE** |
| EBS 30GB gp3 | **FREE** |
| 1GB data out | **FREE** |
| **TOTAL** | **~$1.52/mo** (just S3 + Route 53) |

---

## Standard — $55.50/mo

Managed DB + Redis, EC2 for compute.

| AWS Service | Spec | Monthly |
|---|---|---|
| EC2 t4g.small | 2 vCPU, 2GB | $12.26 |
| EBS gp3 | 30GB | $2.40 |
| RDS PostgreSQL | db.t4g.micro, 20GB, Single-AZ | $17.52 |
| ElastiCache Redis | cache.t4g.micro | $13.14 |
| ALB | 1 ALB | $18.98 |
| S3 | 5GB | $0.12 |
| Route 53 | 1 zone | $0.50 |
| Data transfer | 10GB | $0.90 |
| **TOTAL** | | **~$55.50** |

**Benefits over Minimal:**
- RDS: automated backups, snapshots, point-in-time recovery
- ElastiCache: no Redis on EC2, better memory management
- ALB: SSL termination, health checks, path routing

---

## Full ECS Fargate — $98.50/mo

The "proper" setup from the migration plan.

| AWS Service | Spec | Monthly |
|---|---|---|
| ECS Fargate — backend (2 tasks) | 0.5 vCPU, 1GB | $16.06 |
| ECS Fargate — celery (2 tasks) | 0.5 vCPU, 1GB | $16.06 |
| ECS Fargate — celery-beat (1 task) | 0.25 vCPU, 0.5GB | $4.02 |
| ECS Fargate — frontend (2 tasks) | 0.25 vCPU, 0.5GB | $8.03 |
| RDS PostgreSQL | db.t4g.micro, 20GB | $17.52 |
| ElastiCache Redis | cache.t4g.micro | $13.14 |
| ALB | 1 ALB | $18.98 |
| S3 | 5GB | $0.12 |
| ECR | 2GB | $0.20 |
| CloudWatch Logs | 5GB/mo | $2.50 |
| Route 53 | 1 zone | $0.50 |
| Data transfer | 10GB | $0.90 |
| **TOTAL** | | **~$98.50** |

---

## Cost-cutting levers

| Lever | Saves | Trade-off |
|---|---|---|
| Single EC2 (no RDS/ElastiCache) | ~$30/mo | No managed backups, manual DB ops |
| No ALB (EC2 public IP) | ~$19/mo | No SSL termination, manual certs |
| Fargate Spot (celery only) | ~$5/mo | Tasks can be interrupted |
| Single-AZ RDS | ~$18/mo | No failover if AZ dies |
| ElastiCache Serverless | ~$5/mo | Only if traffic is very low |
| Combine celery+beat in 1 task | ~$4/mo | Beat redundancy risk |
| Free tier (new account) | ~$12/mo | First 12 months only |

---

## Recommendation

**Start with Minimal ($22/mo)** — 1 EC2 running Docker Compose, identical to Oracle. 

Then migrate to Standard ($55/mo) when:
- RDS automated backups become important
- Redis memory issues from Oracle resurface
- Need SSL without Let's Encrypt renewal headaches

Only go Full ECS ($98/mo) when:
- You need auto-scaling (traffic growing)
- You need zero-downtime deploys
- The team grows and you want infrastructure-as-code with Terraform