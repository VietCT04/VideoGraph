"""Representative frame sampling and deterministic near-duplicate reduction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, Sequence

from .segmentation import TemporalChunk


@dataclass(frozen=True)
class FrameCandidate:
    """A decoded-frame reference with a lightweight comparison fingerprint."""

    frame_id: str
    timestamp_ms: int
    fingerprint: tuple[int, ...] = ()
    source_ref: str | None = None
    important: bool = False

    def __post_init__(self) -> None:
        if not self.frame_id.strip():
            raise ValueError("frame_id must not be empty")
        if self.timestamp_ms < 0:
            raise ValueError("frame timestamp must be non-negative")


@dataclass(frozen=True)
class RepresentativeFrame:
    """A frame selected for OCR or later multimodal fusion."""

    frame_id: str
    timestamp_ms: int
    source_ref: str | None = None


class FrameSampler(Protocol):
    """Replaceable boundary for FFmpeg/OpenCV or a frame cache."""

    def sample(
        self,
        chunk: TemporalChunk,
        candidates: Sequence[FrameCandidate],
    ) -> tuple[RepresentativeFrame, ...]:
        """Select a small timestamped set for one semantic chunk."""


class DeterministicFrameSampler:
    """Select anchors and important frames after cheap fingerprint deduplication."""

    def __init__(self, max_frames: int = 4, similarity_threshold: float = 0.8) -> None:
        if max_frames < 1:
            raise ValueError("max_frames must be positive")
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        self.max_frames = max_frames
        self.similarity_threshold = similarity_threshold

    def sample(
        self,
        chunk: TemporalChunk,
        candidates: Sequence[FrameCandidate],
    ) -> tuple[RepresentativeFrame, ...]:
        """Return at most ``max_frames`` frames in timestamp order."""

        ordered = sorted(
            (
                candidate
                for candidate in candidates
                if chunk.start_ms <= candidate.timestamp_ms <= chunk.end_ms
            ),
            key=lambda candidate: (candidate.timestamp_ms, candidate.frame_id),
        )
        unique = self._deduplicate(ordered)
        if len(unique) <= self.max_frames:
            return tuple(_to_representative(candidate) for candidate in unique)

        anchors = {
            self._closest(unique, chunk.start_ms).frame_id,
            self._closest(unique, (chunk.start_ms + chunk.end_ms) // 2).frame_id,
            self._closest(unique, chunk.end_ms).frame_id,
        }
        preferred = [candidate for candidate in unique if candidate.important]
        preferred.extend(candidate for candidate in unique if candidate.frame_id in anchors)
        selected = _unique_by_id(preferred)
        if len(selected) < self.max_frames:
            selected.extend(
                candidate
                for candidate in unique
                if candidate.frame_id not in {item.frame_id for item in selected}
            )
        selected = sorted(
            selected[: self.max_frames],
            key=lambda candidate: candidate.timestamp_ms,
        )
        return tuple(_to_representative(candidate) for candidate in selected)

    def _deduplicate(self, candidates: Sequence[FrameCandidate]) -> list[FrameCandidate]:
        selected: list[FrameCandidate] = []
        for candidate in candidates:
            if any(
                _fingerprint_similarity(candidate.fingerprint, existing.fingerprint)
                >= self.similarity_threshold
                for existing in selected
            ):
                continue
            selected.append(candidate)
        return selected

    @staticmethod
    def _closest(candidates: Sequence[FrameCandidate], timestamp_ms: int) -> FrameCandidate:
        return min(
            candidates,
            key=lambda candidate: (abs(candidate.timestamp_ms - timestamp_ms), candidate.timestamp_ms),
        )


def candidate_timestamps(
    chunk: TemporalChunk,
    scene_change_timestamps: Iterable[int] = (),
) -> tuple[int, ...]:
    """Build start/middle/end candidates plus in-chunk scene changes."""

    timestamps = set(chunk.frame_timestamps_ms)
    timestamps.update(
        timestamp
        for timestamp in scene_change_timestamps
        if chunk.start_ms <= timestamp <= chunk.end_ms
    )
    return tuple(sorted(timestamps))


def _fingerprint_similarity(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    matches = sum(left_item == right_item for left_item, right_item in zip(left, right))
    return matches / len(left)


def _to_representative(candidate: FrameCandidate) -> RepresentativeFrame:
    return RepresentativeFrame(candidate.frame_id, candidate.timestamp_ms, candidate.source_ref)


def _unique_by_id(candidates: Iterable[FrameCandidate]) -> list[FrameCandidate]:
    result: list[FrameCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.frame_id not in seen:
            result.append(candidate)
            seen.add(candidate.frame_id)
    return result
