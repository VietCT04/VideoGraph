"""Concurrent graph/vector retrieval with bounded branch failures."""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from contracts.validation import ContractValidationError, validate_retrieval_plan


@dataclass(frozen=True)
class BranchOutcome:
    name: str
    status: str
    results: tuple[Any, ...]
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True)
class RetrievalBundle:
    plan: dict[str, Any]
    graph: BranchOutcome
    vector: BranchOutcome
    partial_success: bool
    total_latency_ms: float


class HybridRetrievalOrchestrator:
    """Run both retrieval branches concurrently and preserve partial results."""

    def __init__(
        self,
        graph_search: Callable[[Mapping[str, Any]], Any],
        vector_search: Callable[[Mapping[str, Any]], Any],
        graph_timeout_ms: float = 500.0,
        vector_timeout_ms: float = 500.0,
    ) -> None:
        if graph_timeout_ms <= 0 or vector_timeout_ms <= 0:
            raise ValueError("branch timeouts must be positive")
        self.graph_search = graph_search
        self.vector_search = vector_search
        self.timeouts = {"graph": graph_timeout_ms / 1000, "vector": vector_timeout_ms / 1000}

    def retrieve(self, plan: Mapping[str, Any]) -> RetrievalBundle:
        try:
            validated = validate_retrieval_plan(plan)
        except ContractValidationError as error:
            raise ValueError(str(error)) from error
        started = time.perf_counter()
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="videograph-retrieval")
        futures: dict[str, Future[Any]] = {}
        outcomes: dict[str, BranchOutcome] = {}
        try:
            futures["graph"] = executor.submit(self.graph_search, validated)
            futures["vector"] = executor.submit(self.vector_search, validated)
            outcomes.update(self._collect(futures))
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        graph = outcomes.get("graph") or BranchOutcome("graph", "failed", (), 0.0, "branch did not complete")
        vector = outcomes.get("vector") or BranchOutcome("vector", "failed", (), 0.0, "branch did not complete")
        partial_success = (graph.status == "success") != (vector.status == "success")
        return RetrievalBundle(
            plan=validated,
            graph=graph,
            vector=vector,
            partial_success=partial_success,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 3),
        )

    def _collect(self, futures: Mapping[str, Future[Any]]) -> dict[str, BranchOutcome]:
        started = {name: time.perf_counter() for name in futures}
        pending = set(futures.values())
        names = {future: name for name, future in futures.items()}
        outcomes: dict[str, BranchOutcome] = {}
        while pending:
            now = time.perf_counter()
            remaining = [self.timeouts[names[future]] - (now - started[names[future]]) for future in pending]
            wait(pending, timeout=max(0.0, min(remaining)))
            now = time.perf_counter()
            for future in list(pending):
                name = names[future]
                elapsed = now - started[name]
                if future.done():
                    pending.remove(future)
                    try:
                        result = future.result()
                    except Exception as error:  # branch failures are returned as metadata
                        outcomes[name] = BranchOutcome(name, "failed", (), round(elapsed * 1000, 3), str(error))
                    else:
                        outcomes[name] = BranchOutcome(name, "success", tuple(_results(result)), round(elapsed * 1000, 3))
                elif elapsed >= self.timeouts[name]:
                    pending.remove(future)
                    future.cancel()
                    outcomes[name] = BranchOutcome(name, "timeout", (), round(elapsed * 1000, 3), "branch timeout")
        return outcomes


def _results(value: Any) -> list[Any]:
    if value is None:
        return []
    hits = getattr(value, "hits", None)
    if hits is not None:
        return list(hits)
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]

