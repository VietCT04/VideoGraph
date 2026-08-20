"""Map validated extraction payloads to stable canonical graph records."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from contracts.validation import validate_extraction

from .model import EvidenceRef, GraphContent, GraphEntity, GraphMoment, GraphRelation
from .repository import GraphRepository


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "value"


def canonical_moment_id(content_id: str, start_ms: int, end_ms: int) -> str:
    """Build the stable backend ID shared by Neo4j and pgvector."""

    return f"moment_{_slug(content_id)}_{start_ms}_{end_ms}"


def canonical_entity_id(creator_id: str, entity_type: str, normalized_name: str) -> str:
    """Build a deterministic ID without trusting a content-local entity ID."""

    digest = hashlib.sha256(f"{creator_id}|{entity_type}|{normalized_name}".encode()).hexdigest()[:16]
    return f"entity_{_slug(creator_id)}_{entity_type.casefold()}_{digest}"


class ExtractionGraphIngestor:
    """Idempotently persist one extraction payload and preserve evidence links."""

    def __init__(self, repository: GraphRepository) -> None:
        self.repository = repository

    def ingest(self, payload: object, visibility: str = "public") -> list[GraphMoment]:
        extraction = validate_extraction(payload)
        content_id = extraction["content_id"]
        creator_id = extraction["creator_id"]
        metadata = extraction.get("content_metadata") or {}
        self.repository.upsert_content(
            GraphContent(
                id=content_id,
                creator_id=creator_id,
                title=metadata.get("title"),
                source_type=metadata.get("source_type"),
                duration_ms=metadata.get("duration_ms"),
                visibility=visibility,
            )
        )

        moments: list[GraphMoment] = []
        for raw_moment in extraction["moments"]:
            moment_id = canonical_moment_id(content_id, raw_moment["start_ms"], raw_moment["end_ms"])
            evidence = {
                key: tuple(values) for key, values in (raw_moment.get("evidence") or {}).items()
            }
            moment = GraphMoment(
                id=moment_id,
                creator_id=creator_id,
                content_id=content_id,
                start_ms=raw_moment["start_ms"],
                end_ms=raw_moment["end_ms"],
                semantic_text=raw_moment["semantic_text"],
                transcript=raw_moment.get("transcript"),
                visibility=visibility,
                evidence=evidence,
            )
            self.repository.upsert_moment(moment)
            moments.append(moment)
            entity_ids = self._ingest_entities(extraction, raw_moment, moment)
            moment.entity_ids.update(entity_ids.values())
            self.repository.upsert_moment(moment)
            self._ingest_relations(extraction, raw_moment, moment, entity_ids)
        return moments

    def _ingest_entities(self, extraction: dict[str, Any], raw_moment: dict[str, Any], moment: GraphMoment) -> dict[str, str]:
        entity_ids: dict[str, str] = {}
        for raw_entity in raw_moment["entities"]:
            normalized_name = " ".join(raw_entity["name"].casefold().split())
            entity_id = canonical_entity_id(extraction["creator_id"], raw_entity["type"], normalized_name)
            evidence = EvidenceRef(
                moment_id=moment.id,
                content_id=moment.content_id,
                start_ms=moment.start_ms,
                end_ms=moment.end_ms,
                evidence_refs=tuple(raw_entity.get("evidence_refs", ())),
            )
            self.repository.upsert_entity(
                GraphEntity(
                    id=entity_id,
                    creator_id=extraction["creator_id"],
                    entity_type=raw_entity["type"],
                    name=raw_entity["name"],
                    aliases={raw_entity["name"]},
                    visibility=moment.visibility,
                    evidence=[evidence],
                    properties={"confidence": raw_entity["confidence"], "local_id": raw_entity["local_id"]},
                )
            )
            entity_ids[raw_entity["local_id"]] = entity_id
        return entity_ids

    def _ingest_relations(
        self,
        extraction: dict[str, Any],
        raw_moment: dict[str, Any],
        moment: GraphMoment,
        entity_ids: dict[str, str],
    ) -> None:
        creator_node_id = f"creator_{_slug(extraction['creator_id'])}"
        for raw_relation in raw_moment["relations"]:
            subject_id = creator_node_id if raw_relation["subject"] == "creator" else entity_ids[raw_relation["subject"]]
            object_id = creator_node_id if raw_relation["object"] == "creator" else entity_ids[raw_relation["object"]]
            evidence = EvidenceRef(
                moment_id=moment.id,
                content_id=moment.content_id,
                start_ms=moment.start_ms,
                end_ms=moment.end_ms,
                evidence_refs=tuple(raw_relation["evidence_refs"]),
            )
            relation_key = f"{subject_id}|{raw_relation['predicate']}|{object_id}"
            relation_id = "relation_" + hashlib.sha256(relation_key.encode()).hexdigest()[:16]
            self.repository.upsert_relation(
                GraphRelation(
                    id=relation_id,
                    creator_id=extraction["creator_id"],
                    subject_id=subject_id,
                    predicate=raw_relation["predicate"],
                    object_id=object_id,
                    confidence=raw_relation["confidence"],
                    visibility=moment.visibility,
                    evidence=[evidence],
                    properties={"explicit": raw_relation.get("explicit", False)},
                )
            )

