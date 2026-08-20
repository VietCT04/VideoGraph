"""Dependency-light preprocessing components for the AI Service."""

from .asr import ASRConfig, ASRProvider, ASRResult, ASRSegment, AudioInput, FixtureASRProvider
from .frames import DeterministicFrameSampler, FrameCandidate, FrameSampler, RepresentativeFrame
from .fusion import (
    FixtureFusionProvider,
    FusionEntity,
    FusionOutput,
    FusionRelation,
    MultimodalBundle,
    VLMProvider,
    build_extraction_payload,
    validate_fusion_output,
)
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
    "FixtureFusionProvider",
    "FrameCandidate",
    "FrameSampler",
    "DeterministicFrameSampler",
    "OCRFrameResult",
    "OCRItem",
    "OCRProvider",
    "RepresentativeFrame",
    "FusionEntity",
    "FusionOutput",
    "FusionRelation",
    "MultimodalBundle",
    "VLMProvider",
    "build_extraction_payload",
    "validate_fusion_output",
    "MetadataInspector",
    "SceneBoundary",
    "SegmenterConfig",
    "SpeechSpan",
    "TemporalChunk",
    "TemporalSegmenter",
    "VideoMetadata",
]
