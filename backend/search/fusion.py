"""Deterministic evidence-preserving graph/vector fusion and reranking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .orchestrator import RetrievalBundle


@dataclass(frozen=True)
class FusionEvidence:
    moment_id: str
    content_id: str
    start_ms: int
    end_ms: int
    semantic_text: str | None = None


@dataclass
class _Accumulator:
    result_id: str
    label: str
    entity_id: str | None = None
    entity_type: str | None = None
    graph_score: float = 0.0
    vector_score: float = 0.0
    relations: set[str] = field(default_factory=set)
    evidence: dict[str, FusionEvidence] = field(default_factory=dict)


@dataclass(frozen=True)
class FusedResult:
    result_id: str
    label: str
    entity_id: str | None
    entity_type: str | None
    score: float
    graph_score: float
    vector_score: float
    relations: tuple[str, ...]
    evidence: tuple[FusionEvidence, ...]
    direct_answer_eligible: bool


@dataclass(frozen=True)
class FusionResultSet:
    results: tuple[FusedResult, ...]
    latency_ms: float
    direct_answer_eligible: bool


class ResultFusionService:
    """Fuse canonical graph/vector IDs before any optional answer synthesis."""

    def fuse(self, bundle: RetrievalBundle) -> FusionResultSet:
        started = time.perf_counter()
        accumulators: dict[str, _Accumulator] = {}
        moment_to_key: dict[str, str] = {}

        for graph_hit in bundle.graph.results:
            key = str(getattr(graph_hit, "entity_id", None) or getattr(graph_hit, "result_id"))
            accumulator = accumulators.setdefault(
                key,
                _Accumulator(
                    result_id=key,
                    label=str(getattr(graph_hit, "label", key)),
                    entity_id=getattr(graph_hit, "entity_id", None),
                    entity_type=getattr(graph_hit, "entity_type", None),
                ),
            )
            accumulator.graph_score = max(accumulator.graph_score, _bounded_score(getattr(graph_hit, "confidence", 0.0)))
            relation = getattr(graph_hit, "relation", None)
            if relation:
                accumulator.relations.add(str(relation))
            for evidence in getattr(graph_hit, "evidence", ()):
                fusion_evidence = FusionEvidence(
                    moment_id=evidence.moment_id,
                    content_id=evidence.content_id,
                    start_ms=evidence.start_ms,
                    end_ms=evidence.end_ms,
                )
                accumulator.evidence[evidence.moment_id] = fusion_evidence
                moment_to_key[evidence.moment_id] = key

        for vector_hit in bundle.vector.results:
            moment_id = str(getattr(vector_hit, "moment_id"))
            key = moment_to_key.get(moment_id, f"moment:{moment_id}")
            accumulator = accumulators.setdefault(
                key,
                _Accumulator(result_id=key, label=str(getattr(vector_hit, "semantic_text", key))),
            )
            accumulator.vector_score = max(accumulator.vector_score, _bounded_score(getattr(vector_hit, "similarity", 0.0)))
            if accumulator.label.startswith("moment:") or accumulator.label == key:
                accumulator.label = str(getattr(vector_hit, "semantic_text", key))
            accumulator.evidence[moment_id] = FusionEvidence(
                moment_id=moment_id,
                content_id=str(getattr(vector_hit, "content_id")),
                start_ms=int(getattr(vector_hit, "start_ms")),
                end_ms=int(getattr(vector_hit, "end_ms")),
                semantic_text=str(getattr(vector_hit, "semantic_text")),
            )

        results = tuple(
            sorted(
                (_to_result(item, bundle) for item in accumulators.values()),
                key=lambda result: (-result.score, result.result_id),
            )[: bundle.plan["top_k"]]
        )
        return FusionResultSet(
            results=results,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            direct_answer_eligible=bool(results and results[0].direct_answer_eligible),
        )


def _to_result(accumulator: _Accumulator, bundle: RetrievalBundle) -> FusedResult:
    evidence = tuple(sorted(accumulator.evidence.values(), key=lambda item: (item.content_id, item.start_ms, item.moment_id)))
    graph_signal = accumulator.graph_score
    vector_signal = accumulator.vector_score
    relation_boost = 0.12 if accumulator.relations else 0.0
    evidence_signal = min(0.1, len(evidence) * 0.05)
    if graph_signal and vector_signal:
        score = 0.5 * graph_signal + 0.35 * vector_signal + relation_boost + evidence_signal
    elif graph_signal:
        score = 0.8 * graph_signal + relation_boost + evidence_signal
    else:
        score = 0.9 * vector_signal + evidence_signal
    score = min(1.0, score)
    direct = (
        not bundle.partial_success
        and accumulator.graph_score >= 0.75
        and bool(accumulator.relations)
        and bool(evidence)
        and bundle.plan["result_type"] in {"Entity", "Relation"}
    )
    return FusedResult(
        result_id=accumulator.result_id,
        label=accumulator.label,
        entity_id=accumulator.entity_id,
        entity_type=accumulator.entity_type,
        score=round(score, 6),
        graph_score=round(graph_signal, 6),
        vector_score=round(vector_signal, 6),
        relations=tuple(sorted(accumulator.relations)),
        evidence=evidence,
        direct_answer_eligible=direct,
    )


def _bounded_score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0

