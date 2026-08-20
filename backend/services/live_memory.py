"""Fixture-backed incremental LIVE memory state.

This module models stream-time updates without connecting to a real stream provider
or writing directly to Neo4j/pgvector. The backend can use the finalized records to
hand off to its normal indexing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LiveMomentState(str, Enum):
    TEMPORARY = "temporary"
    FINALIZED = "finalized"


@dataclass(frozen=True)
class LiveMoment:
    """One content-local LIVE moment with both timestamp domains."""

    temporary_id: str
    content_id: str
    stream_start_ms: int
    stream_end_ms: int
    wall_clock_start: str
    wall_clock_end: str
    extraction: dict[str, Any]
    state: LiveMomentState = LiveMomentState.TEMPORARY
    persistent_moment_id: str | None = None

    def update(
        self,
        *,
        stream_end_ms: int,
        wall_clock_end: str,
        extraction: dict[str, Any],
    ) -> "LiveMoment":
        _validate_interval(self.stream_start_ms, stream_end_ms)
        if not wall_clock_end:
            raise ValueError("wall_clock_end must not be empty")
        return LiveMoment(
            temporary_id=self.temporary_id,
            content_id=self.content_id,
            stream_start_ms=self.stream_start_ms,
            stream_end_ms=stream_end_ms,
            wall_clock_start=self.wall_clock_start,
            wall_clock_end=wall_clock_end,
            extraction=dict(extraction),
            state=self.state,
            persistent_moment_id=self.persistent_moment_id,
        )


class LiveMemoryStore:
    """In-memory rolling LIVE store used by tests and local demos."""

    def __init__(self) -> None:
        self._moments: dict[str, LiveMoment] = {}

    def append_or_update(
        self,
        *,
        content_id: str,
        chunk_id: str,
        stream_start_ms: int,
        stream_end_ms: int,
        wall_clock_start: str,
        wall_clock_end: str,
        extraction: dict[str, Any],
    ) -> LiveMoment:
        if not content_id:
            raise ValueError("content_id must not be empty")
        if not chunk_id:
            raise ValueError("chunk_id must not be empty")
        if not wall_clock_start or not wall_clock_end:
            raise ValueError("wall-clock timestamps must not be empty")
        _validate_interval(stream_start_ms, stream_end_ms)

        temporary_id = f"live:{content_id}:{chunk_id}"
        existing = self._moments.get(temporary_id)
        if existing is not None:
            if existing.content_id != content_id:
                raise ValueError("a temporary moment cannot change content")
            updated = existing.update(
                stream_end_ms=stream_end_ms,
                wall_clock_end=wall_clock_end,
                extraction=extraction,
            )
            self._moments[temporary_id] = updated
            return updated

        moment = LiveMoment(
            temporary_id=temporary_id,
            content_id=content_id,
            stream_start_ms=stream_start_ms,
            stream_end_ms=stream_end_ms,
            wall_clock_start=wall_clock_start,
            wall_clock_end=wall_clock_end,
            extraction=dict(extraction),
        )
        self._moments[temporary_id] = moment
        return moment

    def get(self, temporary_id: str) -> LiveMoment:
        try:
            return self._moments[temporary_id]
        except KeyError as error:
            raise KeyError(f"unknown LIVE moment: {temporary_id}") from error

    def list_for_content(self, content_id: str) -> list[LiveMoment]:
        return sorted(
            (moment for moment in self._moments.values() if moment.content_id == content_id),
            key=lambda moment: (moment.stream_start_ms, moment.temporary_id),
        )

    def finalize(self, content_id: str, persistent_content_id: str) -> list[LiveMoment]:
        """Finalize temporary moments into IDs consumable by normal indexing."""

        if not persistent_content_id:
            raise ValueError("persistent_content_id must not be empty")

        finalized: list[LiveMoment] = []
        for moment in self.list_for_content(content_id):
            persistent_id = (
                f"moment:{persistent_content_id}:"
                f"{moment.stream_start_ms}:{moment.stream_end_ms}"
            )
            finalized_moment = LiveMoment(
                temporary_id=moment.temporary_id,
                content_id=persistent_content_id,
                stream_start_ms=moment.stream_start_ms,
                stream_end_ms=moment.stream_end_ms,
                wall_clock_start=moment.wall_clock_start,
                wall_clock_end=moment.wall_clock_end,
                extraction=dict(moment.extraction),
                state=LiveMomentState.FINALIZED,
                persistent_moment_id=persistent_id,
            )
            self._moments.pop(moment.temporary_id)
            self._moments[persistent_id] = finalized_moment
            finalized.append(finalized_moment)
        return finalized


def _validate_interval(start_ms: int, end_ms: int) -> None:
    if not isinstance(start_ms, int) or not isinstance(end_ms, int):
        raise ValueError("stream timestamps must be integers")
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError("stream interval must be non-negative and non-empty")
