"""
Bet_Hope Lambda Handler

Routes: POST /sync, POST /train, POST /predict, POST /export, GET /health
Uses Lambda Web Adapter to run as HTTP server on port 8080.
"""

import os
import sys
import json
import traceback
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.lambda_settings")

PORT = int(os.getenv("PORT", "8080"))


def run_management_command(cmd: str, *args) -> dict:
    """Run a Django management command and return structured output."""
    start = datetime.utcnow()
    try:
        command = [sys.executable, "manage.py", cmd] + list(args)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
            cwd="/app",
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        duration = (datetime.utcnow() - start).total_seconds()
        return {
            "status": "success" if result.returncode == 0 else "error",
            "command": cmd,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],  # Last 2000 chars
            "stderr": result.stderr[-1000:],  # Last 1000 chars
            "duration_seconds": round(duration, 1),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "command": cmd,
            "error": "Command exceeded 10 minute timeout",
        }
    except Exception as e:
        return {
            "status": "error",
            "command": cmd,
            "error": str(e),
            "traceback": traceback.format_exc()[-1500:],
        }


ROUTES = {
    "/sync": ("sync_real_data", ["--fixtures"]),
    "/train": ("train_model", []),
    "/predict": ("generate_predictions", []),
    "/export": ("export_training_data", ["--output", "/tmp/training_data.json"]),
}


class LambdaHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress HTTP access logs

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "healthy", "service": "bet-hope-lambda"})
        elif self.path.startswith("/tasks/") and "/status" in self.path:
            self._send_json({"status": "tasks not yet persisted"})
        else:
            self._send_json(
                {"error": "not found", "routes": list(ROUTES.keys())}, 404
            )

    def do_POST(self):
        if self.path not in ROUTES:
            self._send_json(
                {"error": f"unknown route: {self.path}", "valid_routes": list(ROUTES.keys())},
                404,
            )
            return

        cmd, default_args = ROUTES[self.path]

        # Parse optional query params for extra args
        content_len = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_len > 0:
            raw = self.rfile.read(content_len)
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                pass

        # Build args
        args = list(default_args)
        if body.get("leagues"):
            args.extend(["--leagues"] + body["leagues"])
        if body.get("seasons"):
            args.extend(["--seasons"] + body["seasons"])
        if body.get("clear"):
            args.append("--clear")
        if body.get("fixtures"):
            args.append("--fixtures")

        result = run_management_command(cmd, *args)
        print(f"[{cmd}] {result.get('status')} — {result.get('duration_seconds', '?')}s")
        self._send_json(result)


if __name__ == "__main__":
    print(f"Starting Bet_Hope Lambda handler on port {PORT}")
    server = HTTPServer(("0.0.0.0", PORT), LambdaHandler)
    server.serve_forever()