"""Fixture-backed tests for the query application and HTTP adapter contract."""

from __future__ import annotations

import unittest

from backend.api.query import QueryHttpAdapter
from backend.query.service import GroundedEvidenceBundle, build_fixture_query_service


class RecordingSynthesis:
    def __init__(self) -> None:
        self.bundles: list[GroundedEvidenceBundle] = []

    def synthesize(self, bundle: GroundedEvidenceBundle) -> str:
        self.bundles.append(bundle)
        return "grounded explanation"


class QueryServiceTests(unittest.TestCase):
    def test_simple_query_returns_structured_evidence_and_debug_timing(self) -> None:
        synthesis = RecordingSynthesis()
        adapter = QueryHttpAdapter(build_fixture_query_service(synthesis))

        response = adapter.post({"query": "@creator_42 which lipstick does she use?", "debug": True})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["answer_type"], "structured")
        self.assertEqual(synthesis.bundles, [])
        self.assertEqual(
            set(response.body["timing_ms"]),
            {"planner", "graph", "vector", "fusion", "synthesis", "total"},
        )
        evidence = response.body["results"][0]["evidence"][0]
        self.assertEqual(evidence["content_id"], "beauty-video-001")
        self.assertEqual(evidence["start_ms"], 5000)
        self.assertEqual(evidence["end_ms"], 11000)

    def test_complex_query_synthesizes_only_normalized_grounded_evidence(self) -> None:
        synthesis = RecordingSynthesis()
        service = build_fixture_query_service(synthesis)

        response = service.execute("@creator_42 why does she like this lipstick?", debug=True)

        self.assertEqual(response["answer_type"], "synthesized")
        self.assertEqual(response["answer"], "grounded explanation")
        self.assertEqual(len(synthesis.bundles), 1)
        self.assertEqual(synthesis.bundles[0].creator_id, "creator-42")
        self.assertEqual(synthesis.bundles[0].results[0].evidence[0].content_id, "beauty-video-001")

    def test_invalid_http_body_does_not_enter_query_service(self) -> None:
        adapter = QueryHttpAdapter(build_fixture_query_service())

        response = adapter.post({"query": "not addressed to a creator"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body["error"]["code"], "invalid_query")


if __name__ == "__main__":
    unittest.main()
