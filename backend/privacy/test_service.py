"""Fixture-backed checks for creator privacy and synchronized store suppression."""

from __future__ import annotations

import unittest

from backend.api.privacy import PrivacyHttpAdapter
from backend.api.query import QueryHttpAdapter
from backend.graph.fixtures import load_extraction_fixture
from backend.graph.ingestion import ExtractionGraphIngestor
from backend.graph.repository import InMemoryGraphRepository
from backend.graph.tools import SafeGraphQueryService
from backend.planner.planner import RetrievalPlanner
from backend.privacy.service import InMemoryPrivacyRepository, PrivacyControlService
from backend.query.service import QueryApplicationService
from backend.search.embeddings import FixtureHashEmbeddingProvider
from backend.search.fusion import ResultFusionService
from backend.search.orchestrator import HybridRetrievalOrchestrator
from backend.search.semantic_retrieval import SemanticMomentRetriever, index_extraction_fixture
from backend.search.vector_repository import InMemoryVectorRepository


def build_fixture_environment():
    fixture = load_extraction_fixture("beauty")
    graph_repository = InMemoryGraphRepository()
    ExtractionGraphIngestor(graph_repository).ingest(fixture)
    embedder = FixtureHashEmbeddingProvider()
    vector_repository = InMemoryVectorRepository()
    index_extraction_fixture(vector_repository, fixture, embedder)
    privacy = PrivacyControlService(InMemoryPrivacyRepository(), graph_repository, vector_repository)
    graph = SafeGraphQueryService(graph_repository)
    semantic = SemanticMomentRetriever(vector_repository, embedder)
    retrieval = HybridRetrievalOrchestrator(lambda plan: graph.search(plan), lambda plan: semantic.search(plan))
    planner = RetrievalPlanner({"creator_42": "creator-42"})
    query = QueryApplicationService(planner, retrieval, ResultFusionService(), privacy_policy=privacy)
    return fixture, graph_repository, vector_repository, privacy, query


class PrivacyTests(unittest.TestCase):
    def test_opt_in_and_exclude_suppress_both_retrieval_representations(self) -> None:
        fixture, graph_repository, vector_repository, privacy, query = build_fixture_environment()
        privacy.set_memory("creator-42", True, "creator-42")
        privacy.select_content("creator-42", fixture["content_id"], "creator-42")
        visible = QueryHttpAdapter(query).post({"query": "@creator_42 which lipstick does she use?"})

        privacy.exclude_content("creator-42", fixture["content_id"], "creator-42")
        hidden = QueryHttpAdapter(query).post({"query": "@creator_42 which lipstick does she use?"})

        self.assertEqual(visible.status_code, 200)
        self.assertEqual(hidden.status_code, 403)
        self.assertFalse(graph_repository.moments["moment_beauty_video_001_5000_11000"].visibility == "public")
        self.assertEqual(vector_repository.rows["moment_beauty_video_001_5000_11000"].visibility, "excluded")

    def test_rejection_and_deletion_propagate_and_unauthorized_management_fails(self) -> None:
        fixture, graph_repository, vector_repository, privacy, _ = build_fixture_environment()
        privacy.set_memory("creator-42", True, "creator-42")
        privacy.select_content("creator-42", fixture["content_id"], "creator-42")
        adapter = PrivacyHttpAdapter(privacy)

        forbidden = adapter.content_action({"creator_id": "creator-42", "content_id": fixture["content_id"], "requester_id": "other", "action": "reject"})
        rejected = adapter.content_action({"creator_id": "creator-42", "content_id": fixture["content_id"], "requester_id": "creator-42", "action": "reject"})
        deleted = adapter.content_action({"creator_id": "creator-42", "content_id": fixture["content_id"], "requester_id": "creator-42", "action": "delete"})

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(deleted.status_code, 200)
        self.assertNotIn(fixture["content_id"], graph_repository.contents)
        self.assertFalse(vector_repository.rows)


if __name__ == "__main__":
    unittest.main()
