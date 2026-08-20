"""Testable asynchronous job orchestration for the AI Service."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Callable, Mapping, Protocol

from contracts.validation import ContractValidationError, validate_extraction
from pipeline.asr import ASRSegment, AudioInput, FixtureASRProvider
from pipeline.embeddings import HashingEmbeddingProvider, embed_extraction
from pipeline.frames import DeterministicFrameSampler, FrameCandidate
from pipeline.fusion import (
    FixtureFusionProvider,
    MultimodalBundle,
    build_extraction_payload,
)
from pipeline.ocr import FixtureOCRProvider, OCRItem
from pipeline.metadata import VideoMetadata
from pipeline.segmentation import TemporalSegmenter


class JobState(str, Enum):
    """Stable service-side job states visible to the main backend."""

    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    SEGMENTING = "segmenting"
    EXTRACTING_VISUALS = "extracting_visuals"
    FUSING = "fusing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_STATES = {JobState.COMPLETED, JobState.FAILED}
StageCallback = Callable[[JobState], None]


@dataclass(frozen=True)
class ProcessVideoRequest:
    """Validated job input accepted by both HTTP adapters."""

    content_id: str
    creator_id: str
    video_url: str | None = None
    upload_ref: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.content_id, str)
            or not isinstance(self.creator_id, str)
            or not self.content_id.strip()
            or not self.creator_id.strip()
        ):
            raise ValueError("content_id and creator_id must not be empty")
        if bool(self.video_url) == bool(self.upload_ref):
            raise ValueError("provide exactly one of video_url or upload_ref")

    @classmethod
    def from_mapping(cls, value: object) -> "ProcessVideoRequest":
        if not isinstance(value, Mapping):
            raise ValueError("request body must be an object")
        allowed = {"content_id", "creator_id", "video_url", "upload_ref"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown request properties: {sorted(unknown)}")
        content_id = value.get("content_id")
        creator_id = value.get("creator_id")
        video_url = value.get("video_url")
        upload_ref = value.get("upload_ref")
        for name, item in (
            ("content_id", content_id),
            ("creator_id", creator_id),
            ("video_url", video_url),
            ("upload_ref", upload_ref),
        ):
            if item is not None and not isinstance(item, str):
                raise ValueError(f"{name} must be a string when provided")
        return cls(content_id, creator_id, video_url, upload_ref)

    def as_dict(self) -> dict[str, object]:
        return {
            "content_id": self.content_id,
            "creator_id": self.creator_id,
            "video_url": self.video_url,
            "upload_ref": self.upload_ref,
        }


@dataclass(frozen=True)
class JobRecord:
    """In-memory job state and temporary result metadata."""

    job_id: str
    request: ProcessVideoRequest
    status: JobState
    created_at: float
    updated_at: float
    result: dict[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None

    def status_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "job_id": self.job_id,
            "content_id": self.request.content_id,
            "creator_id": self.request.creator_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.error_code is not None:
            payload["error"] = {
                "code": self.error_code,
                "message": self.error_message or "job failed",
            }
        return payload


class VideoPipeline(Protocol):
    """Replaceable ordered pipeline used by the job worker."""

    def process(self, request: ProcessVideoRequest, notify: StageCallback) -> dict[str, object]:
        """Return one contract-compatible extraction payload."""


class InMemoryJobStore:
    """Thread-safe temporary job/result storage for one service process."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, JobRecord] = {}

    def create(self, request: ProcessVideoRequest) -> JobRecord:
        now = time.time()
        record = JobRecord(uuid.uuid4().hex, request, JobState.QUEUED, now, now)
        with self._lock:
            self._jobs[record.job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return copy.deepcopy(record) if record is not None else None

    def update(self, job_id: str, **changes: object) -> JobRecord:
        with self._lock:
            current = self._jobs[job_id]
            updated = replace(current, updated_at=time.time(), **changes)
            self._jobs[job_id] = updated
            return copy.deepcopy(updated)


class JobService:
    """Submit jobs immediately and execute them on a small in-process worker pool."""

    def __init__(
        self,
        pipeline: VideoPipeline | None = None,
        store: InMemoryJobStore | None = None,
        max_workers: int = 1,
    ) -> None:
        if max_workers <= 0:
            raise ValueError("max_workers must be positive")
        self.store = store or InMemoryJobStore()
        self.pipeline = pipeline or FixtureVideoPipeline()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, request: ProcessVideoRequest) -> JobRecord:
        record = self.store.create(request)
        self._executor.submit(self._run, record.job_id, request)
        return record

    def get_status(self, job_id: str) -> JobRecord | None:
        return self.store.get(job_id)

    def get_result(self, job_id: str) -> dict[str, object] | None:
        record = self.store.get(job_id)
        if record is None or record.status != JobState.COMPLETED or record.result is None:
            return None
        return copy.deepcopy(record.result)

    def wait_for_terminal(self, job_id: str, timeout_seconds: float = 5.0) -> JobRecord | None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            record = self.get_status(job_id)
            if record is None or record.status in TERMINAL_STATES:
                return record
            time.sleep(0.001)
        return self.get_status(job_id)

    def close(self) -> None:
        self._executor.shutdown(wait=True)

    def _run(self, job_id: str, request: ProcessVideoRequest) -> None:
        try:
            result = self.pipeline.process(request, lambda state: self._notify(job_id, state))
            validate_extraction(result)
            self.store.update(job_id, status=JobState.COMPLETED, result=result)
        except ContractValidationError as exc:
            self.store.update(
                job_id,
                status=JobState.FAILED,
                error_code="CONTRACT_VALIDATION_FAILED",
                error_message=str(exc),
            )
        except Exception as exc:
            self.store.update(
                job_id,
                status=JobState.FAILED,
                error_code="PIPELINE_FAILED",
                error_message=f"{type(exc).__name__}: {exc}",
            )

    def _notify(self, job_id: str, state: JobState) -> None:
        self.store.update(job_id, status=state, result=None, error_code=None, error_message=None)


class FixtureVideoPipeline:
    """Exercise the #3–#7 boundaries with one deterministic beauty fixture."""

    def process(self, request: ProcessVideoRequest, notify: StageCallback) -> dict[str, object]:
        notify(JobState.PREPROCESSING)
        metadata = VideoMetadata(
            duration_ms=11000,
            width=1920,
            height=1080,
            fps=30,
            has_audio=True,
        )

        notify(JobState.TRANSCRIBING)
        asr = FixtureASRProvider(
            {
                "beauty": (
                    ASRSegment(
                        "asr_1",
                        5000,
                        11000,
                        "This one is my favorite for everyday use.",
                        0.94,
                    ),
                )
            }
        )
        asr_result = asr.transcribe(
            AudioInput("fixture-video", metadata.duration_ms, fixture_key="beauty")
        )

        notify(JobState.SEGMENTING)
        chunks = TemporalSegmenter().segment(metadata.duration_ms, asr_result.to_speech_spans())
        chunk = next((item for item in chunks if item.start_ms == 5000), chunks[-1])

        notify(JobState.EXTRACTING_VISUALS)
        candidates = (
            FrameCandidate("frame_5", 5500, (5, 5, 5, 5)),
            FrameCandidate("frame_8", 8000, (8, 8, 8, 8), important=True),
            FrameCandidate("frame_10", 10500, (10, 10, 10, 10)),
        )
        frames = DeterministicFrameSampler(max_frames=4).sample(chunk, candidates)
        ocr = FixtureOCRProvider(
            {"frame_8": (OCRItem("ocr_1", "RARE BEAUTY", 0.96, (112, 220, 390, 305)),)}
        )
        ocr_results = ocr.recognize_many(frames)

        notify(JobState.FUSING)
        bundle = MultimodalBundle(
            chunk=chunk,
            transcript=asr_result.segments[0].text,
            asr_segment_ids=tuple(segment.id for segment in asr_result.segments),
            frames=tuple(frames),
            ocr_results=ocr_results,
            fixture_key="beauty",
        )
        fusion_output = FixtureFusionProvider().fuse(bundle)
        extraction = build_extraction_payload(
            request.content_id,
            request.creator_id,
            (fusion_output,),
        )

        notify(JobState.EMBEDDING)
        return embed_extraction(extraction, HashingEmbeddingProvider())
