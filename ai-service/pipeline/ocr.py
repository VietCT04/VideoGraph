"""Timestamped OCR result models and a deterministic fixture provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from .frames import RepresentativeFrame


@dataclass(frozen=True)
class OCRItem:
    """One OCR span with source-frame geometry."""

    item_id: str
    text: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("OCR item_id must not be empty")
        if not self.text.strip():
            raise ValueError("OCR text must not be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("OCR confidence must be between 0 and 1")
        if self.bbox is not None:
            if len(self.bbox) != 4 or any(coordinate < 0 for coordinate in self.bbox):
                raise ValueError("OCR bbox must contain four non-negative coordinates")
            if self.bbox[2] < self.bbox[0] or self.bbox[3] < self.bbox[1]:
                raise ValueError("OCR bbox must have non-negative width and height")


@dataclass(frozen=True)
class OCRFrameResult:
    """OCR evidence tied to the exact selected frame timestamp."""

    frame_id: str
    timestamp_ms: int
    items: tuple[OCRItem, ...]
    provider: str

    def __post_init__(self) -> None:
        if not self.frame_id.strip():
            raise ValueError("frame_id must not be empty")
        if self.timestamp_ms < 0:
            raise ValueError("OCR timestamp must be non-negative")
        if not self.provider.strip():
            raise ValueError("provider must not be empty")

    def as_dict(self) -> dict[str, object]:
        return {
            "frame_id": self.frame_id,
            "timestamp_ms": self.timestamp_ms,
            "provider": self.provider,
            "items": [
                {
                    "item_id": item.item_id,
                    "text": item.text,
                    "confidence": item.confidence,
                    "bbox": list(item.bbox) if item.bbox is not None else None,
                }
                for item in self.items
            ],
        }


class OCRProvider(Protocol):
    """Replaceable boundary for Tesseract, PaddleOCR, or another OCR engine."""

    def recognize(self, frame: RepresentativeFrame) -> OCRFrameResult:
        """Return timestamp-preserving OCR evidence for one frame."""


class FixtureOCRProvider:
    """Return configured OCR items without decoding pixels or loading OCR models."""

    def __init__(
        self,
        fixtures: Mapping[str, Sequence[OCRItem]],
        provider_name: str = "fixture",
    ) -> None:
        self.provider_name = provider_name
        self._fixtures = {key: tuple(value) for key, value in fixtures.items()}

    def recognize(self, frame: RepresentativeFrame) -> OCRFrameResult:
        return OCRFrameResult(
            frame_id=frame.frame_id,
            timestamp_ms=frame.timestamp_ms,
            items=self._fixtures.get(frame.frame_id, ()),
            provider=self.provider_name,
        )

    def recognize_many(self, frames: Sequence[RepresentativeFrame]) -> tuple[OCRFrameResult, ...]:
        """Process selected frames in stable order for one job."""

        return tuple(self.recognize(frame) for frame in frames)
