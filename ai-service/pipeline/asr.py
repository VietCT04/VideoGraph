"""Timestamped ASR interfaces and a deterministic fixture provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from .segmentation import SpeechSpan


@dataclass(frozen=True)
class ASRConfig:
    """Provider settings that callers can pass without depending on Whisper."""

    model_size: str = "small"
    compute_type: str = "auto"
    no_speech_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not self.model_size.strip():
            raise ValueError("model_size must not be empty")
        if not self.compute_type.strip():
            raise ValueError("compute_type must not be empty")
        if not 0 <= self.no_speech_threshold <= 1:
            raise ValueError("no_speech_threshold must be between 0 and 1")


@dataclass(frozen=True)
class AudioInput:
    """Audio reference and duration supplied to an ASR provider."""

    source_ref: str
    duration_ms: int
    language_hint: str | None = None
    fixture_key: str | None = None

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("source_ref must not be empty")
        if self.duration_ms <= 0:
            raise ValueError("duration_ms must be positive")


@dataclass(frozen=True)
class ASRSegment:
    """One ordered timestamped speech segment."""

    id: str
    start_ms: int
    end_ms: int
    text: str
    confidence: float
    no_speech_probability: float = 0.0

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ASR segment id must not be empty")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("ASR segment must have 0 <= start_ms < end_ms")
        if not self.text.strip():
            raise ValueError("ASR segment text must not be empty")
        _check_probability(self.confidence, "confidence")
        _check_probability(self.no_speech_probability, "no_speech_probability")


@dataclass(frozen=True)
class ASRResult:
    """Normalized ASR output consumed by temporal segmentation."""

    segments: tuple[ASRSegment, ...]
    language: str | None
    speech_ratio: float
    no_speech: bool
    provider: str
    model: str

    def __post_init__(self) -> None:
        _check_probability(self.speech_ratio, "speech_ratio")
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        previous_end = -1
        for segment in self.segments:
            if segment.start_ms < previous_end:
                raise ValueError("ASR segments must be ordered and non-overlapping")
            previous_end = segment.end_ms
        if self.no_speech != (not self.segments or self.speech_ratio == 0):
            raise ValueError("no_speech must reflect whether usable segments exist")

    @classmethod
    def empty(cls, language: str | None, provider: str, model: str) -> "ASRResult":
        """Return an explicit no-speech result with no fabricated transcript."""

        return cls(
            segments=(),
            language=language,
            speech_ratio=0.0,
            no_speech=True,
            provider=provider,
            model=model,
        )

    def to_speech_spans(self) -> tuple[SpeechSpan, ...]:
        """Convert normalized segments to the #3 segmenter input shape."""

        return tuple(
            SpeechSpan(segment.start_ms, segment.end_ms, segment.text)
            for segment in self.segments
        )

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation for logs and job metadata."""

        return {
            "segments": [
                {
                    "id": segment.id,
                    "start_ms": segment.start_ms,
                    "end_ms": segment.end_ms,
                    "text": segment.text,
                    "confidence": segment.confidence,
                    "no_speech_probability": segment.no_speech_probability,
                }
                for segment in self.segments
            ],
            "language": self.language,
            "speech_ratio": self.speech_ratio,
            "no_speech": self.no_speech,
            "provider": self.provider,
            "model": self.model,
        }


class ASRProvider(Protocol):
    """Replaceable boundary for faster-whisper, Whisper, or another ASR engine."""

    def transcribe(self, audio: AudioInput) -> ASRResult:
        """Return timestamped speech evidence for one audio input."""


class FixtureASRProvider:
    """Return configured segments without loading an ASR model or audio codec."""

    def __init__(
        self,
        fixtures: Mapping[str, Sequence[ASRSegment]],
        config: ASRConfig | None = None,
        provider_name: str = "fixture",
    ) -> None:
        self.config = config or ASRConfig()
        self.provider_name = provider_name
        self._fixtures = {key: tuple(value) for key, value in fixtures.items()}

    def transcribe(self, audio: AudioInput) -> ASRResult:
        key = audio.fixture_key or audio.source_ref
        configured_segments = self._fixtures.get(key, ())
        segments = tuple(
            segment
            for segment in configured_segments
            if segment.end_ms <= audio.duration_ms
            and segment.no_speech_probability < self.config.no_speech_threshold
        )
        speech_ms = sum(segment.end_ms - segment.start_ms for segment in segments)
        speech_ratio = min(1.0, speech_ms / audio.duration_ms)
        if not segments:
            return ASRResult.empty(
                language=audio.language_hint,
                provider=self.provider_name,
                model=self.config.model_size,
            )
        return ASRResult(
            segments=segments,
            language=audio.language_hint,
            speech_ratio=speech_ratio,
            no_speech=False,
            provider=self.provider_name,
            model=self.config.model_size,
        )

    def transcribe_many(self, audio_inputs: Sequence[AudioInput]) -> tuple[ASRResult, ...]:
        """Provide deterministic batching for callers processing multiple clips."""

        return tuple(self.transcribe(audio) for audio in audio_inputs)


def _check_probability(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
