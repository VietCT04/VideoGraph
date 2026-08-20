"""Durable indexing state machine and idempotent graph/vector orchestration."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Protocol

from contracts.validation import ContractValidationError, validate_extraction

from backend.graph.ingestion import ExtractionGraphIngestor
from backend.graph.repository import GraphRepository
from backend.search.embeddings import EmbeddingProvider
from backend.search.semantic_retrieval import index_extraction_fixture
from backend.search.vector_repository import VectorRepository

from .client import AIServiceClient


class JobState(str, Enum):
    QUEUED = "queued"
    SUBMITTED = "submitted"
    AI_PROCESSING = "ai_processing"
    AI_DONE = "ai_done"
    INGESTING_GRAPH = "ingesting_graph"
    INGESTING_VECTOR = "ingesting_vector"
    READY = "ready"
    FAILED = "failed"


@dataclass
class ProcessingJob:
    id: str
    creator_id: str
    content_id: str
    pipeline_version: str
    state: JobState = JobState.QUEUED
    progress: int = 0
    attempts: int = 0
    ai_job_id: str | None = None
    graph_complete: bool = False
    vector_complete: bool = False
    failed_stage: str | None = None
    error_code: str | None = None

    @property
    def processing_key(self) -> tuple[str, str, str]:
        return (self.creator_id, self.content_id, self.pipeline_version)


class IndexingJobRepository(Protocol):
    def create(self, job: ProcessingJob) -> ProcessingJob:
        ...

    def get(self, job_id: str) -> ProcessingJob | None:
        ...

    def get_by_processing_key(self, key: tuple[str, str, str]) -> ProcessingJob | None:
        ...

    def save(self, job: ProcessingJob) -> ProcessingJob:
        ...


class InMemoryIndexingJobRepository:
    """Process-durable fixture store with unique processing-key semantics."""

    def __init__(self) -> None:
        self.jobs: dict[str, ProcessingJob] = {}
        self.keys: dict[tuple[str, str, str], str] = {}

    def create(self, job: ProcessingJob) -> ProcessingJob:
        current = self.get_by_processing_key(job.processing_key)
        if current is not None:
            return current
        self.jobs[job.id] = job
        self.keys[job.processing_key] = job.id
        return job

    def get(self, job_id: str) -> ProcessingJob | None:
        return self.jobs.get(job_id)

    def get_by_processing_key(self, key: tuple[str, str, str]) -> ProcessingJob | None:
        job_id = self.keys.get(key)
        return self.jobs.get(job_id) if job_id else None

    def save(self, job: ProcessingJob) -> ProcessingJob:
        if job.id not in self.jobs:
            raise KeyError(job.id)
        self.jobs[job.id] = job
        self.keys[job.processing_key] = job.id
        return job


class JobNotFoundError(KeyError):
    """Raised when a status or retry request references no job."""


class JobRetryLimitError(ValueError):
    """Raised when a failed job has exhausted its configured retry budget."""


class IndexingJobService:
    """Run one durable job through AI extraction, graph, and vector stages."""

    _allowed_transitions = {
        JobState.QUEUED: {JobState.SUBMITTED, JobState.FAILED},
        JobState.SUBMITTED: {JobState.AI_PROCESSING, JobState.FAILED},
        JobState.AI_PROCESSING: {JobState.AI_DONE, JobState.FAILED},
        JobState.AI_DONE: {JobState.INGESTING_GRAPH, JobState.INGESTING_VECTOR, JobState.FAILED},
        JobState.INGESTING_GRAPH: {JobState.INGESTING_VECTOR, JobState.FAILED},
        JobState.INGESTING_VECTOR: {JobState.READY, JobState.FAILED},
        JobState.READY: set(),
        JobState.FAILED: {JobState.QUEUED, JobState.INGESTING_GRAPH, JobState.INGESTING_VECTOR},
    }

    def __init__(
        self,
        ai_client: AIServiceClient,
        jobs: IndexingJobRepository,
        graph_repository: GraphRepository,
        vector_repository: VectorRepository,
        embedder: EmbeddingProvider,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.ai_client = ai_client
        self.jobs = jobs
        self.graph_repository = graph_repository
        self.vector_repository = vector_repository
        self.embedder = embedder
        self.max_attempts = max_attempts
        self.graph_ingestor = ExtractionGraphIngestor(graph_repository)

    def submit_content(self, creator_id: str, content_id: str, pipeline_version: str) -> ProcessingJob:
        _require_text(creator_id, "creator_id")
        _require_text(content_id, "content_id")
        _require_text(pipeline_version, "pipeline_version")
        key = (creator_id, content_id, pipeline_version)
        current = self.jobs.get_by_processing_key(key)
        if current is not None:
            return current
        job_id = "job_" + hashlib.sha256("|".join(key).encode()).hexdigest()[:16]
        return self.jobs.create(ProcessingJob(job_id, creator_id, content_id, pipeline_version))

    def process(self, job_id: str) -> ProcessingJob:
        job = self._get(job_id)
        if job.state in {JobState.READY, JobState.FAILED}:
            return job
        if job.state == JobState.QUEUED:
            job = self._transition(job, JobState.SUBMITTED, attempts=job.attempts + 1, progress=5)
            try:
                ai_job_id = self.ai_client.submit_content(job.creator_id, job.content_id, job.pipeline_version)
            except Exception:
                return self._fail(job, "ai_submit")
            job = self._save(replace(job, ai_job_id=ai_job_id))
        if job.state == JobState.SUBMITTED:
            job = self._transition(job, JobState.AI_PROCESSING, progress=10)
        if job.state == JobState.AI_PROCESSING:
            status = self.ai_client.get_status(job.ai_job_id or "")
            if status.state == "failed":
                return self._fail(job, status.error_code or "ai_processing")
            if status.state != "completed":
                return self._save(replace(job, progress=max(job.progress, min(99, status.progress))))
            try:
                payload = validate_extraction(self.ai_client.get_result(job.ai_job_id or ""))
            except (ContractValidationError, ValueError, TypeError, KeyError):
                return self._fail(job, "invalid_extraction")
            job = self._transition(job, JobState.AI_DONE, progress=35)
        else:
            payload = self._validated_result(job)
            if payload is None:
                return self._fail(job, "invalid_extraction")
        if job.state == JobState.AI_DONE:
            next_state = JobState.INGESTING_GRAPH if not job.graph_complete else JobState.INGESTING_VECTOR
            job = self._transition(job, next_state, progress=45 if not job.graph_complete else 75)
        if job.state == JobState.INGESTING_GRAPH:
            try:
                self.graph_ingestor.ingest(payload)
            except Exception:
                return self._fail(job, "graph_persistence")
            job = self._save(replace(job, graph_complete=True, progress=70))
            job = self._transition(job, JobState.INGESTING_VECTOR, progress=75)
        if job.state == JobState.INGESTING_VECTOR:
            try:
                index_extraction_fixture(self.vector_repository, payload, self.embedder)
            except Exception:
                return self._fail(job, "vector_persistence")
            return self._transition(
                job,
                JobState.READY,
                vector_complete=True,
                progress=100,
                failed_stage=None,
                error_code=None,
            )
        return job

    def retry(self, job_id: str) -> ProcessingJob:
        job = self._get(job_id)
        if job.state != JobState.FAILED:
            raise ValueError("only failed jobs can be retried")
        if job.attempts >= self.max_attempts:
            raise JobRetryLimitError(job.id)
        if job.failed_stage == "vector" and job.graph_complete:
            next_state = JobState.INGESTING_VECTOR
        elif job.failed_stage == "graph":
            next_state = JobState.INGESTING_GRAPH
        else:
            next_state = JobState.QUEUED
        return self._transition(job, next_state, error_code=None, failed_stage=None)

    def status(self, job_id: str) -> ProcessingJob:
        return self._get(job_id)

    def _validated_result(self, job: ProcessingJob) -> dict[str, Any] | None:
        try:
            return validate_extraction(self.ai_client.get_result(job.ai_job_id or ""))
        except (ContractValidationError, ValueError, TypeError, KeyError):
            return None

    def _get(self, job_id: str) -> ProcessingJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def _save(self, job: ProcessingJob) -> ProcessingJob:
        return self.jobs.save(job)

    def _transition(self, job: ProcessingJob, state: JobState, **changes: Any) -> ProcessingJob:
        if state != job.state and state not in self._allowed_transitions[job.state]:
            raise RuntimeError(f"invalid indexing transition {job.state.value} -> {state.value}")
        return self._save(replace(job, state=state, **changes))

    def _fail(self, job: ProcessingJob, error_code: str) -> ProcessingJob:
        failed_stage = {
            JobState.QUEUED: "ai_submit",
            JobState.SUBMITTED: "ai_submit",
            JobState.AI_PROCESSING: "ai",
            JobState.AI_DONE: "validation",
            JobState.INGESTING_GRAPH: "graph",
            JobState.INGESTING_VECTOR: "vector",
        }.get(job.state, error_code)
        return self._transition(job, JobState.FAILED, failed_stage=failed_stage, error_code=error_code)


def _require_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
