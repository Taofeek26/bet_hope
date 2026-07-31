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


def _get_task_run(task_id):
    """
    Load the TaskRun row for a UI-triggered invocation (see
    apps/api/views/tasks.py). Only imports Django/the ORM when a task_id is
    actually present, so EventBridge-scheduled invocations (no task_id)
    don't pay for django.setup() just to touch the database.
    """
    import django
    django.setup()
    from apps.core.models import TaskRun
    try:
        return TaskRun.objects.get(id=task_id)
    except TaskRun.DoesNotExist:
        return None


def handler(event, context):
    command = event.get("command", "migrate")
    args = event.get("args", [])
    task_id = event.get("task_id")
    timeout = min(context.get_remaining_time_in_millis() / 1000 - 5, 850) if context else 600

    task = _get_task_run(task_id) if task_id else None
    start = datetime.utcnow()
    if task:
        from apps.core.models import TaskRun
        task.status = TaskRun.Status.RUNNING
        task.started_at = start
        task.save(update_fields=["status", "started_at", "updated_at"])

    try:
        result = subprocess.run(
            [sys.executable, "manage.py", command] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
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
    except subprocess.TimeoutExpired as e:
        # Left uncaught, this crashes the whole invocation as an unhandled
        # Lambda error with a raw traceback instead of a clean response —
        # this scope of management command (too many matches/leagues for
        # the per-match feature-extraction queries to finish in time) is a
        # real, recurring case, not an edge case worth ignoring.
        duration = (datetime.utcnow() - start).total_seconds()
        output = {
            "status": "timeout",
            "command": command,
            "exit_code": None,
            "stdout": (e.stdout or "")[-4000:] if isinstance(e.stdout, str) else "",
            "stderr": (e.stderr or "")[-2000:] if isinstance(e.stderr, str) else "",
            "error": f"Command exceeded {timeout:.0f}s — try a smaller scope (fewer --seasons/--leagues)",
            "duration_seconds": round(duration, 1),
        }

    if task:
        from apps.core.models import TaskRun
        task.status = output["status"]
        task.finished_at = datetime.utcnow()
        task.log_tail = (output.get("stdout", "") + "\n" + output.get("stderr", ""))[-8000:]
        task.error = output.get("error", "") if output["status"] != "success" else ""
        task.save(update_fields=["status", "finished_at", "log_tail", "error", "updated_at"])

    print(json.dumps({k: v for k, v in output.items() if k != "stdout"}))
    return output
