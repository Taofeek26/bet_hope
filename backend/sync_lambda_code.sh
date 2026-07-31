#!/bin/bash
# Sync the Django app into backend/lambda-code/ before `sam build`.
#
# backend/lambda-code/apps/ and backend/lambda-code/config/ are a GENERATED
# mirror of backend/apps/ and backend/config/ (the source of truth used by
# the EC2/Docker deployment) — trimmed to just what the Lambda zip needs.
# Never hand-edit files under backend/lambda-code/{apps,config}/ directly;
# edit backend/apps/ or backend/config/ and re-run this script, or Lambda
# and EC2 behavior will silently drift apart.
set -euo pipefail
cd "$(dirname "$0")"

rsync -a --delete \
  --exclude='__pycache__' --exclude='*.pyc' \
  apps/ lambda-code/apps/

rsync -a --delete \
  --exclude='__pycache__' --exclude='*.pyc' \
  config/ lambda-code/config/

echo "Synced backend/apps/ and backend/config/ -> backend/lambda-code/"
