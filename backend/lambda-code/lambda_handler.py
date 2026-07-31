"""
Bet_Hope Lambda Handler — zip-based, no Docker.
Routes: train, predict, export tasks via API Gateway events.

This function runs inside the same VPC as the EC2 Postgres instance (see
LambdaVpcId/LambdaSubnetId in infrastructure/template.yaml) so it can reach
the database directly and has no internet access — that's why /tasks/sync
(which needs API-Football/Football-Data.org) lives in the separate
non-VPC ../lambda-sync/handler.py instead, dispatched via SSM to EC2.
"""

import os
import sys
import json
import traceback
import subprocess
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.lambda_settings")

TASKS_API_KEY = os.environ.get("TASKS_API_KEY", "")


def run_command(cmd: str, *args) -> dict:
    """Run a Django management command and return structured output."""
    start = datetime.utcnow()
    try:
        result = subprocess.run(
            [sys.executable, "manage.py", cmd] + list(args),
            capture_output=True,
            text=True,
            timeout=600,
            cwd="/var/task",
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        duration = (datetime.utcnow() - start).total_seconds()
        return {
            "status": "success" if result.returncode == 0 else "error",
            "command": cmd,
            "exit_code": result.returncode,
            "stdout": result.stdout[-3000:],
            "stderr": result.stderr[-1000:],
            "duration_seconds": round(duration, 1),
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": cmd, "error": "Timed out after 10min"}
    except Exception as e:
        return {"status": "error", "command": cmd, "error": str(e), "traceback": traceback.format_exc()[-1000:]}


ROUTES = {
    "/tasks/train": ("train_model", []),
    "/tasks/predict": ("generate_predictions", []),
    "/tasks/export": ("export_training_data", ["--output", "/tmp/training_data.json"]),
}


def handler(event, context):
    """Lambda entry point — dispatched by API Gateway HTTP API."""
    path = event.get("rawPath", event.get("path", "/"))
    # Strip stage prefix (e.g., /prod/health -> /health)
    if path.startswith("/prod/"):
        path = path[5:]  # Remove "/prod" prefix
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))

    print(f"[Lambda] {method} {path}")

    if path == "/health" and method == "GET":
        return {"statusCode": 200, "body": json.dumps({"status": "healthy", "service": "bet-hope-lambda"})}

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if not TASKS_API_KEY or headers.get("x-api-key") != TASKS_API_KEY:
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    if path not in ROUTES:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"unknown route: {path}", "valid": list(ROUTES.keys())}),
        }

    cmd, default_args = ROUTES[path]
    args = list(default_args)

    # Parse query params or body for extra args
    body = {}
    if event.get("body"):
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            pass

    # Also check query string params
    qs = event.get("queryStringParameters") or {}
    body.update(qs or {})

    if body.get("leagues"):
        args.extend(["--leagues"] + (body["leagues"] if isinstance(body["leagues"], list) else [body["leagues"]]))
    if body.get("seasons"):
        args.extend(["--seasons"] + (body["seasons"] if isinstance(body["seasons"], list) else [body["seasons"]]))
    if body.get("clear"):
        args.append("--clear")
    if body.get("fixtures"):
        args.append("--fixtures")

    result = run_command(cmd, *args)
    print(f"[Lambda] {cmd}: {result['status']} ({result.get('duration_seconds', '?')}s)")

    return {"statusCode": 200, "body": json.dumps(result, default=str)}