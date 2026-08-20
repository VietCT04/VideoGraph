"""Fixture-backed checks for durable indexing state and retry behavior."""

from __future__ import annotations

import unittest

from backend.api.indexing import IndexingHttpAdapter
from backend.graph.fixtures import load_extraction_fixture
from backend.graph.repository import InMemoryGraphRepository
from backend.indexing.client import FixtureAIServiceClient
from backend.indexing.jobs import IndexingJobService, InMemoryIndexingJobRepository, JobState
from backend.search.embeddings import FixtureHashEmbeddingProvider
from backend.search.vector_repository import InMemoryVectorRepository


class FailingOnceVectorRepository(InMemoryVectorRepository):
    def __init__(self) -> None:
        super().__init__()
        self.fail = True

    def upsert(self, row):
        if self.fail:
            self.fail = False
            raise RuntimeError("fixture vector outage")
        return super().upsert(row)


def build_service(vector_repository=None):
    fixture = load_extraction_fixture("beauty")
    return IndexingJobService(
        FixtureAIServiceClient({fixture["content_id"]: fixture}),
        InMemoryIndexingJobRepository(),
        InMemoryGraphRepository(),
        vector_repository or InMemoryVectorRepository(),
        FixtureHashEmbeddingProvider(),
    )


class IndexingJobTests(unittest.TestCase):
    def test_fixture_job_reaches_ready_and_duplicate_submission_is_idempotent(self) -> None:
        service = build_service()
        job = service.submit_content("creator-42", "beauty-video-001", "fixture-v1")

        ready = service.process(job.id)
        duplicate = service.submit_content("creator-42", "beauty-video-001", "fixture-v1")

        self.assertEqual(ready.state, JobState.READY)
        self.assertEqual(ready.progress, 100)
        self.assertEqual(duplicate.id, job.id)

    def test_vector_failure_is_visible_and_retry_skips_completed_graph_stage(self) -> None:
        vector_repository = FailingOnceVectorRepository()
        service = build_service(vector_repository)
        job = service.submit_content("creator-42", "beauty-video-001", "fixture-v1")

        failed = service.process(job.id)
        retried = service.retry(job.id)
        ready = service.process(retried.id)

        self.assertEqual(failed.state, JobState.FAILED)
        self.assertEqual(failed.failed_stage, "vector")
        self.assertTrue(failed.graph_complete)
        self.assertEqual(ready.state, JobState.READY)

    def test_status_adapter_exposes_progress_without_running_the_worker(self) -> None:
        service = build_service()
        adapter = IndexingHttpAdapter(service)
        response = adapter.post({"creator_id": "creator-42", "content_id": "beauty-video-001", "pipeline_version": "fixture-v1"})

        self.assertEqual(response.status_code, 202)
        status = adapter.get(response.body["job_id"])
        self.assertEqual(status.body["state"], "queued")
        self.assertEqual(status.body["progress"], 0)


if __name__ == "__main__":
    unittest.main()
