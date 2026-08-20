"""Deterministic speech/scene-aware temporal segmentation."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Iterable


@dataclass(frozen=True)
class SpeechSpan:
    """A timestamped speech interval supplied by ASR or a fixture."""

    start_ms: int
    end_ms: int
    text: str = ""

    def __post_init__(self) -> None:
        _validate_interval(self.start_ms, self.end_ms, "speech span")


@dataclass(frozen=True)
class SceneBoundary:
    """A candidate visual boundary; strong boundaries are not merged away."""

    timestamp_ms: int
    strong: bool = False

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise ValueError("scene boundary timestamp must be non-negative")


@dataclass(frozen=True)
class SegmenterConfig:
    """MVP chunking heuristics, expressed in milliseconds."""

    min_duration_ms: int = 3000
    target_duration_ms: int = 6000
    max_duration_ms: int = 15000
    frame_padding_ms: int = 500

    def __post_init__(self) -> None:
        if self.min_duration_ms <= 0:
            raise ValueError("min_duration_ms must be positive")
        if self.target_duration_ms < self.min_duration_ms:
            raise ValueError("target_duration_ms must be at least min_duration_ms")
        if self.max_duration_ms < self.target_duration_ms:
            raise ValueError("max_duration_ms must be at least target_duration_ms")
        if self.frame_padding_ms < 0:
            raise ValueError("frame_padding_ms must be non-negative")


@dataclass(frozen=True)
class TemporalChunk:
    """A content-local chunk descriptor for downstream AI stages."""

    chunk_id: str
    start_ms: int
    end_ms: int
    frame_timestamps_ms: tuple[int, ...]
    has_speech: bool

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class TemporalSegmenter:
    """Combine speech and visual boundaries into bounded semantic chunks."""

    def __init__(self, config: SegmenterConfig | None = None) -> None:
        self.config = config or SegmenterConfig()

    def segment(
        self,
        duration_ms: int,
        speech_spans: Iterable[SpeechSpan] = (),
        scene_boundaries: Iterable[SceneBoundary] = (),
    ) -> tuple[TemporalChunk, ...]:
        """Return an ordered, deterministic set of chunk descriptors."""

        if duration_ms <= 0:
            raise ValueError("duration_ms must be positive")

        speech = tuple(speech_spans)
        scenes = tuple(scene_boundaries)
        boundaries: dict[int, bool] = {0: True, duration_ms: True}

        for span in speech:
            for timestamp in (span.start_ms, span.end_ms):
                if 0 < timestamp < duration_ms:
                    boundaries[timestamp] = boundaries.get(timestamp, False)

        for scene in scenes:
            if 0 < scene.timestamp_ms < duration_ms:
                boundaries[scene.timestamp_ms] = (
                    boundaries.get(scene.timestamp_ms, False) or scene.strong
                )

        intervals = self._merge_short_intervals(sorted(boundaries.items()))
        intervals = self._split_long_intervals(intervals)

        chunks: list[TemporalChunk] = []
        for index, (start_ms, end_ms, _) in enumerate(intervals, start=1):
            chunks.append(
                TemporalChunk(
                    chunk_id=f"chunk_{index:03d}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    frame_timestamps_ms=self._representative_timestamps(start_ms, end_ms),
                    has_speech=_contains_speech(start_ms, end_ms, speech),
                )
            )
        return tuple(chunks)

    def _merge_short_intervals(
        self,
        boundaries: list[tuple[int, bool]],
    ) -> list[tuple[int, int, bool]]:
        intervals: list[list[int | bool]] = []
        for (start_ms, _), (end_ms, end_strong) in zip(boundaries, boundaries[1:]):
            intervals.append([start_ms, end_ms, end_strong])

        changed = True
        while changed:
            changed = False
            for index, interval in enumerate(intervals):
                start_ms, end_ms, end_strong = interval
                if end_ms - start_ms >= self.config.min_duration_ms or end_strong:
                    continue
                if index + 1 < len(intervals):
                    next_interval = intervals[index + 1]
                    interval[1] = next_interval[1]
                    interval[2] = next_interval[2]
                    del intervals[index + 1]
                elif index > 0:
                    previous = intervals[index - 1]
                    previous[1] = end_ms
                    previous[2] = end_strong
                    del intervals[index]
                changed = True
                break

        return [(int(start), int(end), bool(strong)) for start, end, strong in intervals]

    def _split_long_intervals(
        self,
        intervals: list[tuple[int, int, bool]],
    ) -> list[tuple[int, int, bool]]:
        result: list[tuple[int, int, bool]] = []
        split_duration = min(self.config.target_duration_ms, self.config.max_duration_ms)
        for start_ms, end_ms, end_strong in intervals:
            duration_ms = end_ms - start_ms
            if duration_ms <= self.config.max_duration_ms:
                result.append((start_ms, end_ms, end_strong))
                continue
            piece_count = ceil(duration_ms / split_duration)
            previous = start_ms
            for piece_index in range(1, piece_count + 1):
                boundary = start_ms + round(duration_ms * piece_index / piece_count)
                result.append((previous, boundary, end_strong and piece_index == piece_count))
                previous = boundary
        return result

    def _representative_timestamps(self, start_ms: int, end_ms: int) -> tuple[int, ...]:
        duration_ms = end_ms - start_ms
        padding = min(self.config.frame_padding_ms, duration_ms // 4)
        candidates = (start_ms + padding, start_ms + duration_ms // 2, end_ms - padding)
        return tuple(dict.fromkeys(sorted(candidates)))


def _contains_speech(start_ms: int, end_ms: int, spans: tuple[SpeechSpan, ...]) -> bool:
    return any(span.start_ms < end_ms and span.end_ms > start_ms for span in spans)


def _validate_interval(start_ms: int, end_ms: int, label: str) -> None:
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError(f"{label} must have 0 <= start_ms < end_ms")
