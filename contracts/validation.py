"""Small standard-library validators for the versioned JSON contracts.

The JSON Schema files remain the language-neutral source of truth. This module
implements the subset of their constraints needed at the Python service
boundaries without adding a runtime validation dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .ontology import (
    CONTENT_SOURCE_TYPES,
    ENTITY_TYPES,
    EXTRACTION_SCHEMA_VERSION,
    RELATION_TYPES,
    RESULT_TYPES,
    RETRIEVAL_PLAN_SCHEMA_VERSION,
)

CONTRACTS_DIR = Path(__file__).resolve().parent


class ContractValidationError(ValueError):
    """Raised when a payload is not valid for a shared v1 contract."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


def load_schema(name: str) -> dict[str, Any]:
    """Load a checked-in JSON Schema by filename."""

    path = CONTRACTS_DIR / name
    with path.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    if not isinstance(schema, dict):
        raise ContractValidationError([f"{name}: schema root must be an object"])
    return schema


def validate_extraction(payload: object) -> dict[str, Any]:
    """Validate and return a multimodal extraction payload."""

    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ContractValidationError(["$: extraction payload must be an object"])

    _check_keys(
        payload,
        {
            "schema_version",
            "content_id",
            "creator_id",
            "content_metadata",
            "pipeline",
            "moments",
        },
        {"schema_version", "content_id", "creator_id", "moments"},
        "$",
        errors,
    )
    _check_string(payload.get("schema_version"), "$.schema_version", errors)
    if payload.get("schema_version") != EXTRACTION_SCHEMA_VERSION:
        errors.append(f"$.schema_version: expected {EXTRACTION_SCHEMA_VERSION!r}")
    _check_nonempty_string(payload.get("content_id"), "$.content_id", errors)
    _check_nonempty_string(payload.get("creator_id"), "$.creator_id", errors)

    if "content_metadata" in payload:
        _validate_content_metadata(payload["content_metadata"], errors)
    if "pipeline" in payload:
        _validate_pipeline_metadata(payload["pipeline"], errors)

    moments = payload.get("moments")
    if not isinstance(moments, list):
        errors.append("$.moments: expected an array")
    else:
        local_ids: set[str] = set()
        for index, moment in enumerate(moments):
            _validate_moment(moment, f"$.moments[{index}]", local_ids, errors)

    if errors:
        raise ContractValidationError(errors)
    return payload


def validate_retrieval_plan(payload: object) -> dict[str, Any]:
    """Validate a planner result before graph or vector retrieval."""

    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ContractValidationError(["$: retrieval plan must be an object"])

    _check_keys(
        payload,
        {
            "schema_version",
            "creator_id",
            "intent",
            "graph",
            "semantic_query",
            "time_range",
            "entity_filters",
            "result_type",
            "top_k",
        },
        {
            "schema_version",
            "creator_id",
            "intent",
            "graph",
            "semantic_query",
            "result_type",
            "top_k",
        },
        "$",
        errors,
    )
    _check_string(payload.get("schema_version"), "$.schema_version", errors)
    if payload.get("schema_version") != RETRIEVAL_PLAN_SCHEMA_VERSION:
        errors.append(f"$.schema_version: expected {RETRIEVAL_PLAN_SCHEMA_VERSION!r}")
    _check_nonempty_string(payload.get("creator_id"), "$.creator_id", errors)
    _check_nonempty_string(payload.get("intent"), "$.intent", errors)
    _check_nonempty_string(payload.get("semantic_query"), "$.semantic_query", errors)
    if payload.get("result_type") not in RESULT_TYPES:
        errors.append(f"$.result_type: unknown result type {payload.get('result_type')!r}")
    _check_integer(payload.get("top_k"), "$.top_k", errors)
    if isinstance(payload.get("top_k"), int) and not 1 <= payload["top_k"] <= 100:
        errors.append("$.top_k: expected a value between 1 and 100")

    _validate_graph_constraints(payload.get("graph"), errors)
    _validate_time_range(payload.get("time_range"), errors)
    if "entity_filters" in payload:
        _validate_entity_filters(payload["entity_filters"], errors)

    if errors:
        raise ContractValidationError(errors)
    return payload


def _validate_content_metadata(value: object, errors: list[str]) -> None:
    path = "$.content_metadata"
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(value, {"title", "source_type", "duration_ms", "language"}, set(), path, errors)
    if "title" in value:
        _check_string(value["title"], f"{path}.title", errors)
    if "source_type" in value and value["source_type"] not in CONTENT_SOURCE_TYPES:
        errors.append(f"{path}.source_type: unknown source type")
    if "duration_ms" in value:
        _check_nonnegative_integer(value["duration_ms"], f"{path}.duration_ms", errors)
    if "language" in value:
        _check_string(value["language"], f"{path}.language", errors)


def _validate_pipeline_metadata(value: object, errors: list[str]) -> None:
    path = "$.pipeline"
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(value, {"version", "asr_model", "vision_model", "embedding_model"}, {"version"}, path, errors)
    _check_nonempty_string(value.get("version"), f"{path}.version", errors)
    for key in ("asr_model", "vision_model", "embedding_model"):
        if key in value:
            _check_string(value[key], f"{path}.{key}", errors)


def _validate_moment(value: object, path: str, seen_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(
        value,
        {
            "local_id", "start_ms", "end_ms", "transcript", "semantic_text",
            "entities", "relations", "evidence", "embedding",
        },
        {"local_id", "start_ms", "end_ms", "semantic_text", "entities", "relations", "evidence"},
        path,
        errors,
    )
    local_id = value.get("local_id")
    _check_nonempty_string(local_id, f"{path}.local_id", errors)
    if isinstance(local_id, str):
        if local_id in seen_ids:
            errors.append(f"{path}.local_id: duplicate moment local_id")
        seen_ids.add(local_id)
    _check_nonnegative_integer(value.get("start_ms"), f"{path}.start_ms", errors)
    _check_nonnegative_integer(value.get("end_ms"), f"{path}.end_ms", errors)
    if (
        isinstance(value.get("start_ms"), int)
        and isinstance(value.get("end_ms"), int)
        and value["end_ms"] <= value["start_ms"]
    ):
        errors.append(f"{path}: end_ms must be greater than start_ms")
    if "transcript" in value:
        _check_string(value["transcript"], f"{path}.transcript", errors)
    _check_nonempty_string(value.get("semantic_text"), f"{path}.semantic_text", errors)

    entities = value.get("entities")
    entity_ids: set[str] = set()
    if not isinstance(entities, list):
        errors.append(f"{path}.entities: expected an array")
    else:
        for index, entity in enumerate(entities):
            _validate_entity(entity, f"{path}.entities[{index}]", entity_ids, errors)

    relations = value.get("relations")
    if not isinstance(relations, list):
        errors.append(f"{path}.relations: expected an array")
    else:
        for index, relation in enumerate(relations):
            _validate_relation(relation, f"{path}.relations[{index}]", entity_ids, errors)

    _validate_evidence(value.get("evidence"), f"{path}.evidence", errors)
    if "embedding" in value and value["embedding"] is not None:
        _validate_embedding(value["embedding"], f"{path}.embedding", errors)


def _validate_entity(value: object, path: str, seen_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(
        value,
        {"local_id", "type", "name", "confidence", "evidence_refs", "explicit"},
        {"local_id", "type", "name", "confidence"},
        path,
        errors,
    )
    local_id = value.get("local_id")
    _check_nonempty_string(local_id, f"{path}.local_id", errors)
    if isinstance(local_id, str):
        if local_id in seen_ids:
            errors.append(f"{path}.local_id: duplicate entity local_id")
        seen_ids.add(local_id)
    if value.get("type") not in ENTITY_TYPES:
        errors.append(f"{path}.type: unknown entity type {value.get('type')!r}")
    _check_nonempty_string(value.get("name"), f"{path}.name", errors)
    _check_confidence(value.get("confidence"), f"{path}.confidence", errors)
    if "evidence_refs" in value:
        _validate_string_array(value["evidence_refs"], f"{path}.evidence_refs", errors)
    if "explicit" in value and not isinstance(value["explicit"], bool):
        errors.append(f"{path}.explicit: expected a boolean")


def _validate_relation(value: object, path: str, entity_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(
        value,
        {"subject", "predicate", "object", "confidence", "evidence_refs", "explicit"},
        {"subject", "predicate", "object", "confidence", "evidence_refs"},
        path,
        errors,
    )
    for key in ("subject", "object"):
        reference = value.get(key)
        if not isinstance(reference, str) or not reference:
            errors.append(f"{path}.{key}: expected a non-empty local reference")
        elif reference != "creator" and reference not in entity_ids:
            errors.append(f"{path}.{key}: unknown local reference {reference!r}")
    if value.get("predicate") not in RELATION_TYPES:
        errors.append(f"{path}.predicate: unknown relation {value.get('predicate')!r}")
    _check_confidence(value.get("confidence"), f"{path}.confidence", errors)
    _validate_string_array(value.get("evidence_refs"), f"{path}.evidence_refs", errors)
    if isinstance(value.get("evidence_refs"), list) and not value["evidence_refs"]:
        errors.append(f"{path}.evidence_refs: expected at least one reference")
    if "explicit" in value and not isinstance(value["explicit"], bool):
        errors.append(f"{path}.explicit: expected a boolean")


def _validate_evidence(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(
        value,
        {"asr_segment_ids", "frame_timestamps_ms", "frame_ids", "ocr_text", "ocr_item_ids"},
        set(),
        path,
        errors,
    )
    for key in ("asr_segment_ids", "frame_ids", "ocr_text", "ocr_item_ids"):
        if key in value:
            _validate_string_array(value[key], f"{path}.{key}", errors)
    if "frame_timestamps_ms" in value:
        timestamps = value["frame_timestamps_ms"]
        if not isinstance(timestamps, list):
            errors.append(f"{path}.frame_timestamps_ms: expected an array")
        else:
            for index, timestamp in enumerate(timestamps):
                _check_nonnegative_integer(timestamp, f"{path}.frame_timestamps_ms[{index}]", errors)


def _validate_embedding(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(
        value,
        {"model", "version", "dimension", "vector", "normalized"},
        {"model", "dimension", "vector"},
        path,
        errors,
    )
    _check_nonempty_string(value.get("model"), f"{path}.model", errors)
    if "version" in value:
        _check_nonempty_string(value["version"], f"{path}.version", errors)
    _check_integer(value.get("dimension"), f"{path}.dimension", errors)
    if isinstance(value.get("dimension"), int) and value["dimension"] < 1:
        errors.append(f"{path}.dimension: expected a positive integer")
    vector = value.get("vector")
    if not isinstance(vector, list):
        errors.append(f"{path}.vector: expected an array")
    else:
        if isinstance(value.get("dimension"), int) and len(vector) != value["dimension"]:
            errors.append(f"{path}.vector: length must equal dimension")
        for index, item in enumerate(vector):
            if not isinstance(item, (int, float)) or isinstance(item, bool):
                errors.append(f"{path}.vector[{index}]: expected a number")
    if "normalized" in value and not isinstance(value["normalized"], bool):
        errors.append(f"{path}.normalized: expected a boolean")


def _validate_graph_constraints(value: object, errors: list[str]) -> None:
    path = "$.graph"
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(value, {"relations", "entity_types", "filters"}, set(), path, errors)
    relations = value.get("relations", [])
    if not isinstance(relations, list):
        errors.append(f"{path}.relations: expected an array")
    else:
        for index, relation in enumerate(relations):
            if relation not in RELATION_TYPES:
                errors.append(f"{path}.relations[{index}]: unknown relation {relation!r}")
    entity_types = value.get("entity_types", [])
    if not isinstance(entity_types, list):
        errors.append(f"{path}.entity_types: expected an array")
    else:
        for index, entity_type in enumerate(entity_types):
            if entity_type not in ENTITY_TYPES:
                errors.append(f"{path}.entity_types[{index}]: unknown entity type {entity_type!r}")
    if "filters" in value:
        filters = value["filters"]
        if not isinstance(filters, dict):
            errors.append(f"{path}.filters: expected an object")
        else:
            filters_path = f"{path}.filters"
            _check_keys(filters, {"category", "color", "content_id", "entity_name", "relation"}, set(), filters_path, errors)
            for key, item in filters.items():
                if not isinstance(item, (str, int, float, bool)) or item is None:
                    errors.append(f"{filters_path}.{key}: expected a scalar")


def _validate_time_range(value: object, errors: list[str]) -> None:
    path = "$.time_range"
    if value is None:
        return
    if not isinstance(value, dict):
        errors.append(f"{path}: expected null or an object")
        return
    _check_keys(value, {"start_ms", "end_ms"}, {"start_ms", "end_ms"}, path, errors)
    _check_nonnegative_integer(value.get("start_ms"), f"{path}.start_ms", errors)
    _check_nonnegative_integer(value.get("end_ms"), f"{path}.end_ms", errors)
    if (
        isinstance(value.get("start_ms"), int)
        and isinstance(value.get("end_ms"), int)
        and value["end_ms"] <= value["start_ms"]
    ):
        errors.append(f"{path}: end_ms must be greater than start_ms")


def _validate_entity_filters(value: object, errors: list[str]) -> None:
    path = "$.entity_filters"
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return
    _check_keys(value, {"names", "types"}, set(), path, errors)
    if "names" in value:
        _validate_string_array(value["names"], f"{path}.names", errors)
    if "types" in value:
        _validate_string_array(value["types"], f"{path}.types", errors)
        if isinstance(value["types"], list):
            for index, entity_type in enumerate(value["types"]):
                if entity_type not in ENTITY_TYPES:
                    errors.append(f"{path}.types[{index}]: unknown entity type {entity_type!r}")


def _check_keys(value: dict[str, Any], allowed: set[str], required: set[str], path: str, errors: list[str]) -> None:
    for key in sorted(set(value) - allowed):
        errors.append(f"{path}: unknown property {key!r}")
    for key in sorted(required - set(value)):
        errors.append(f"{path}: missing required property {key!r}")


def _check_string(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{path}: expected a string")


def _check_nonempty_string(value: object, path: str, errors: list[str]) -> None:
    _check_string(value, path, errors)
    if isinstance(value, str) and not value.strip():
        errors.append(f"{path}: expected a non-empty string")


def _check_integer(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"{path}: expected an integer")


def _check_nonnegative_integer(value: object, path: str, errors: list[str]) -> None:
    _check_integer(value, path, errors)
    if isinstance(value, int) and not isinstance(value, bool) and value < 0:
        errors.append(f"{path}: expected a non-negative integer")


def _check_confidence(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{path}: expected a number")
    elif not 0 <= value <= 1:
        errors.append(f"{path}: expected a value between 0 and 1")


def _validate_string_array(value: object, path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path}: expected an array")
        return
    for index, item in enumerate(value):
        _check_nonempty_string(item, f"{path}[{index}]", errors)
