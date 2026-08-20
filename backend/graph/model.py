"""Small canonical graph value objects used by Neo4j and fixture adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VISIBILITIES = ("public", "creator_only", "hidden", "excluded")


@dataclass(frozen=True)
class EvidenceRef:
    """A viewer-facing reference back to one canonical Moment."""

    moment_id: str
    content_id: str
    start_ms: int
    end_ms: int
    evidence_refs: tuple[str, ...] = ()


@dataclass
class GraphEntity:
    id: str
    creator_id: str
    entity_type: str
    name: str
    aliases: set[str] = field(default_factory=set)
    visibility: str = "public"
    evidence: list[EvidenceRef] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphMoment:
    id: str
    creator_id: str
    content_id: str
    start_ms: int
    end_ms: int
    semantic_text: str
    transcript: str | None = None
    visibility: str = "public"
    evidence: dict[str, tuple[Any, ...]] = field(default_factory=dict)
    entity_ids: set[str] = field(default_factory=set)


@dataclass
class GraphRelation:
    id: str
    creator_id: str
    subject_id: str
    predicate: str
    object_id: str
    confidence: float
    visibility: str = "public"
    evidence: list[EvidenceRef] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphContent:
    id: str
    creator_id: str
    title: str | None = None
    source_type: str | None = None
    duration_ms: int | None = None
    visibility: str = "public"


@dataclass
class GraphSnapshot:
    contents: dict[str, GraphContent]
    moments: dict[str, GraphMoment]
    entities: dict[str, GraphEntity]
    relations: dict[str, GraphRelation]

