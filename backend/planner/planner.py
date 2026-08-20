"""Creator-scoped retrieval planning with validation, fallback, and timing."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from contracts.validation import ContractValidationError, validate_retrieval_plan

from .parser import CreatorQuery, parse_creator_query
from .provider import FixturePlannerProvider, PlannerProvider


@dataclass(frozen=True)
class PlannerResult:
    query: CreatorQuery
    plan: dict[str, object]
    used_fallback: bool
    latency_ms: float
    provider_error: str | None = None


def build_fallback_plan(query: CreatorQuery, creator_id: str) -> dict[str, object]:
    """Produce a safe, broad plan when a provider fails or emits invalid JSON."""

    text = query.question.casefold()
    relations: list[str] = []
    if any(word in text for word in ("recommend", "suggest")):
        relations.append("RECOMMENDS")
    elif any(word in text for word in ("use", "uses", "used", "wear", "wears")):
        relations.append("USES")
    entity_types = ["Product"] if any(word in text for word in ("product", "lipstick", "foundation", "makeup")) else []
    return {
        "schema_version": "1.0",
        "creator_id": creator_id,
        "intent": "find_recommendation" if relations == ["RECOMMENDS"] else "semantic_memory_search",
        "graph": {"relations": relations, "entity_types": entity_types, "filters": {}},
        "semantic_query": query.question,
        "time_range": None,
        "result_type": "Entity" if relations or entity_types else "Moment",
        "top_k": 10,
    }


class RetrievalPlanner:
    """Resolve creator scope before accepting any provider-produced plan."""

    def __init__(
        self,
        creator_resolver: Mapping[str, str] | Callable[[str], str],
        provider: PlannerProvider | None = None,
    ) -> None:
        self.creator_resolver = creator_resolver
        self.provider = provider or FixturePlannerProvider()

    def plan(self, raw_query: str) -> PlannerResult:
        started = time.perf_counter()
        query = parse_creator_query(raw_query)
        creator_id = self._resolve_creator(query.handle)
        provider_error: str | None = None
        used_fallback = False
        try:
            candidate = self.provider.plan(query, creator_id)
            plan = validate_retrieval_plan(candidate)
        except (ContractValidationError, ValueError, TypeError, KeyError) as error:
            provider_error = str(error)
            used_fallback = True
            plan = validate_retrieval_plan(build_fallback_plan(query, creator_id))
        latency_ms = (time.perf_counter() - started) * 1000
        return PlannerResult(query, plan, used_fallback, round(latency_ms, 3), provider_error)

    def _resolve_creator(self, handle: str) -> str:
        if isinstance(self.creator_resolver, Mapping):
            creator_id = self.creator_resolver.get(handle)
        else:
            creator_id = self.creator_resolver(handle)
        if not isinstance(creator_id, str) or not creator_id.strip():
            raise ValueError(f"unknown creator handle @{handle}")
        return creator_id

