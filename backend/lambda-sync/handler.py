"""
Bet_Hope Sync Dispatcher.

Handles POST /tasks/sync only. Deliberately NOT deployed inside the VPC
(unlike ../lambda-code/lambda_handler.py which runs train/predict/export):
sync_real_data needs real internet access to reach API-Football and
Football-Data.org, which a NAT-less VPC Lambda can't provide. Staying
outside the VPC gives this function default internet/AWS-API access, but
no route to the EC2 instance's private Postgres — so instead of connecting
to the database itself, it asks AWS Systems Manager to run the sync command
ON the EC2 box, where Django already has a local DB connection and the
instance's own internet access via its public IP.

No Django app or ml-layer needed here — just boto3, which ships with the
standard Lambda Python runtime.
"""

import os
import re
import json
import time
import boto3

ssm = boto3.client("ssm")

INSTANCE_ID = os.environ["INSTANCE_ID"]
TASKS_API_KEY = os.environ.get("TASKS_API_KEY", "")

# League/season codes are short alphanumeric identifiers (e.g. "E0", "2425").
# Reject anything else before it ever reaches a shell command string.
_SAFE_CODE = re.compile(r"^[A-Za-z0-9]{1,10}$")


def _json_response(status: int, payload: dict) -> dict:
    return {"statusCode": status, "body": json.dumps(payload, default=str)}


def _sanitize_codes(value) -> list:
    values = value if isinstance(value, list) else [value]
    return [v for v in values if isinstance(v, str) and _SAFE_CODE.match(v)]


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if not TASKS_API_KEY or headers.get("x-api-key") != TASKS_API_KEY:
        return _json_response(401, {"error": "unauthorized"})

    body = {}
    if event.get("body"):
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            pass
    body.update(event.get("queryStringParameters") or {})

    args = ["--fixtures"]
    leagues = _sanitize_codes(body["leagues"]) if body.get("leagues") else []
    if leagues:
        args.append("--leagues " + " ".join(leagues))
    seasons = _sanitize_codes(body["seasons"]) if body.get("seasons") else []
    if seasons:
        args.append("--seasons " + " ".join(seasons))
    if body.get("clear"):
        args.append("--clear")

    command = (
        "cd /opt/bet_hope && "
        "docker compose -f docker-compose.prod.yml exec -T backend "
        "python manage.py sync_real_data " + " ".join(args)
    )

    print(f"[SyncDispatcher] dispatching via SSM: {command}")

    send = ssm.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command]},
        TimeoutSeconds=580,
    )
    command_id = send["Command"]["CommandId"]

    result = _wait_for_command(command_id, INSTANCE_ID)
    print(f"[SyncDispatcher] sync_real_data: {result['status']} ({result.get('duration_seconds', '?')}s)")
    return _json_response(200, result)


def _wait_for_command(command_id: str, instance_id: str, max_wait: int = 550) -> dict:
    start = time.time()
    # Give SSM a moment to register the command before the first poll.
    time.sleep(2)
    while time.time() - start < max_wait:
        try:
            invocation = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(2)
            continue
        status = invocation["Status"]
        if status not in ("Pending", "InProgress", "Delayed"):
            return {
                "status": "success" if status == "Success" else "error",
                "command": "sync_real_data",
                "ssm_status": status,
                "stdout": invocation.get("StandardOutputContent", "")[-3000:],
                "stderr": invocation.get("StandardErrorContent", "")[-1000:],
                "duration_seconds": round(time.time() - start, 1),
            }
        time.sleep(3)
    return {
        "status": "timeout",
        "command": "sync_real_data",
        "error": "SSM command did not finish within the dispatcher's wait window",
        "ssm_command_id": command_id,
    }
