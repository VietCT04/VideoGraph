"""Small health-aware placeholder used until the service issues add real APIs."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.getenv("PORT", "8000"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "videograph-placeholder")


class PlaceholderHandler(BaseHTTPRequestHandler):
    server_version = "VideoGraphPlaceholder/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler interface
        if self.path in {"/health", "/healthz", "/readyz"}:
            self._write_json(
                200,
                {
                    "service": SERVICE_NAME,
                    "status": "ok",
                    "placeholder": True,
                    "dependencies_checked": False,
                },
            )
            return

        if self.path == "/":
            self._write_json(
                200,
                {
                    "service": SERVICE_NAME,
                    "status": "placeholder",
                    "message": "Application routes are provided by later implementation issues.",
                },
            )
            return

        self._write_json(
            501,
            {
                "service": SERVICE_NAME,
                "status": "not_implemented",
                "path": self.path,
            },
        )

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler interface
        self._write_json(
            501,
            {
                "service": SERVICE_NAME,
                "status": "not_implemented",
                "path": self.path,
            },
        )

    def _write_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        # Keep the placeholder quiet and avoid echoing request data into logs.
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), PlaceholderHandler).serve_forever()
