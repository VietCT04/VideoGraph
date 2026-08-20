"""Video metadata interfaces with a deterministic fixture implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class VideoMetadata:
    """Metadata required by temporal preprocessing."""

    duration_ms: int
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    has_audio: bool = True

    def __post_init__(self) -> None:
        if self.duration_ms <= 0:
            raise ValueError("duration_ms must be positive")
        if self.width is not None and self.width <= 0:
            raise ValueError("width must be positive when provided")
        if self.height is not None and self.height <= 0:
            raise ValueError("height must be positive when provided")
        if self.fps is not None and self.fps <= 0:
            raise ValueError("fps must be positive when provided")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "VideoMetadata":
        """Build metadata from a probe-like mapping."""

        duration_ms = value.get("duration_ms")
        if not isinstance(duration_ms, int) or isinstance(duration_ms, bool):
            raise ValueError("duration_ms must be an integer")
        return cls(
            duration_ms=duration_ms,
            width=_optional_int(value.get("width"), "width"),
            height=_optional_int(value.get("height"), "height"),
            fps=_optional_float(value.get("fps"), "fps"),
            has_audio=_optional_bool(value.get("has_audio"), "has_audio", True),
        )


class MetadataInspector(Protocol):
    """Boundary for ffprobe/OpenCV or another metadata implementation."""

    def inspect(self, source_ref: str) -> VideoMetadata:
        """Return metadata for one selected source."""


class FixtureMetadataInspector:
    """Look up metadata without opening a video or requiring FFmpeg."""

    def __init__(self, fixtures: Mapping[str, VideoMetadata]) -> None:
        self._fixtures = dict(fixtures)

    def inspect(self, source_ref: str) -> VideoMetadata:
        try:
            return self._fixtures[source_ref]
        except KeyError as exc:
            raise KeyError(f"no metadata fixture for {source_ref!r}") from exc


def _optional_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer when provided")
    return value


def _optional_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric when provided")
    return float(value)


def _optional_bool(value: object, name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean when provided")
    return value
