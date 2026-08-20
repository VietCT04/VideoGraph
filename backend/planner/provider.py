"""Planner provider boundary and a model-free fixture implementation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from contracts.ontology import ENTITY_TYPES, RELATION_TYPES

from .parser import CreatorQuery


PLANNER_SYSTEM_PROMPT = f"""You are a VideoGraph retrieval planner.
Return only a JSON object matching contracts/retrieval-plan.schema.json.
The graph field is structured intent, never executable Cypher. Keep creator_id supplied
by the backend. Allowed entity types: {', '.join(ENTITY_TYPES)}.
Allowed relation predicates: {', '.join(RELATION_TYPES)}.
Unknown properties, predicates, and entity types are invalid and must be omitted.
Separate graph constraints from the natural-language semantic_query."""


class PlannerProvider(Protocol):
    def plan(self, query: CreatorQuery, creator_id: str) -> Mapping[str, object]:
        ...


class FixturePlannerProvider:
    """Predictable provider used until a real constrained model adapter is available."""

    def plan(self, query: CreatorQuery, creator_id: str) -> Mapping[str, object]:
        text = query.question.casefold()
        relations: list[str] = []
        if any(word in text for word in ("recommend", "suggest")):
            relations.append("RECOMMENDS")
        if any(word in text for word in ("use", "uses", "used", "wear", "wears")):
            relations.append("USES")
        if any(word in text for word in ("like", "likes", "favorite", "favourite")):
            relations.append("LIKES")
        if any(word in text for word in ("compare", "difference", "versus", " vs ")):
            relations.append("COMPARES")
        entity_types = ["Product"] if any(word in text for word in ("product", "lipstick", "foundation", "makeup")) else []
        intent = "find_recommendation" if "RECOMMENDS" in relations else "semantic_memory_search"
        result_type = "Entity" if relations or entity_types else "Moment"
        return {
            "schema_version": "1.0",
            "creator_id": creator_id,
            "intent": intent,
            "graph": {"relations": relations, "entity_types": entity_types, "filters": {}},
            "semantic_query": query.question,
            "time_range": None,
            "result_type": result_type,
            "top_k": 10,
        }

