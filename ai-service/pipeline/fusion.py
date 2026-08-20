"""Structured multimodal fusion models and fixture-backed validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from contracts.validation import ContractValidationError, validate_extraction

from .frames import RepresentativeFrame
from .ocr import OCRFrameResult
from .segmentation import TemporalChunk


@dataclass(frozen=True)
class MultimodalBundle:
    """Evidence assembled for one temporal chunk."""

    chunk: TemporalChunk
    transcript: str
    asr_segment_ids: tuple[str, ...]
    frames: tuple[RepresentativeFrame, ...]
    ocr_results: tuple[OCRFrameResult, ...]
    fixture_key: str

    def context(self) -> dict[str, object]:
        """Return a provider-neutral, timestamp-preserving context object."""

        return {
            "chunk": {
                "local_id": self.chunk.chunk_id,
                "start_ms": self.chunk.start_ms,
                "end_ms": self.chunk.end_ms,
            },
            "transcript": self.transcript,
            "asr_segment_ids": list(self.asr_segment_ids),
            "frames": [
                {"frame_id": frame.frame_id, "timestamp_ms": frame.timestamp_ms}
                for frame in self.frames
            ],
            "ocr": [result.as_dict() for result in self.ocr_results],
        }


@dataclass(frozen=True)
class FusionEntity:
    """A content-local candidate entity from structured fusion."""

    local_id: str
    type: str
    name: str
    confidence: float
    evidence_refs: tuple[str, ...] = ()
    explicit: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "local_id": self.local_id,
            "type": self.type,
            "name": self.name,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "explicit": self.explicit,
        }


@dataclass(frozen=True)
class FusionRelation:
    """A controlled-ontology relation grounded in local evidence references."""

    subject: str
    predicate: str
    object: str
    confidence: float
    evidence_refs: tuple[str, ...]
    explicit: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "explicit": self.explicit,
        }


@dataclass(frozen=True)
class FusionOutput:
    """Validated extraction Moment data emitted by a fusion provider."""

    local_id: str
    start_ms: int
    end_ms: int
    transcript: str
    semantic_text: str
    entities: tuple[FusionEntity, ...]
    relations: tuple[FusionRelation, ...]
    evidence: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "local_id": self.local_id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "transcript": self.transcript,
            "semantic_text": self.semantic_text,
            "entities": [entity.as_dict() for entity in self.entities],
            "relations": [relation.as_dict() for relation in self.relations],
            "evidence": self.evidence,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FusionOutput":
        """Parse and validate provider output before exposing it to callers."""

        payload = dict(value)
        validate_fusion_output(payload)
        entities = tuple(
            FusionEntity(
                local_id=entity["local_id"],
                type=entity["type"],
                name=entity["name"],
                confidence=entity["confidence"],
                evidence_refs=tuple(entity.get("evidence_refs", ())),
                explicit=entity.get("explicit", True),
            )
            for entity in payload["entities"]
        )
        relations = tuple(
            FusionRelation(
                subject=relation["subject"],
                predicate=relation["predicate"],
                object=relation["object"],
                confidence=relation["confidence"],
                evidence_refs=tuple(relation["evidence_refs"]),
                explicit=relation.get("explicit", True),
            )
            for relation in payload["relations"]
        )
        return cls(
            local_id=payload["local_id"],
            start_ms=payload["start_ms"],
            end_ms=payload["end_ms"],
            transcript=payload.get("transcript", ""),
            semantic_text=payload["semantic_text"],
            entities=entities,
            relations=relations,
            evidence=dict(payload["evidence"]),
        )


class VLMProvider(Protocol):
    """Replaceable boundary for a structured VLM or multimodal model."""

    def fuse(self, bundle: MultimodalBundle) -> FusionOutput:
        """Return validated content-local facts for one chunk."""


def validate_fusion_output(value: object) -> dict[str, Any]:
    """Validate fusion output using the shared ontology and evidence rules."""

    if not isinstance(value, dict):
        raise ContractValidationError(["$: fusion output must be an object"])
    wrapper = {
        "schema_version": "1.0",
        "content_id": "fusion-content",
        "creator_id": "fusion-creator",
        "moments": [value],
    }
    validate_extraction(wrapper)
    for index, relation in enumerate(value["relations"]):
        if not relation["evidence_refs"]:
            raise ContractValidationError(
                [f"$.relations[{index}].evidence_refs: expected at least one reference"]
            )
    return value


class FixtureFusionProvider:
    """Load deterministic structured outputs from local JSON fixtures."""

    def __init__(self, fixture_directory: Path | None = None) -> None:
        self.fixture_directory = (
            fixture_directory or Path(__file__).resolve().parents[1] / "fixtures"
        )

    def fuse(self, bundle: MultimodalBundle) -> FusionOutput:
        fixture_path = self.fixture_directory / f"{bundle.fixture_key}.json"
        with fixture_path.open(encoding="utf-8") as fixture_file:
            payload = json.load(fixture_file)
        output = FusionOutput.from_mapping(payload)
        if (output.start_ms, output.end_ms) != (
            bundle.chunk.start_ms,
            bundle.chunk.end_ms,
        ):
            raise ContractValidationError(
                ["$: fusion fixture timestamps must match the input chunk"]
            )
        return output


def build_extraction_payload(
    content_id: str,
    creator_id: str,
    outputs: Sequence[FusionOutput],
) -> dict[str, object]:
    """Wrap content-local fusion Moments in the shared extraction contract."""

    moments: list[dict[str, object]] = []
    used_local_ids: set[str] = set()
    for index, output in enumerate(outputs, start=1):
        moment = output.as_dict()
        if moment["local_id"] in used_local_ids:
            moment["local_id"] = f"{moment['local_id']}_{index}"
        used_local_ids.add(moment["local_id"])
        moments.append(moment)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "content_id": content_id,
        "creator_id": creator_id,
        "pipeline": {"version": "fixture-fusion-v1"},
        "moments": moments,
    }
    validate_extraction(payload)
    return payload
