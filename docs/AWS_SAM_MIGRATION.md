# Bet_Hope: Oracle → AWS Migration – SAM/CloudFormation

> **Plan:** Minimal ($22/mo), 1× EC2, Docker Compose, no managed services

---

## 1. What Changes vs What Stays

### Nothing changes (zero code modifications)

| Component | Status | Reason |
|---|---|---|
| `docker-compose.prod.yml` | ✅ No change | Same 7 containers |
| `Dockerfile` (backend) | ✅ No change | Multi-stage ARM/x86 build works on Graviton |
| `Dockerfile` (frontend) | ✅ No change | Node.js is arch-agnostic |
| `nginx/nginx.conf` | ✅ No change | Still reverse-proxying on EC2 |
| Django settings | ✅ No change | ENV vars injected same way |
| Celery tasks | ✅ No change | Same Redis broker |
| ML pipeline (`ml_pipeline/`) | ✅ No change | XGBoost inference works identically |
| Model files (`models/`) | ✅ No change | Baked into Docker image, loaded with joblib |
| Requirements.txt | ✅ No change | Same packages |
| GHCR images | ✅ No change | Same `ghcr.io/taofeek26/bet-hope-*` images |

### What changes

| Component | Before (Oracle) | After (AWS) |
|---|---|---|
| Server IP | `145.241.188.142` | EC2 Elastic IP (assigned at deploy) |
| SSH user | `ubuntu` | `ubuntu` (same) |
| GitHub Actions deploy target | Oracle IP | EC2 IP |
| GitHub Actions train-model target | Oracle IP | EC2 IP |
| Let's Encrypt SSL | Manual certbot on Oracle | Same process on EC2 |
| Swap file | 2GB on Oracle | 2GB on EC2 (in UserData) |

---

## 2. ML Pipeline Impact Assessment

### How training works (2 paths)

**Path A — GitHub Actions nightly (`train-model.yml`):**
```
Cron 5AM UTC → SSH to prod → export DB data → download to GH runner
→ train XGBoost on GH runner → commit model.pkl/.json to repo
→ SSH to prod → git pull → activate model in DB → restart backend+celery
```
⚠️ Must update IP from `145.241.188.142` → EC2 IP

**Path B — Celery Beat task (`retrain_model`):**
```
Celery beat 5AM UTC → call_command('train_with_feedback')
→ trains XGBoost on the EC2 instance itself
→ saves to ml/artifacts/
```
✅ No changes needed — runs inside the container

### ML memory considerations

| Operation | RAM needed | Where it runs |
|---|---|---|
| Feature extraction | ~500MB | EC2 (inference) |
| XGBoost inference | ~300MB | EC2 (inference) |
| XGBoost training (100 trees) | ~1.5GB | GitHub Actions runner |
| Optuna hyperparameter tuning (100 trials) | ~2GB | GitHub Actions runner |
| `sentence-transformers` embeddings | ~2GB | EC2 (docs module) |

`t4g.small` has 2GB RAM. With 2GB swap → ~4GB effective. Sufficient for inference + sentence-transformers. **Training stays on GitHub Actions** (7GB runners).

### What to verify after migration

```bash
# 1. Model loading works
docker compose exec backend python manage.py shell -c "
from apps.ml_pipeline.inference.predictor import MatchPredictor
p = MatchPredictor(model_version='latest')
print('Model loaded:', p.metadata['version'])
"

# 2. Prediction generation works
docker compose exec backend python manage.py generate_predictions

# 3. Celery beat schedule is registered
docker compose exec backend celery -A config inspect scheduled

# 4. Training export works
docker compose exec backend python manage.py export_training_data --output /tmp/test.json
```

---

## 3. Deployment Steps

### Step 1: Prerequisites

```bash
# Install SAM CLI
brew install aws-sam-cli   # macOS
# or: pip install aws-sam-cli

# Configure AWS credentials
aws configure
# Enter: Access Key, Secret Key, region (us-east-1), output (json)

# Create EC2 key pair (one-time)
aws ec2 create-key-pair --key-name bet-hope-key --query 'KeyMaterial' --output text > ~/bet-hope-key.pem
chmod 400 ~/bet-hope-key.pem
```

### Step 2: Deploy with SAM

```bash
cd infrastructure/

# Build (SAM validates the template)
sam build

# Deploy (interactive — fill in params)
sam deploy --guided
#   Stack Name: bet-hope
#   AWS Region: us-east-1
#   KeyPairName: bet-hope-key
#   InstanceType: t4g.small
#   VolumeSize: 30
#   GitHubRepo: taofeek26/bet-hope
#   DomainName: [leave blank or enter domain]
#   Confirm changes before deploy: Y
#   Allow SAM CLI IAM role creation: Y
```

### Step 3: SSH in & configure secrets

```bash
# Get the public IP from SAM outputs
IP=$(aws cloudformation describe-stacks --stack-name bet-hope \
  --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' --output text)

ssh -i ~/bet-hope-key.pem ubuntu@$IP

# Fill in real secrets
sudo nano /opt/bet_hope/backend/.env.prod

# Start the app
cd /opt/bet_hope
docker compose -f docker-compose.prod.yml up -d

# Verify
curl http://localhost/health/
```

### Step 4: Set up SSL (Let's Encrypt)

```bash
ssh ubuntu@$IP
sudo snap install certbot --classic
sudo certbot --nginx -d yourdomain.com
# Auto-renews via systemd timer
```

### Step 5: Update GitHub Actions

Update these secrets in your GitHub repo:

| Secret | Old Value | New Value |
|---|---|---|
| `SSH_HOST` | `145.241.188.142` | EC2 Elastic IP |
| `SSH_USER` | `ubuntu` | `ubuntu` (unchanged) |
| `SSH_PRIVATE_KEY` | Oracle key | `cat ~/bet-hope-key.pem` |

Or update the IPs directly in the workflow files (see `infrastructure/deploy-aws.yml`).

### Step 6: Data migration

```bash
# From Oracle server
ssh ubuntu@145.241.188.142
cd /opt/bet_hope
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U bet_hope bet_hope > /tmp/dump.sql
exit

# Copy to local
scp ubuntu@145.241.188.142:/tmp/dump.sql .

# Copy to EC2 & restore
scp dump.sql ubuntu@$IP:/tmp/
ssh ubuntu@$IP "cd /opt/bet_hope && docker compose -f docker-compose.prod.yml exec -T db psql -U bet_hope bet_hope < /tmp/dump.sql"

# Verify
ssh ubuntu@$IP "cd /opt/bet_hope && docker compose exec -T db psql -U bet_hope bet_hope -c 'SELECT count(*) FROM matches_match;'"
```

### Step 7: DNS cutover

```bash
# If using Route 53 (auto-created by template) — just update domain NS
# If using external DNS — create A record pointing to EC2 Elastic IP

# Test
curl http://$IP/health/
curl https://yourdomain.com/health/

# Monitor for 48h before shutting down Oracle
ssh ubuntu@145.241.188.142 "cd /opt/bet_hope && docker compose -f docker-compose.prod.yml down"
```

---

## 4. Files Created

```
infrastructure/
└── template.yaml              ← SAM/CloudFormation for EC2 + S3 + EIP + SG

infrastructure/
└── deploy-aws.yml             ← Updated CI/CD for AWS (replaces Oracle SSH)

docs/
├── AWS_MIGRATION_PLAN.md      ← Full Fargate plan (reference for future)
├── AWS_COST_ESTIMATOR.md      ← Cost comparison (3 scenarios)
├── AWS_MINIMAL_DEPLOYMENT.md  ← Minimal EC2 deployment guide
└── AWS_SAM_MIGRATION.md       ← This file (definitive migration guide)
```

---

## 5. Quick Commands

```bash
# Deploy infra changes
sam build && sam deploy

# View stack outputs
aws cloudformation describe-stacks --stack-name bet-hope \
  --query 'Stacks[0].Outputs' --output table

# View EC2 metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$(aws cloudformation describe-stacks \
    --stack-name bet-hope --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' --output text) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average

# Tear down everything
sam delete --stack-name bet-hope
# ⚠️ This deletes the S3 bucket too — backup first!
aws s3 sync s3://bet-hope-static-<account-id> ./backup/  # before delete
```

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| EC2 can't pull GHCR images | SSH in: `docker login ghcr.io -u taofeek26` |
| Celery beat running duplicates | Ensure `desiredCount: 1` / only one container started |
| `pgvector` not found after restore | SSH in: `docker compose exec db psql -U bet_hope bet_hope -c "CREATE EXTENSION IF NOT EXISTS vector;"` |
| OOM on model load | Increase swap: `fallocate -l 4G /swapfile2 && mkswap /swapfile2 && swapon /swapfile2` |
| XGBoost `n_jobs=-1` uses all cores | Set `n_jobs=1` in config if t4g.small CPU throttles |
| SAM deploy fails on IAM | Add `--capabilities CAPABILITY_IAM` to `sam deploy` |
| Static files 403 | Check S3 bucket policy — public read must be allowed |