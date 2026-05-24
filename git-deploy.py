#!/usr/bin/env python3
"""git-deploy: lightweight git-push-to-deploy webhook listener."""

import hmac, hashlib, json, subprocess, sys, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required: pip3 install pyyaml")

CONFIG_PATH = os.environ.get("GIT_DEPLOY_CONFIG", "/etc/git-deploy/config.yaml")


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def verify_signature(payload_body, signature_header, secret):
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        config = load_config()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if not verify_signature(
            body, self.headers.get("X-Hub-Signature-256"), config["webhook_secret"]
        ):
            log("rejected: bad signature")
            self._respond(403, "bad signature")
            return

        payload = json.loads(body)
        repo = payload.get("repository", {}).get("full_name", "")
        ref = payload.get("ref", "")
        branch = ref.split("/")[-1] if ref.startswith("refs/heads/") else None

        project = config.get("projects", {}).get(repo)
        if not project:
            log(f"ignored: {repo} not in config")
            self._respond(200, f"ignored: {repo} not configured")
            return

        target_branch = project.get("branch", "main")
        if branch != target_branch:
            log(f"ignored: {repo} push to {branch}, watching {target_branch}")
            self._respond(200, f"ignored: branch {branch}")
            return

        directory = project["directory"]
        deploy_cmd = project["deploy_command"]
        log(f"deploying {repo}@{branch} in {directory}")

        try:
            result = subprocess.run(
                deploy_cmd,
                shell=True,
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = (
                f"repo: {repo}\nbranch: {branch}\nexit: {result.returncode}\n"
                f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
            )
            log(f"deployed {repo}: exit={result.returncode}")
            self._respond(200 if result.returncode == 0 else 500, output)
        except subprocess.TimeoutExpired:
            log(f"deploy timeout: {repo}")
            self._respond(500, f"deploy timed out after 300s")
        except Exception as e:
            log(f"deploy error: {repo}: {e}")
            self._respond(500, str(e))

    def do_GET(self):
        if self.path == "/health":
            config = load_config()
            projects = list(config.get("projects", {}).keys())
            self._respond(200, json.dumps({"ok": True, "projects": projects}))
            return
        self.send_response(404)
        self.end_headers()

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    config = load_config()
    port = config.get("listen_port", 9000)
    projects = config.get("projects", {})
    log(f"git-deploy listening on port {port}")
    for repo, proj in projects.items():
        log(f"  {repo} → {proj['directory']}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
