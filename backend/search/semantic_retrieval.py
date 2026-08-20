"""Creator-scoped semantic Moment retrieval over the vector repository boundary."""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from contracts.validation import ContractValidationError, validate_retrieval_plan

from backend.graph.ingestion import canonical_moment_id
from backend.search.embeddings import EmbeddingProvider
from backend.search.vector_repository import InMemoryVectorRepository, MomentEmbeddingRow, VectorRepository, VectorSearchFilters


@dataclass(frozen=True)
class SemanticHit:
    result_id: str
    moment_id: str
    creator_id: str
    content_id: str
    start_ms: int
    end_ms: int
    semantic_text: str
    similarity: float
    visibility: str
    embedding_model: str
    embedding_version: str | None


@dataclass(frozen=True)
class SemanticSearchResult:
    hits: tuple[SemanticHit, ...]
    latency_ms: float
    query_model: str
    query_version: str


class SemanticMomentRetriever:
    """Embed only validated planner text and search a scoped repository."""

    def __init__(self, repository: VectorRepository, embedder: EmbeddingProvider) -> None:
        self.repository = repository
        self.embedder = embedder

    def search(self, plan: Mapping[str, Any], allowed_visibility: Iterable[str] = ("public",)) -> SemanticSearchResult:
        validated = _validate_plan(plan)
        started = time.perf_counter()
        query_embedding = self.embedder.embed(validated["semantic_query"])
        filters = validated["graph"].get("filters", {})
        time_range = validated.get("time_range")
        search_filters = VectorSearchFilters(
            creator_id=validated["creator_id"],
            content_id=filters.get("content_id"),
            start_ms=time_range.get("start_ms") if time_range else None,
            end_ms=time_range.get("end_ms") if time_range else None,
            allowed_visibility=tuple(allowed_visibility),
        )
        rows = self.repository.search(query_embedding, search_filters, validated["top_k"])
        hits = tuple(_to_hit(row, similarity) for row, similarity in rows)
        return SemanticSearchResult(
            hits=hits,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            query_model=self.embedder.model,
            query_version=self.embedder.version,
        )


def index_extraction_fixture(
    repository: InMemoryVectorRepository,
    payload: Mapping[str, Any],
    embedder: EmbeddingProvider,
    visibility: str = "public",
) -> int:
    """Index contract fixture Moments using the graph's canonical Moment ID."""

    if not isinstance(payload.get("content_id"), str) or not isinstance(payload.get("creator_id"), str):
        raise ValueError("fixture must include content_id and creator_id")
    count = 0
    for moment in payload.get("moments", ()):
        source_embedding = moment.get("embedding") or {}
        row = MomentEmbeddingRow(
            moment_id=canonical_moment_id(payload["content_id"], moment["start_ms"], moment["end_ms"]),
            creator_id=payload["creator_id"],
            content_id=payload["content_id"],
            start_ms=moment["start_ms"],
            end_ms=moment["end_ms"],
            semantic_text=moment["semantic_text"],
            embedding=tuple(source_embedding.get("vector", ())) or embedder.embed(moment["semantic_text"]),
            embedding_model=embedder.model,
            embedding_version=embedder.version,
            visibility=visibility,
        )
        repository.upsert(row)
        count += 1
    return count


def _validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_retrieval_plan(plan)
    except ContractValidationError as error:
        raise ValueError(str(error)) from error


def _to_hit(row: MomentEmbeddingRow, similarity: float) -> SemanticHit:
    return SemanticHit(
        result_id=row.moment_id,
        moment_id=row.moment_id,
        creator_id=row.creator_id,
        content_id=row.content_id,
        start_ms=row.start_ms,
        end_ms=row.end_ms,
        semantic_text=row.semantic_text,
        similarity=similarity,
        visibility=row.visibility,
        embedding_model=row.embedding_model,
        embedding_version=row.embedding_version,
    )

