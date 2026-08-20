"""Fixture-backed checks for permissioned action tools and failure isolation."""

from __future__ import annotations

import unittest

from backend.actions.catalog import FixtureProductCatalog
from backend.actions.tools import ActionToolService
from backend.api.actions import ActionHttpAdapter
from backend.graph.ingestion import canonical_entity_id
from backend.graph.repository import InMemoryGraphRepository
from backend.privacy.service import InMemoryPrivacyRepository, PrivacyControlService
from backend.search.fusion import FusedResult, FusionEvidence
from backend.search.vector_repository import InMemoryVectorRepository


def build_result() -> FusedResult:
    canonical_id = canonical_entity_id("creator-42", "Product", "rare beauty humble lipstick")
    return FusedResult(
        result_id=canonical_id,
        label="Rare Beauty Humble lipstick",
        entity_id=canonical_id,
        entity_type="Product",
        score=0.95,
        graph_score=0.94,
        vector_score=0.9,
        relations=("USES",),
        evidence=(FusionEvidence("moment_beauty_video_001_5000_11000", "beauty-video-001", 5000, 11000),),
        direct_answer_eligible=True,
    )


class ActionToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = InMemoryGraphRepository()
        self.vector = InMemoryVectorRepository()
        self.privacy = PrivacyControlService(InMemoryPrivacyRepository(), self.graph, self.vector)
        self.privacy.set_memory("creator-42", True, "creator-42")
        self.privacy.select_content("creator-42", "beauty-video-001", "creator-42")
        self.result = build_result()
        self.tools = ActionToolService(self.privacy, FixtureProductCatalog())

    def test_jump_uses_exact_retrieved_evidence_timestamp(self) -> None:
        result = self.tools.jump_to_timestamp("creator-42", self.result)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.payload["content_id"], "beauty-video-001")
        self.assertEqual(result.payload["start_ms"], 5000)
        self.assertEqual(result.payload["end_ms"], 11000)

    def test_product_and_similar_product_tools_use_canonical_entity(self) -> None:
        product = self.tools.find_product("creator-42", build_result())
        similar = self.tools.find_similar_products("creator-42", build_result())

        self.assertEqual(product.status, "success")
        self.assertEqual(product.payload["canonical_product_id"], self.result.entity_id)
        self.assertEqual(similar.status, "success")
        self.assertEqual(len(similar.payload["products"]), 1)

    def test_hidden_evidence_is_rejected_and_lookup_failure_preserves_evidence(self) -> None:
        self.privacy.exclude_content("creator-42", "beauty-video-001", "creator-42")
        denied = self.tools.jump_to_timestamp("creator-42", self.result)
        self.privacy.select_content("creator-42", "beauty-video-001", "creator-42")
        unknown = ActionToolService(self.privacy, FixtureProductCatalog(())).find_product("creator-42", build_result())

        self.assertEqual(denied.status, "denied")
        self.assertEqual(denied.evidence, ())
        self.assertEqual(unknown.status, "failed")
        self.assertEqual(unknown.error_code, "product_not_found")
        self.assertEqual(len(unknown.evidence), 1)

    def test_http_adapter_resolves_canonical_result_not_user_supplied_timestamp(self) -> None:
        adapter = ActionHttpAdapter(self.tools, lambda result_id: self.result if result_id == self.result.result_id else None)

        response = adapter.post({"action": "jump_to_timestamp", "creator_id": "creator-42", "result_id": self.result.result_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["payload"]["start_ms"], 5000)


if __name__ == "__main__":
    unittest.main()
