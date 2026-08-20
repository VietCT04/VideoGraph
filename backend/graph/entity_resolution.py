"""Deterministic, reversible cross-video entity resolution."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Protocol

from .model import EvidenceRef, GraphEntity
from .repository import InMemoryGraphRepository


_STOPWORDS = {"a", "an", "and", "for", "my", "the", "this", "that"}


def normalize_entity_name(name: str) -> str:
    """Normalize spelling and harmless determiners without changing evidence."""

    normalized = unicodedata.normalize("NFKC", name).casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    tokens = [token for token in normalized.split() if token not in _STOPWORDS]
    return " ".join(tokens)


@dataclass(frozen=True)
class EntityCandidate:
    candidate_id: str
    creator_id: str
    entity_type: str
    name: str
    external_id: str | None = None
    brand: str | None = None
    category: str | None = None
    semantic_similarity: float | None = None
    visual_similarity: float | None = None
    evidence: tuple[EvidenceRef, ...] = ()
    context_names: tuple[str, ...] = ()

    @property
    def normalized_name(self) -> str:
        return normalize_entity_name(self.name)


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    score: float
    reasons: tuple[str, ...]


@dataclass
class ResolutionDecision:
    decision_id: str
    action: str
    candidate_id: str
    canonical_id: str | None
    score: float
    aliases: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]
    reversible: bool = True
    status: str = "active"


class CandidateScorer(Protocol):
    def score(self, candidate: EntityCandidate, existing: GraphEntity) -> CandidateScore:
        ...


class DeterministicCandidateScorer:
    """Weighted scorer whose output is stable for a fixed configuration."""

    def score(self, candidate: EntityCandidate, existing: GraphEntity) -> CandidateScore:
        if candidate.entity_type != existing.entity_type or candidate.creator_id != existing.creator_id:
            return CandidateScore(candidate.candidate_id, 0.0, ("creator_or_type_mismatch",))

        score = 0.0
        reasons: list[str] = []
        normalized_existing = normalize_entity_name(existing.name)
        if candidate.external_id and existing.properties.get("external_id") == candidate.external_id:
            score = 1.0
            reasons.append("exact_external_id")
        else:
            if candidate.normalized_name == normalized_existing:
                score += 0.72
                reasons.append("normalized_name")
            else:
                ratio = SequenceMatcher(None, candidate.normalized_name, normalized_existing).ratio()
                score += 0.46 * ratio
                if ratio >= 0.8:
                    reasons.append("similar_name")

            existing_brand = existing.properties.get("brand")
            if candidate.brand and existing_brand:
                if normalize_entity_name(candidate.brand) == normalize_entity_name(str(existing_brand)):
                    score += 0.12
                    reasons.append("brand_match")
                else:
                    score -= 0.18
                    reasons.append("brand_mismatch")

            existing_category = existing.properties.get("category")
            if candidate.category and existing_category:
                if normalize_entity_name(candidate.category) == normalize_entity_name(str(existing_category)):
                    score += 0.08
                    reasons.append("category_match")
                else:
                    score -= 0.1
                    reasons.append("category_mismatch")

            if candidate.semantic_similarity is not None:
                score += 0.06 * max(0.0, min(1.0, candidate.semantic_similarity))
                reasons.append("semantic_similarity")
            if candidate.visual_similarity is not None:
                score += 0.04 * max(0.0, min(1.0, candidate.visual_similarity))
                reasons.append("visual_similarity")
            if any(normalize_entity_name(alias) == normalized_existing for alias in candidate.context_names):
                score += 0.06
                reasons.append("creator_history_context")

        return CandidateScore(candidate.candidate_id, max(0.0, min(1.0, score)), tuple(reasons))


class EntityResolver:
    """Resolve candidates while keeping ambiguous links and merge decisions reversible."""

    def __init__(
        self,
        repository: InMemoryGraphRepository,
        scorer: CandidateScorer | None = None,
        merge_threshold: float = 0.9,
        ambiguous_threshold: float = 0.6,
    ) -> None:
        if not 0 < ambiguous_threshold < merge_threshold <= 1:
            raise ValueError("thresholds must satisfy 0 < ambiguous < merge <= 1")
        self.repository = repository
        self.scorer = scorer or DeterministicCandidateScorer()
        self.merge_threshold = merge_threshold
        self.ambiguous_threshold = ambiguous_threshold
        self.decisions: dict[str, ResolutionDecision] = {}

    def resolve(self, candidate: EntityCandidate) -> ResolutionDecision:
        existing = self.repository.entities_for_creator(candidate.creator_id, ("public", "creator_only"))
        scores = sorted(
            (self.scorer.score(candidate, entity) for entity in existing),
            key=lambda item: (-item.score, item.candidate_id),
        )
        best = scores[0] if scores else None
        decision_id = _decision_id(candidate.candidate_id, best.candidate_id if best else "none")
        if best is not None and best.score >= self.merge_threshold:
            entity = self.repository.entities[best.candidate_id]
            entity.aliases.add(candidate.name)
            entity.evidence = _merge_evidence(entity.evidence, candidate.evidence)
            entity.properties.update({"external_id": candidate.external_id} if candidate.external_id else {})
            decision = ResolutionDecision(
                decision_id, "merge", candidate.candidate_id, entity.id, best.score,
                (candidate.name,), candidate.evidence,
            )
        elif best is not None and best.score >= self.ambiguous_threshold:
            decision = ResolutionDecision(
                decision_id, "link", candidate.candidate_id, best.candidate_id, best.score,
                (candidate.name,), candidate.evidence,
            )
        else:
            canonical_id = _new_canonical_id(candidate)
            entity = GraphEntity(
                id=canonical_id,
                creator_id=candidate.creator_id,
                entity_type=candidate.entity_type,
                name=candidate.name,
                aliases={candidate.name},
                evidence=list(candidate.evidence),
                properties={"external_id": candidate.external_id} if candidate.external_id else {},
            )
            self.repository.upsert_entity(entity)
            decision = ResolutionDecision(
                decision_id, "create", candidate.candidate_id, canonical_id, best.score if best else 0.0,
                (), candidate.evidence,
            )
        self.decisions[decision_id] = decision
        return decision

    def revert(self, decision_id: str) -> ResolutionDecision:
        decision = self.decisions[decision_id]
        if not decision.reversible or decision.status == "reverted":
            raise ValueError("resolution decision is not reversible")
        if decision.action == "merge" and decision.canonical_id in self.repository.entities:
            entity = self.repository.entities[decision.canonical_id]
            entity.aliases.discard(decision.aliases[0])
            entity.evidence = [item for item in entity.evidence if item not in decision.evidence]
        elif decision.action == "create" and decision.canonical_id:
            self.repository.entities.pop(decision.canonical_id, None)
        decision.status = "reverted"
        return decision

    def active_decisions(self) -> tuple[ResolutionDecision, ...]:
        return tuple(sorted((item for item in self.decisions.values() if item.status == "active"), key=lambda item: item.decision_id))


def _decision_id(candidate_id: str, existing_id: str) -> str:
    return "resolution_" + hashlib.sha256(f"{candidate_id}|{existing_id}".encode()).hexdigest()[:16]


def _new_canonical_id(candidate: EntityCandidate) -> str:
    digest = hashlib.sha256(f"{candidate.creator_id}|{candidate.entity_type}|{candidate.normalized_name}".encode()).hexdigest()[:16]
    return f"entity_{candidate.creator_id}_{candidate.entity_type.casefold()}_{digest}"


def _merge_evidence(current: Iterable[EvidenceRef], incoming: Iterable[EvidenceRef]) -> list[EvidenceRef]:
    result: list[EvidenceRef] = []
    seen: set[tuple] = set()
    for item in (*tuple(current), *tuple(incoming)):
        key = (item.moment_id, item.content_id, item.start_ms, item.end_ms, item.evidence_refs)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result

