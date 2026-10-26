"""Receives Alertmanager webhooks and logs them, one line per alert.

This is the starting point for the ServiceNow bridge. For now it only proves
alerts are leaving Prometheus and arriving somewhere.
"""
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

MAX_BODY = 1_000_000  # don't read arbitrarily large requests


class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/alerts":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_BODY:
            self.send_error(400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400)
            return

        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            print(
                f"{now} {alert.get('status', '?').upper():8} "
                f"{labels.get('alertname', '?'):16} {labels.get('severity', '?'):8} "
                f"{alert.get('annotations', {}).get('summary', '')}",
                flush=True,
            )
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # skip the default access log, the alert lines are enough


if __name__ == "__main__":
    print("alert receiver listening on :5001", flush=True)
    HTTPServer(("0.0.0.0", 5001), AlertHandler).serve_forever()
