"""Framework-neutral orchestration for the grounded ``@creator`` query path."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from backend.graph.fixtures import load_extraction_fixture
from backend.graph.ingestion import ExtractionGraphIngestor
from backend.graph.repository import InMemoryGraphRepository
from backend.graph.tools import SafeGraphQueryService
from backend.planner.planner import RetrievalPlanner
from backend.search.embeddings import FixtureHashEmbeddingProvider
from backend.search.fusion import FusedResult, ResultFusionService
from backend.search.orchestrator import HybridRetrievalOrchestrator, RetrievalBundle
from backend.search.semantic_retrieval import SemanticMomentRetriever, index_extraction_fixture
from backend.search.vector_repository import InMemoryVectorRepository


@dataclass(frozen=True)
class GroundedEvidence:
    """One exact source reference allowed into the synthesis boundary."""

    moment_id: str
    content_id: str
    start_ms: int
    end_ms: int
    semantic_text: str | None


@dataclass(frozen=True)
class GroundedResult:
    """Normalized result data exposed to direct responses and synthesis."""

    result_id: str
    label: str
    entity_id: str | None
    relations: tuple[str, ...]
    score: float
    evidence: tuple[GroundedEvidence, ...]


@dataclass(frozen=True)
class GroundedEvidenceBundle:
    """The only input a synthesis provider receives from the query service."""

    creator_id: str
    question: str
    results: tuple[GroundedResult, ...]
    partial_success: bool


class SynthesisProvider(Protocol):
    """Optional final-answer adapter over already-authorized evidence."""

    def synthesize(self, bundle: GroundedEvidenceBundle) -> str:
        ...


class QueryPrivacyPolicy(Protocol):
    """Backend-owned creator authorization check for viewer retrieval."""

    def authorize_creator(self, creator_id: str) -> None:
        ...


class FixtureSynthesisProvider:
    """Deterministic prose adapter used to exercise the synthesis boundary."""

    def synthesize(self, bundle: GroundedEvidenceBundle) -> str:
        if not bundle.results:
            return "No grounded creator evidence matched the question."
        labels = ", ".join(result.label for result in bundle.results[:3])
        return f"Grounded creator evidence for {bundle.question!r}: {labels}."


class QueryApplicationService:
    """Run parsing, planning, hybrid retrieval, fusion, and optional synthesis."""

    def __init__(
        self,
        planner: RetrievalPlanner,
        retrieval: HybridRetrievalOrchestrator,
        fusion: ResultFusionService | None = None,
        synthesis: SynthesisProvider | None = None,
        allowed_visibility: Iterable[str] = ("public",),
        privacy_policy: QueryPrivacyPolicy | None = None,
    ) -> None:
        visibility = tuple(allowed_visibility)
        if not visibility:
            raise ValueError("at least one visibility value is required")
        self.planner = planner
        self.retrieval = retrieval
        self.fusion = fusion or ResultFusionService()
        self.synthesis = synthesis
        self.allowed_visibility = visibility
        self.privacy_policy = privacy_policy

    def execute(self, raw_query: str, debug: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        planner_result = self.planner.plan(raw_query)
        if self.privacy_policy is not None:
            self.privacy_policy.authorize_creator(planner_result.plan["creator_id"])
        bundle = self.retrieval.retrieve(planner_result.plan)
        fused = self.fusion.fuse(bundle)
        synthesis_latency_ms = 0.0
        warnings = _branch_warnings(bundle)
        answer: str | None = None
        answer_type = "empty" if not fused.results else "grounded"

        if fused.results and self._should_synthesize(planner_result.query.question, fused):
            if self.synthesis is None:
                warnings.append("synthesis_unavailable")
            else:
                synthesis_started = time.perf_counter()
                try:
                    answer = self.synthesis.synthesize(
                        GroundedEvidenceBundle(
                            creator_id=planner_result.plan["creator_id"],
                            question=planner_result.query.question,
                            results=tuple(_grounded_result(result) for result in fused.results),
                            partial_success=bundle.partial_success,
                        )
                    )
                except Exception:
                    warnings.append("synthesis_failed")
                else:
                    answer_type = "synthesized"
                synthesis_latency_ms = (time.perf_counter() - synthesis_started) * 1000
        elif fused.results and fused.direct_answer_eligible:
            answer_type = "structured"

        response: dict[str, Any] = {
            "creator_id": planner_result.plan["creator_id"],
            "answer_type": answer_type,
            "answer": answer,
            "results": [_serialize_result(result) for result in fused.results],
            "warnings": sorted(set(warnings)),
        }
        if debug:
            response["timing_ms"] = {
                "planner": round(planner_result.latency_ms, 3),
                "graph": bundle.graph.latency_ms,
                "vector": bundle.vector.latency_ms,
                "fusion": fused.latency_ms,
                "synthesis": round(synthesis_latency_ms, 3),
                "total": round((time.perf_counter() - started) * 1000, 3),
            }
            response["debug"] = {
                "planner_used_fallback": planner_result.used_fallback,
                "graph_status": bundle.graph.status,
                "vector_status": bundle.vector.status,
                "partial_success": bundle.partial_success,
            }
        return response

    @staticmethod
    def _should_synthesize(question: str, fused: Any) -> bool:
        if not fused.direct_answer_eligible:
            return True
        normalized = question.casefold()
        return any(
            marker in normalized
            for marker in ("why", "compare", "explain", "how did", "before", "after", "switch", "ever")
        )


def build_fixture_query_service(
    synthesis: SynthesisProvider | None = None,
) -> QueryApplicationService:
    """Build the complete local query path from the shared beauty fixture."""

    extraction = load_extraction_fixture("beauty")
    graph_repository = InMemoryGraphRepository()
    ExtractionGraphIngestor(graph_repository).ingest(extraction)

    embedder = FixtureHashEmbeddingProvider()
    vector_repository = InMemoryVectorRepository()
    index_extraction_fixture(vector_repository, extraction, embedder)

    graph = SafeGraphQueryService(graph_repository)
    semantic = SemanticMomentRetriever(vector_repository, embedder)
    retrieval = HybridRetrievalOrchestrator(
        graph_search=lambda plan: graph.search(plan),
        vector_search=lambda plan: semantic.search(plan),
    )
    planner = RetrievalPlanner(
        {"creator_42": extraction["creator_id"], "alice": extraction["creator_id"]}
    )
    return QueryApplicationService(planner, retrieval, synthesis=synthesis)


def _grounded_result(result: FusedResult) -> GroundedResult:
    return GroundedResult(
        result_id=result.result_id,
        label=result.label,
        entity_id=result.entity_id,
        relations=result.relations,
        score=result.score,
        evidence=tuple(
            GroundedEvidence(
                moment_id=evidence.moment_id,
                content_id=evidence.content_id,
                start_ms=evidence.start_ms,
                end_ms=evidence.end_ms,
                semantic_text=evidence.semantic_text,
            )
            for evidence in result.evidence
        ),
    )


def _serialize_result(result: FusedResult) -> dict[str, Any]:
    return {
        "result_id": result.result_id,
        "entity": (
            {"id": result.entity_id, "name": result.label}
            if result.entity_id is not None
            else None
        ),
        "label": result.label,
        "score": result.score,
        "relations": list(result.relations),
        "direct_answer_eligible": result.direct_answer_eligible,
        "evidence": [
            {
                "moment_id": evidence.moment_id,
                "content_id": evidence.content_id,
                "start_ms": evidence.start_ms,
                "end_ms": evidence.end_ms,
                "semantic_text": evidence.semantic_text,
            }
            for evidence in result.evidence
        ],
    }


def _branch_warnings(bundle: RetrievalBundle) -> list[str]:
    warnings: list[str] = []
    for outcome in (bundle.graph, bundle.vector):
        if outcome.status != "success":
            warnings.append(f"{outcome.name}_{outcome.status}")
    return warnings
