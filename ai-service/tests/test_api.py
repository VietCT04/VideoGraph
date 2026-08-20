"""Focused tests for async job orchestration and both route boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.api import StandardLibraryApplication
from app.jobs import JobService, JobState, ProcessVideoRequest
from contracts.validation import validate_extraction


class InvalidPipeline:
    def process(self, request, notify):
        notify(JobState.PREPROCESSING)
        return {"malformed": True}


class AsyncAPIAndJobTests(unittest.TestCase):
    def test_standard_library_routes_submit_status_and_validated_result(self) -> None:
        service = JobService()
        application = StandardLibraryApplication(service)
        try:
            health = application.dispatch("GET", "/health")
            self.assertEqual(health.status_code, 200)

            response = application.dispatch(
                "POST",
                "/jobs/process-video",
                {"content_id": "video-1", "creator_id": "creator-1", "upload_ref": "fixture.mp4"},
            )
            self.assertEqual(response.status_code, 202)
            job_id = response.body["job_id"]
            record = service.wait_for_terminal(job_id)
            self.assertIsNotNone(record)
            self.assertEqual(record.status, JobState.COMPLETED)

            status = application.dispatch("GET", f"/jobs/{job_id}")
            result = application.dispatch("GET", f"/jobs/{job_id}/result")
            self.assertEqual(status.status_code, 200)
            self.assertEqual(status.body["status"], "completed")
            self.assertEqual(result.status_code, 200)
            validate_extraction(result.body)
            self.assertEqual(result.body["content_id"], "video-1")
        finally:
            application.close()

    def test_invalid_input_and_missing_jobs_are_machine_readable(self) -> None:
        service = JobService()
        application = StandardLibraryApplication(service)
        try:
            invalid = application.dispatch("POST", "/jobs/process-video", {"content_id": "only-id"})
            missing = application.dispatch("GET", "/jobs/not-found")

            self.assertEqual(invalid.status_code, 400)
            self.assertEqual(invalid.body["error"]["code"], "INVALID_REQUEST")
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.body["error"]["code"], "JOB_NOT_FOUND")
        finally:
            application.close()

    def test_invalid_pipeline_fails_without_exposing_partial_result(self) -> None:
        service = JobService(pipeline=InvalidPipeline())
        request = ProcessVideoRequest("video-2", "creator-2", upload_ref="fixture.mp4")
        try:
            record = service.submit(request)
            finished = service.wait_for_terminal(record.job_id)
            self.assertIsNotNone(finished)
            self.assertEqual(finished.status, JobState.FAILED)
            self.assertEqual(finished.error_code, "CONTRACT_VALIDATION_FAILED")
            self.assertIsNone(service.get_result(record.job_id))
        finally:
            service.close()


if __name__ == "__main__":
    unittest.main()
