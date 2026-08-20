"""Dependency-light preprocessing components for the AI Service."""

from .asr import ASRConfig, ASRProvider, ASRResult, ASRSegment, AudioInput, FixtureASRProvider
from .metadata import FixtureMetadataInspector, MetadataInspector, VideoMetadata
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
    "MetadataInspector",
    "SceneBoundary",
    "SegmenterConfig",
    "SpeechSpan",
    "TemporalChunk",
    "TemporalSegmenter",
    "VideoMetadata",
]
