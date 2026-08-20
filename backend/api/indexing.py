"""Framework-neutral HTTP adapter for indexing-job creation and status."""

from __future__ import annotations

from typing import Any

from backend.api.query import HttpResponse
from backend.indexing.jobs import IndexingJobService, JobNotFoundError, JobRetryLimitError, ProcessingJob


class IndexingHttpAdapter:
    """Expose job operations without selecting a web framework."""

    def __init__(self, service: IndexingJobService) -> None:
        self.service = service

    def post(self, body: object) -> HttpResponse:
        if not isinstance(body, dict) or set(body) - {"creator_id", "content_id", "pipeline_version"}:
            return _bad_request("creator_id, content_id, and pipeline_version are required")
        try:
            job = self.service.submit_content(
                body.get("creator_id"),
                body.get("content_id"),
                body.get("pipeline_version"),
            )
        except ValueError:
            return _bad_request("creator_id, content_id, and pipeline_version are required")
        return HttpResponse(202, _serialize_job(job))

    def get(self, job_id: str) -> HttpResponse:
        try:
            return HttpResponse(200, _serialize_job(self.service.status(job_id)))
        except JobNotFoundError:
            return HttpResponse(404, {"error": {"code": "job_not_found"}})

    def retry(self, job_id: str) -> HttpResponse:
        try:
            return HttpResponse(202, _serialize_job(self.service.retry(job_id)))
        except JobNotFoundError:
            return HttpResponse(404, {"error": {"code": "job_not_found"}})
        except (JobRetryLimitError, ValueError):
            return HttpResponse(409, {"error": {"code": "job_not_retryable"}})


def _serialize_job(job: ProcessingJob) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "creator_id": job.creator_id,
        "content_id": job.content_id,
        "pipeline_version": job.pipeline_version,
        "state": job.state.value,
        "progress": job.progress,
        "attempts": job.attempts,
        "ai_job_id": job.ai_job_id,
        "graph_complete": job.graph_complete,
        "vector_complete": job.vector_complete,
        "failed_stage": job.failed_stage,
        "error_code": job.error_code,
    }


def _bad_request(message: str) -> HttpResponse:
    return HttpResponse(400, {"error": {"code": "invalid_indexing_request", "message": message}})
