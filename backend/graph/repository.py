"""Graph repository contracts and a deterministic fixture-backed implementation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from .model import GraphContent, GraphEntity, GraphMoment, GraphRelation, GraphSnapshot, VISIBILITIES


class GraphRepository:
    """Minimal persistence surface needed by ingestion and safe graph tools."""

    def upsert_content(self, content: GraphContent) -> GraphContent:
        raise NotImplementedError

    def upsert_moment(self, moment: GraphMoment) -> GraphMoment:
        raise NotImplementedError

    def upsert_entity(self, entity: GraphEntity) -> GraphEntity:
        raise NotImplementedError

    def upsert_relation(self, relation: GraphRelation) -> GraphRelation:
        raise NotImplementedError

    def snapshot(self) -> GraphSnapshot:
        raise NotImplementedError

    def set_visibility(self, content_id: str, visibility: str) -> None:
        raise NotImplementedError

    def delete_content(self, content_id: str) -> None:
        raise NotImplementedError


class InMemoryGraphRepository(GraphRepository):
    """Idempotent graph store for fixtures and local service development."""

    def __init__(self) -> None:
        self.contents: dict[str, GraphContent] = {}
        self.moments: dict[str, GraphMoment] = {}
        self.entities: dict[str, GraphEntity] = {}
        self.relations: dict[str, GraphRelation] = {}

    def upsert_content(self, content: GraphContent) -> GraphContent:
        _check_visibility(content.visibility)
        current = self.contents.get(content.id)
        if current is None:
            self.contents[content.id] = content
        else:
            self.contents[content.id] = replace(
                current,
                title=content.title or current.title,
                source_type=content.source_type or current.source_type,
                duration_ms=content.duration_ms if content.duration_ms is not None else current.duration_ms,
                visibility=content.visibility,
            )
        return self.contents[content.id]

    def upsert_moment(self, moment: GraphMoment) -> GraphMoment:
        _check_visibility(moment.visibility)
        current = self.moments.get(moment.id)
        if current is None:
            self.moments[moment.id] = moment
        else:
            current.semantic_text = moment.semantic_text
            current.transcript = moment.transcript or current.transcript
            current.end_ms = moment.end_ms
            current.visibility = moment.visibility
            current.entity_ids.update(moment.entity_ids)
            current.evidence = _merge_evidence(current.evidence, moment.evidence)
        return self.moments[moment.id]

    def upsert_entity(self, entity: GraphEntity) -> GraphEntity:
        _check_visibility(entity.visibility)
        current = self.entities.get(entity.id)
        if current is None:
            self.entities[entity.id] = entity
        else:
            current.aliases.update(entity.aliases)
            if entity.name:
                current.name = entity.name
            current.visibility = entity.visibility
            current.evidence = _merge_evidence_refs(current.evidence, entity.evidence)
            current.properties.update(entity.properties)
        return self.entities[entity.id]

    def upsert_relation(self, relation: GraphRelation) -> GraphRelation:
        _check_visibility(relation.visibility)
        current = self.relations.get(relation.id)
        if current is None:
            self.relations[relation.id] = relation
        else:
            current.confidence = max(current.confidence, relation.confidence)
            current.visibility = relation.visibility
            current.evidence = _merge_evidence_refs(current.evidence, relation.evidence)
            current.properties.update(relation.properties)
        return self.relations[relation.id]

    def get_moment(self, moment_id: str) -> GraphMoment | None:
        return self.moments.get(moment_id)

    def entities_for_creator(self, creator_id: str, allowed_visibility: Iterable[str] = ("public",)) -> list[GraphEntity]:
        allowed = _visibility_set(allowed_visibility)
        return sorted(
            (entity for entity in self.entities.values() if entity.creator_id == creator_id and entity.visibility in allowed),
            key=lambda entity: entity.id,
        )

    def relations_for_creator(self, creator_id: str, allowed_visibility: Iterable[str] = ("public",)) -> list[GraphRelation]:
        allowed = _visibility_set(allowed_visibility)
        return sorted(
            (relation for relation in self.relations.values() if relation.creator_id == creator_id and relation.visibility in allowed),
            key=lambda relation: relation.id,
        )

    def moments_for_creator(self, creator_id: str, allowed_visibility: Iterable[str] = ("public",)) -> list[GraphMoment]:
        allowed = _visibility_set(allowed_visibility)
        return sorted(
            (moment for moment in self.moments.values() if moment.creator_id == creator_id and moment.visibility in allowed),
            key=lambda moment: (moment.start_ms, moment.id),
        )

    def set_visibility(self, content_id: str, visibility: str) -> None:
        _check_visibility(visibility)
        if content_id in self.contents:
            self.contents[content_id].visibility = visibility
        for moment in self.moments.values():
            if moment.content_id == content_id:
                moment.visibility = visibility
        for entity in self.entities.values():
            entity.evidence = [evidence for evidence in entity.evidence if evidence.content_id != content_id]
        for relation in self.relations.values():
            relation.evidence = [evidence for evidence in relation.evidence if evidence.content_id != content_id]

    def snapshot(self) -> GraphSnapshot:
        return GraphSnapshot(self.contents, self.moments, self.entities, self.relations)

    def delete_content(self, content_id: str) -> None:
        moment_ids = {moment.id for moment in self.moments.values() if moment.content_id == content_id}
        self.contents.pop(content_id, None)
        for moment_id in moment_ids:
            self.moments.pop(moment_id, None)
        for entity in self.entities.values():
            entity.evidence = [evidence for evidence in entity.evidence if evidence.moment_id not in moment_ids]
        for relation_id, relation in list(self.relations.items()):
            relation.evidence = [evidence for evidence in relation.evidence if evidence.moment_id not in moment_ids]
            if not relation.evidence:
                del self.relations[relation_id]


def _merge_evidence(current: dict[str, tuple[object, ...]], incoming: dict[str, tuple[object, ...]]) -> dict[str, tuple[object, ...]]:
    merged = dict(current)
    for key, values in incoming.items():
        merged[key] = tuple(dict.fromkeys((*merged.get(key, ()), *values)))
    return merged


def _merge_evidence_refs(current: list, incoming: list) -> list:
    existing = {(item.moment_id, item.content_id, item.start_ms, item.end_ms, item.evidence_refs) for item in current}
    result = list(current)
    for item in incoming:
        key = (item.moment_id, item.content_id, item.start_ms, item.end_ms, item.evidence_refs)
        if key not in existing:
            result.append(item)
            existing.add(key)
    return result


def _visibility_set(values: Iterable[str]) -> set[str]:
    allowed = set(values)
    if not allowed or not allowed.issubset(VISIBILITIES):
        raise ValueError(f"visibility must be a non-empty subset of {VISIBILITIES}")
    return allowed


def _check_visibility(value: str) -> None:
    if value not in VISIBILITIES:
        raise ValueError(f"unknown visibility {value!r}")

