"""Dependency-light preprocessing components for the AI Service."""

from .asr import ASRConfig, ASRProvider, ASRResult, ASRSegment, AudioInput, FixtureASRProvider
from .frames import DeterministicFrameSampler, FrameCandidate, FrameSampler, RepresentativeFrame
from .metadata import FixtureMetadataInspector, MetadataInspector, VideoMetadata
from .ocr import FixtureOCRProvider, OCRFrameResult, OCRItem, OCRProvider
from .segmentation import (
    SceneBoundary,
    SegmenterConfig,
    SpeechSpan,
    TemporalChunk,
    TemporalSegmenter,
)

__all__ = [
    "ASRConfig",
    "ASRProvider",
    "ASRResult",
    "ASRSegment",
    "AudioInput",
    "FixtureMetadataInspector",
    "FixtureASRProvider",
    "FixtureOCRProvider",
    "FrameCandidate",
    "FrameSampler",
    "DeterministicFrameSampler",
    "OCRFrameResult",
    "OCRItem",
    "OCRProvider",
    "RepresentativeFrame",
    "MetadataInspector",
    "SceneBoundary",
    "SegmenterConfig",
    "SpeechSpan",
    "TemporalChunk",
    "TemporalSegmenter",
    "VideoMetadata",
]
