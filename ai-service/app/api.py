"""FastAPI-compatible routes with a standard-library HTTP fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

from .jobs import FixtureVideoPipeline, JobService, JobState, ProcessVideoRequest


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: dict[str, object]


class StandardLibraryApplication:
    """Route the documented API without FastAPI or another web dependency."""

    def __init__(self, service: JobService | None = None) -> None:
        self.service = service or JobService(FixtureVideoPipeline())

    def dispatch(
        self,
        method: str,
        path: str,
        body: object | None = None,
    ) -> HttpResponse:
        route = urlsplit(path).path.rstrip("/") or "/"
        if method == "GET" and route == "/health":
            return HttpResponse(
                200,
                {
                    "status": "ok",
                    "service": "ai-service",
                    "implementation": "stdlib",
                },
            )
        if method == "POST" and route == "/jobs/process-video":
            return self._submit(body)
        if method == "GET" and route.startswith("/jobs/"):
            parts = route.split("/")
            if len(parts) == 3 and parts[2]:
                return self._status(parts[2])
            if len(parts) == 4 and parts[2] and parts[3] == "result":
                return self._result(parts[2])
        return HttpResponse(
            404,
            {"error": {"code": "NOT_FOUND", "message": "route not found"}},
        )

    def serve(self, host: str = "127.0.0.1", port: int = 8001) -> None:
        """Serve the same routes with ``http.server`` for local fallback use."""

        application = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
                self._respond(application.dispatch("GET", self.path))

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length)
                try:
                    body = json.loads(raw_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._respond(
                        HttpResponse(
                            400,
                            {
                                "error": {
                                    "code": "INVALID_JSON",
                                    "message": "body must be valid JSON",
                                }
                            },
                        )
                    )
                    return
                self._respond(application.dispatch("POST", self.path, body))

            def _respond(self, response: HttpResponse) -> None:
                payload = json.dumps(response.body).encode("utf-8")
                self.send_response(response.status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:
                return

        with ThreadingHTTPServer((host, port), Handler) as server:
            server.serve_forever()

    def close(self) -> None:
        self.service.close()

    def _submit(self, body: object | None) -> HttpResponse:
        try:
            request = ProcessVideoRequest.from_mapping(body)
            record = self.service.submit(request)
        except ValueError as exc:
            return HttpResponse(
                400,
                {"error": {"code": "INVALID_REQUEST", "message": str(exc)}},
            )
        return HttpResponse(202, {"job_id": record.job_id, "status": record.status.value})

    def _status(self, job_id: str) -> HttpResponse:
        record = self.service.get_status(job_id)
        if record is None:
            return HttpResponse(
                404,
                {"error": {"code": "JOB_NOT_FOUND", "message": "job not found"}},
            )
        return HttpResponse(200, record.status_dict())

    def _result(self, job_id: str) -> HttpResponse:
        record = self.service.get_status(job_id)
        if record is None:
            return HttpResponse(
                404,
                {"error": {"code": "JOB_NOT_FOUND", "message": "job not found"}},
            )
        if record.status == JobState.FAILED:
            return HttpResponse(409, record.status_dict())
        if record.status != JobState.COMPLETED:
            return HttpResponse(202, record.status_dict())
        result = self.service.get_result(job_id)
        return HttpResponse(200, result or {})


def create_app(service: JobService | None = None) -> object:
    """Return a FastAPI app when installed, otherwise the stdlib route adapter."""

    service = service or JobService(FixtureVideoPipeline())
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError:
        return StandardLibraryApplication(service)

    app = FastAPI(title="VideoGraph AI Service")
    app.state.job_service = service

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "ai-service", "implementation": "fastapi"}

    @app.post("/jobs/process-video", status_code=202)
    async def process_video(payload: dict[str, object]) -> dict[str, object]:
        try:
            request = ProcessVideoRequest.from_mapping(payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        record = service.submit(request)
        return {"job_id": record.job_id, "status": record.status.value}

    @app.get("/jobs/{job_id}")
    async def job_status(job_id: str) -> dict[str, object]:
        record = service.get_status(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="job not found")
        return record.status_dict()

    @app.get("/jobs/{job_id}/result")
    async def job_result(job_id: str) -> dict[str, object]:
        record = service.get_status(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="job not found")
        if record.status == JobState.FAILED:
            raise HTTPException(status_code=409, detail=record.status_dict())
        if record.status != JobState.COMPLETED:
            raise HTTPException(status_code=202, detail=record.status_dict())
        return service.get_result(job_id) or {}

    return app
