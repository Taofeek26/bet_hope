"""
Lambda entry point for running one-off/scheduled Django management
commands against RDS (migrate, sync_real_data, train_model,
generate_predictions, export_training_data, sync_injuries,
generate_news_signals, etc) — invoked directly (aws lambda invoke) or via
EventBridge Scheduled Rules, not through API Gateway.

Uses the same container image as lambda_web_handler.py, selected via a
different Lambda function's ImageConfig.Command override (see
infrastructure/template.yaml) rather than a separate build.
"""
import os
import sys
import subprocess
import json
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ENV", "production")


def handler(event, context):
    command = event.get("command", "migrate")
    args = event.get("args", [])

    start = datetime.utcnow()
    result = subprocess.run(
        [sys.executable, "manage.py", command] + list(args),
        capture_output=True,
        text=True,
        timeout=min(context.get_remaining_time_in_millis() / 1000 - 5, 850) if context else 600,
        cwd="/var/task",
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    duration = (datetime.utcnow() - start).total_seconds()

    output = {
        "status": "success" if result.returncode == 0 else "error",
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-2000:],
        "duration_seconds": round(duration, 1),
    }
    print(json.dumps({k: v for k, v in output.items() if k != "stdout"}))
    return output
