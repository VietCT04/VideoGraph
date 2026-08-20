"""Safe graph retrieval tools backed by allowlisted parameterized Cypher templates."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from contracts.ontology import ENTITY_TYPES, RELATION_TYPES
from contracts.validation import ContractValidationError, validate_retrieval_plan

from .model import EvidenceRef, GraphEntity, GraphRelation
from .repository import InMemoryGraphRepository


@dataclass(frozen=True)
class ParameterizedCypher:
    text: str
    params: Mapping[str, Any]


@dataclass(frozen=True)
class GraphHit:
    result_id: str
    creator_id: str
    entity_id: str | None
    label: str
    entity_type: str | None
    relation: str | None
    confidence: float
    evidence: tuple[EvidenceRef, ...]


class GraphToolError(ValueError):
    """Raised when a plan cannot be mapped to a controlled graph tool."""


class SafeGraphQueryService:
    """Expose graph intent without accepting user/model-generated Cypher."""

    def __init__(
        self,
        repository: InMemoryGraphRepository,
        executor: Callable[[str, Mapping[str, Any]], Iterable[Mapping[str, Any]]] | None = None,
    ) -> None:
        self.repository = repository
        self.executor = executor

    def build_queries(self, plan: Mapping[str, Any], allowed_visibility: Iterable[str] = ("public",)) -> list[ParameterizedCypher]:
        validated = _validate_plan(plan)
        visibility = tuple(allowed_visibility)
        if not visibility:
            raise GraphToolError("at least one visibility value is required")
        relation_values = tuple(validated["graph"].get("relations", ())) or (None,)
        entity_values = tuple(validated["graph"].get("entity_types", ())) or (None,)
        filters = validated["graph"].get("filters", {})
        queries: list[ParameterizedCypher] = []
        for relation in relation_values:
            if relation not in RELATION_TEMPLATES and relation is not None:
                raise GraphToolError(f"unsupported relation {relation!r}")
            for entity_type in entity_values:
                if entity_type not in ENTITY_TEMPLATES and entity_type is not None:
                    raise GraphToolError(f"unsupported entity type {entity_type!r}")
                template = RELATION_TEMPLATES[relation][entity_type]
                params = {
                    "creator_id": validated["creator_id"],
                    "allowed_visibility": list(visibility),
                    "top_k": validated["top_k"],
                    "content_id": filters.get("content_id"),
                    "entity_name": filters.get("entity_name"),
                    "category": filters.get("category"),
                    "color": filters.get("color"),
                    "start_ms": (validated.get("time_range") or {}).get("start_ms"),
                    "end_ms": (validated.get("time_range") or {}).get("end_ms"),
                }
                queries.append(ParameterizedCypher(template, params))
        return queries

    def search(self, plan: Mapping[str, Any], allowed_visibility: Iterable[str] = ("public",)) -> list[GraphHit]:
        queries = self.build_queries(plan, allowed_visibility)
        if self.executor is not None:
            hits: list[GraphHit] = []
            for query in queries:
                hits.extend(_normalize_database_rows(self.executor(query.text, query.params), plan["creator_id"]))
            return _deduplicate_hits(hits)
        return self._fixture_search(plan, allowed_visibility)

    def get_creator_entities(self, creator_id: str, allowed_visibility: Iterable[str] = ("public",)) -> list[GraphEntity]:
        return self.repository.entities_for_creator(creator_id, allowed_visibility)

    def get_creator_relations(self, creator_id: str, allowed_visibility: Iterable[str] = ("public",)) -> list[GraphRelation]:
        return self.repository.relations_for_creator(creator_id, allowed_visibility)

    def get_entity_evidence(self, entity_id: str, creator_id: str, allowed_visibility: Iterable[str] = ("public",)) -> tuple[EvidenceRef, ...]:
        entity = self.repository.entities.get(entity_id)
        if entity is None or entity.creator_id != creator_id or entity.visibility not in set(allowed_visibility):
            return ()
        return tuple(entity.evidence)

    def _fixture_search(self, plan: Mapping[str, Any], allowed_visibility: Iterable[str]) -> list[GraphHit]:
        creator_id = plan["creator_id"]
        graph = plan["graph"]
        relations = set(graph.get("relations", ()))
        entity_types = set(graph.get("entity_types", ()))
        filters = graph.get("filters", {})
        time_range = plan.get("time_range")
        allowed = set(allowed_visibility)
        entities = self.repository.entities
        hits: list[GraphHit] = []
        for relation in self.repository.relations_for_creator(creator_id, allowed):
            if relations and relation.predicate not in relations:
                continue
            entity = entities.get(relation.object_id) or entities.get(relation.subject_id)
            if entity is None or entity.visibility not in allowed:
                continue
            if entity_types and entity.entity_type not in entity_types:
                continue
            if filters.get("entity_name") and str(filters["entity_name"]).casefold() not in entity.name.casefold():
                continue
            if filters.get("category") and entity.properties.get("category") != filters["category"]:
                continue
            evidence = tuple(_filter_evidence(relation.evidence, filters.get("content_id"), time_range))
            if not evidence:
                continue
            hits.append(
                GraphHit(
                    result_id=entity.id,
                    creator_id=creator_id,
                    entity_id=entity.id,
                    label=entity.name,
                    entity_type=entity.entity_type,
                    relation=relation.predicate,
                    confidence=relation.confidence,
                    evidence=evidence,
                )
            )
        return _deduplicate_hits(hits)[: plan["top_k"]]


def _validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_retrieval_plan(plan)
    except ContractValidationError as error:
        raise GraphToolError(str(error)) from error


def _filter_evidence(evidence: Iterable[EvidenceRef], content_id: str | None, time_range: Mapping[str, int] | None) -> Iterable[EvidenceRef]:
    for item in evidence:
        if content_id is not None and item.content_id != content_id:
            continue
        if time_range is not None and (item.end_ms <= time_range["start_ms"] or item.start_ms >= time_range["end_ms"]):
            continue
        yield item


def _normalize_database_rows(rows: Iterable[Mapping[str, Any]], creator_id: str) -> list[GraphHit]:
    hits: list[GraphHit] = []
    for row in rows:
        evidence = tuple(row.get("evidence", ()))
        hits.append(
            GraphHit(
                result_id=str(row["entity_id"]),
                creator_id=creator_id,
                entity_id=str(row["entity_id"]),
                label=str(row.get("label", row["entity_id"])),
                entity_type=row.get("entity_type"),
                relation=row.get("relation"),
                confidence=float(row.get("confidence", 0.0)),
                evidence=evidence,
            )
        )
    return hits


def _deduplicate_hits(hits: Iterable[GraphHit]) -> list[GraphHit]:
    merged: dict[str, GraphHit] = {}
    for hit in hits:
        current = merged.get(hit.result_id)
        if current is None:
            merged[hit.result_id] = hit
            continue
        evidence = list(current.evidence)
        for item in hit.evidence:
            if item not in evidence:
                evidence.append(item)
        merged[hit.result_id] = GraphHit(
            result_id=current.result_id,
            creator_id=current.creator_id,
            entity_id=current.entity_id,
            label=current.label,
            entity_type=current.entity_type,
            relation=current.relation or hit.relation,
            confidence=max(current.confidence, hit.confidence),
            evidence=tuple(sorted(evidence, key=lambda item: (item.content_id, item.start_ms, item.moment_id))),
        )
    return sorted(merged.values(), key=lambda hit: (-hit.confidence, hit.result_id))


def _template(relation: str | None, entity_type: str | None) -> str:
    relation_match = f"-[r:{relation}]->" if relation else "-[r]->"
    entity_label = f":{entity_type}" if entity_type else ":Entity"
    return f"""
        MATCH (c:Creator {{id: $creator_id}}){relation_match}(entity{entity_label})
        MATCH (assertion:RelationAssertion {{creator_id: $creator_id}})
        WHERE assertion.predicate = type(r)
          AND entity.creator_id = $creator_id
          AND entity.visibility IN $allowed_visibility
          AND ($entity_name IS NULL OR toLower(entity.name) CONTAINS toLower($entity_name))
          AND ($category IS NULL OR entity.category = $category)
          AND ($color IS NULL OR entity.color = $color)
          AND ($content_id IS NULL OR assertion.content_id = $content_id)
          AND ($start_ms IS NULL OR assertion.end_ms > $start_ms)
          AND ($end_ms IS NULL OR assertion.start_ms < $end_ms)
        RETURN entity.id AS entity_id, entity.name AS label, entity.entity_type AS entity_type,
               type(r) AS relation, assertion.confidence AS confidence,
               assertion.moment_id AS moment_id, assertion.content_id AS content_id,
               assertion.start_ms AS start_ms, assertion.end_ms AS end_ms
        LIMIT $top_k
    """.strip()


RELATION_TEMPLATES: dict[str | None, dict[str | None, str]] = {
    relation: {entity_type: _template(relation, entity_type) for entity_type in (None, *ENTITY_TYPES)}
    for relation in (None, *RELATION_TYPES)
}
ENTITY_TEMPLATES = {entity_type: _template(None, entity_type) for entity_type in (None, *ENTITY_TYPES)}

