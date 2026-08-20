#!/usr/bin/env python3
"""Evaluate safe benchmark configuration candidates without applying code changes."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from .run_benchmark import load_json, run_benchmark, sha256_files
except ImportError:
    from run_benchmark import load_json, run_benchmark, sha256_files


SAFE_CONFIG_FIELDS = (
    "chunk_target_duration_s",
    "frames_per_chunk",
    "vlm_prompt_version",
    "reranking_weights",
    "retrieval_top_k",
)
_SAFE_FIELD_SET = frozenset(SAFE_CONFIG_FIELDS)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DEFAULT_CONFIG: dict[str, Any] = {
    "chunk_target_duration_s": 20.0,
    "frames_per_chunk": 8,
    "vlm_prompt_version": "v1",
    "reranking_weights": {"graph": 1.0, "vector": 1.0},
    "retrieval_top_k": 10,
}


class ExperimentValidationError(ValueError):
    """Raised when an experiment or candidate leaves the safe configuration surface."""


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value))


@dataclass(frozen=True)
class OptimizationConfig:
    """The only configuration a candidate is allowed to change."""

    chunk_target_duration_s: float
    frames_per_chunk: int
    vlm_prompt_version: str
    reranking_weights: dict[str, float]
    retrieval_top_k: int

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None = None) -> "OptimizationConfig":
        merged = _copy_mapping(DEFAULT_CONFIG)
        if values is not None:
            unknown = set(values) - _SAFE_FIELD_SET
            if unknown:
                raise ExperimentValidationError(
                    f"Unsupported configuration field(s): {', '.join(sorted(unknown))}"
                )
            for key, value in values.items():
                if key == "reranking_weights":
                    if not isinstance(value, Mapping):
                        raise ExperimentValidationError("reranking_weights must be an object")
                    merged[key] = {**merged[key], **dict(value)}
                else:
                    merged[key] = value

        chunk_target_duration_s = merged["chunk_target_duration_s"]
        if not _is_number(chunk_target_duration_s) or not 1 <= chunk_target_duration_s <= 120:
            raise ExperimentValidationError("chunk_target_duration_s must be between 1 and 120 seconds")

        frames_per_chunk = merged["frames_per_chunk"]
        if (
            not isinstance(frames_per_chunk, int)
            or isinstance(frames_per_chunk, bool)
            or not 1 <= frames_per_chunk <= 64
        ):
            raise ExperimentValidationError("frames_per_chunk must be an integer between 1 and 64")

        vlm_prompt_version = merged["vlm_prompt_version"]
        if not isinstance(vlm_prompt_version, str) or not _IDENTIFIER_RE.fullmatch(vlm_prompt_version):
            raise ExperimentValidationError("vlm_prompt_version must be a short identifier")

        reranking_weights = merged["reranking_weights"]
        if not isinstance(reranking_weights, Mapping) or set(reranking_weights) != {"graph", "vector"}:
            raise ExperimentValidationError("reranking_weights must contain only graph and vector")
        if not all(_is_number(value) and 0 <= value <= 10 for value in reranking_weights.values()):
            raise ExperimentValidationError("reranking weights must be numbers between 0 and 10")
        if sum(float(value) for value in reranking_weights.values()) <= 0:
            raise ExperimentValidationError("at least one reranking weight must be positive")

        retrieval_top_k = merged["retrieval_top_k"]
        if not isinstance(retrieval_top_k, int) or isinstance(retrieval_top_k, bool) or not 1 <= retrieval_top_k <= 50:
            raise ExperimentValidationError("retrieval_top_k must be an integer between 1 and 50")

        return cls(
            chunk_target_duration_s=round(float(chunk_target_duration_s), 3),
            frames_per_chunk=frames_per_chunk,
            vlm_prompt_version=vlm_prompt_version,
            reranking_weights={key: round(float(value), 3) for key, value in reranking_weights.items()},
            retrieval_top_k=retrieval_top_k,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "chunk_target_duration_s": self.chunk_target_duration_s,
            "frames_per_chunk": self.frames_per_chunk,
            "vlm_prompt_version": self.vlm_prompt_version,
            "reranking_weights": dict(self.reranking_weights),
            "retrieval_top_k": self.retrieval_top_k,
        }


def apply_candidate_changes(
    baseline: OptimizationConfig,
    changes: Mapping[str, Any],
) -> OptimizationConfig:
    """Merge and validate a candidate without executing candidate-provided code."""

    if not isinstance(changes, Mapping):
        raise ExperimentValidationError("candidate changes must be an object")
    unknown = set(changes) - _SAFE_FIELD_SET
    if unknown:
        raise ExperimentValidationError(
            f"Unsupported candidate field(s): {', '.join(sorted(unknown))}"
        )
    merged = baseline.as_dict()
    for key, value in changes.items():
        if key == "reranking_weights":
            if not isinstance(value, Mapping):
                raise ExperimentValidationError("reranking_weights must be an object")
            merged[key] = {**merged[key], **dict(value)}
        else:
            merged[key] = value
    return OptimizationConfig.from_mapping(merged)


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    changes: dict[str, Any]
    rationale: str | None = None
    patch_proposal: dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CandidateSpec":
        allowed = {"candidate_id", "changes", "rationale", "patch_proposal"}
        unknown = set(value) - allowed
        if unknown:
            raise ExperimentValidationError(
                f"Unsupported candidate property/properties: {', '.join(sorted(unknown))}"
            )
        candidate_id = value.get("candidate_id")
        if not isinstance(candidate_id, str) or not _IDENTIFIER_RE.fullmatch(candidate_id):
            raise ExperimentValidationError("candidate_id must be a short identifier")
        changes = value.get("changes")
        if not isinstance(changes, Mapping) or not changes:
            raise ExperimentValidationError("candidate changes must be a non-empty object")
        if "rationale" in value and value["rationale"] is not None and not isinstance(value["rationale"], str):
            raise ExperimentValidationError("candidate rationale must be a string")
        patch_proposal = value.get("patch_proposal")
        if patch_proposal is not None and not isinstance(patch_proposal, Mapping):
            raise ExperimentValidationError("patch_proposal must be an object")
        if patch_proposal is not None:
            proposal_unknown = set(patch_proposal) - {"summary", "notes", "target_config_fields"}
            if proposal_unknown:
                raise ExperimentValidationError(
                    "Unsupported patch proposal property/properties: "
                    + ", ".join(sorted(proposal_unknown))
                )
            target_config_fields = patch_proposal.get("target_config_fields")
            if target_config_fields is not None and (
                not isinstance(target_config_fields, list)
                or not all(isinstance(field, str) and field in changes for field in target_config_fields)
            ):
                raise ExperimentValidationError(
                    "patch proposal fields must name changed safe configuration fields"
                )
        return cls(
            candidate_id=candidate_id,
            changes=_copy_mapping(changes),
            rationale=value.get("rationale"),
            patch_proposal=_copy_mapping(patch_proposal) if patch_proposal is not None else None,
        )

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"candidate_id": self.candidate_id, "changes": _copy_mapping(self.changes)}
        if self.rationale is not None:
            result["rationale"] = self.rationale
        if self.patch_proposal is not None:
            result["patch_proposal"] = _copy_mapping(self.patch_proposal)
        return result


@dataclass(frozen=True)
class EvaluationGates:
    max_latency_ms: float | None = None
    max_cost_units: float | None = None
    max_quality_regression: float = 0.0
    min_objective_delta: float = 0.0
    minimum_metrics: dict[str, float] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "EvaluationGates":
        value = value or {}
        allowed = {
            "max_latency_ms",
            "max_cost_units",
            "max_quality_regression",
            "min_objective_delta",
            "minimum_metrics",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ExperimentValidationError(
                f"Unsupported gate property/properties: {', '.join(sorted(unknown))}"
            )
        numeric: dict[str, float | None] = {}
        for key in ("max_latency_ms", "max_cost_units", "max_quality_regression", "min_objective_delta"):
            raw = value.get(key)
            if raw is not None and (
                not _is_number(raw)
                or (
                    key in {"max_latency_ms", "max_cost_units", "max_quality_regression"}
                    and raw < 0
                )
            ):
                raise ExperimentValidationError(f"{key} must be a non-negative number")
            numeric[key] = float(raw) if raw is not None else None
        minimum_metrics = value.get("minimum_metrics", {})
        if not isinstance(minimum_metrics, Mapping):
            raise ExperimentValidationError("minimum_metrics must be an object")
        if not all(isinstance(key, str) and _is_number(metric) for key, metric in minimum_metrics.items()):
            raise ExperimentValidationError("minimum_metrics values must be numeric")
        return cls(
            max_latency_ms=numeric["max_latency_ms"],
            max_cost_units=numeric["max_cost_units"],
            max_quality_regression=numeric["max_quality_regression"] or 0.0,
            min_objective_delta=numeric["min_objective_delta"] or 0.0,
            minimum_metrics={key: float(metric) for key, metric in minimum_metrics.items()},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_latency_ms": self.max_latency_ms,
            "max_cost_units": self.max_cost_units,
            "max_quality_regression": self.max_quality_regression,
            "min_objective_delta": self.min_objective_delta,
            "minimum_metrics": dict(self.minimum_metrics or {}),
        }


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    benchmark_version: str
    objective_metric: str
    baseline_config: OptimizationConfig
    candidates: tuple[CandidateSpec, ...]
    gates: EvaluationGates
    patch_proposals_enabled: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExperimentSpec":
        allowed = {
            "experiment_id",
            "benchmark_version",
            "objective_metric",
            "baseline_config",
            "candidates",
            "gates",
            "patch_proposals_enabled",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ExperimentValidationError(
                f"Unsupported experiment property/properties: {', '.join(sorted(unknown))}"
            )
        experiment_id = value.get("experiment_id")
        benchmark_version = value.get("benchmark_version")
        objective_metric = value.get("objective_metric")
        if not isinstance(experiment_id, str) or not _IDENTIFIER_RE.fullmatch(experiment_id):
            raise ExperimentValidationError("experiment_id must be a short identifier")
        if not isinstance(benchmark_version, str) or not _IDENTIFIER_RE.fullmatch(benchmark_version):
            raise ExperimentValidationError("benchmark_version must be a short identifier")
        if not isinstance(objective_metric, str) or not objective_metric:
            raise ExperimentValidationError("objective_metric must be a metric path")
        candidates = value.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ExperimentValidationError("candidates must be a non-empty list")
        parsed_candidates = tuple(CandidateSpec.from_mapping(candidate) for candidate in candidates)
        candidate_ids = [candidate.candidate_id for candidate in parsed_candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ExperimentValidationError("candidate_id values must be unique")
        patch_proposals_enabled = value.get("patch_proposals_enabled", True)
        if not isinstance(patch_proposals_enabled, bool):
            raise ExperimentValidationError("patch_proposals_enabled must be boolean")
        return cls(
            experiment_id=experiment_id,
            benchmark_version=benchmark_version,
            objective_metric=objective_metric,
            baseline_config=OptimizationConfig.from_mapping(value.get("baseline_config")),
            candidates=parsed_candidates,
            gates=EvaluationGates.from_mapping(value.get("gates")),
            patch_proposals_enabled=patch_proposals_enabled,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "benchmark_version": self.benchmark_version,
            "objective_metric": self.objective_metric,
            "baseline_config": self.baseline_config.as_dict(),
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "gates": self.gates.as_dict(),
            "patch_proposals_enabled": self.patch_proposals_enabled,
        }


BenchmarkRunner = Callable[[OptimizationConfig], dict[str, Any]]
CandidateGenerator = Callable[[OptimizationConfig], Iterable[CandidateSpec]]


def load_experiment_spec(path: Path) -> ExperimentSpec:
    return ExperimentSpec.from_mapping(load_json(path))


def metric_at_path(report: Mapping[str, Any], path: str) -> float:
    value: Any = report
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise ExperimentValidationError(f"Metric path not found: {path}")
        value = value[part]
    if not _is_number(value):
        raise ExperimentValidationError(f"Metric path is not numeric: {path}")
    return float(value)


def deterministic_latency_ms(config: OptimizationConfig) -> float:
    """Return a fixture-only latency model, not a service performance measurement."""

    return round(
        100.0
        + config.chunk_target_duration_s * 0.2
        + config.frames_per_chunk * 1.25
        + config.retrieval_top_k * 0.35
        + sum(config.reranking_weights.values()) * 0.5,
        3,
    )


def deterministic_cost_units(config: OptimizationConfig) -> float:
    """Return a relative fixture cost model, not provider billing or GPU usage."""

    return round(
        1.0
        + config.chunk_target_duration_s * 0.01
        + config.frames_per_chunk * 0.08
        + config.retrieval_top_k * 0.015
        + sum(config.reranking_weights.values()) * 0.05,
        3,
    )


def fixture_runner(manifest_path: Path, queries_path: Path) -> BenchmarkRunner:
    """Create a runner over the same versioned fixture files used by issue #23."""

    manifest = load_json(manifest_path)
    queries_file = load_json(queries_path)

    def run(config: OptimizationConfig) -> dict[str, Any]:
        report = run_benchmark(manifest, queries_file, config.as_dict())
        report["optimization_measurement"] = {
            "latency_ms": deterministic_latency_ms(config),
            "cost_units": deterministic_cost_units(config),
            "status": "deterministic_fixture_model",
            "notes": [
                "Latency and cost are relative fixture estimates for gate demonstrations.",
                "They are not hosted-service, model, GPU, or provider billing measurements.",
            ],
        }
        report["inputs_sha256"] = sha256_files([manifest_path, queries_path])
        return report

    return run


def _run_snapshot(
    report: Mapping[str, Any],
    objective_metric: str,
) -> dict[str, Any]:
    measurement = report.get("optimization_measurement")
    if not isinstance(measurement, Mapping):
        raise ExperimentValidationError("runner must return optimization_measurement")
    latency_ms = measurement.get("latency_ms")
    cost_units = measurement.get("cost_units")
    if not _is_number(latency_ms) or not _is_number(cost_units):
        raise ExperimentValidationError("runner latency_ms and cost_units must be numeric")
    return {
        "objective": metric_at_path(report, objective_metric),
        "metrics": _copy_mapping(report.get("metrics", {})),
        "latency_ms": round(float(latency_ms), 3),
        "cost_units": round(float(cost_units), 3),
        "inputs_sha256": report.get("inputs_sha256"),
        "runner": _copy_mapping(report.get("runner", {})),
    }


def _patch_proposal(candidate: CandidateSpec, enabled: bool) -> dict[str, Any] | None:
    if candidate.patch_proposal is None or not enabled:
        return None
    allowed = {"summary", "notes", "target_config_fields"}
    unknown = set(candidate.patch_proposal) - allowed
    if unknown:
        raise ExperimentValidationError(
            f"Unsupported patch proposal property/properties: {', '.join(sorted(unknown))}"
        )
    target_config_fields = candidate.patch_proposal.get("target_config_fields", list(candidate.changes))
    if not isinstance(target_config_fields, list) or not all(
        isinstance(field, str) and field in candidate.changes for field in target_config_fields
    ):
        raise ExperimentValidationError("patch proposal fields must name changed safe configuration fields")
    return {
        "candidate_id": candidate.candidate_id,
        "summary": candidate.patch_proposal.get("summary", "Apply the accepted configuration candidate"),
        "notes": candidate.patch_proposal.get("notes"),
        "target_config_fields": target_config_fields,
        "applied": False,
        "deployment_requested": False,
    }


def evaluate_experiment(spec: ExperimentSpec, runner: BenchmarkRunner) -> dict[str, Any]:
    """Run baseline and candidates through a typed runner and return an auditable report."""

    baseline_report = runner(spec.baseline_config)
    baseline = _run_snapshot(baseline_report, spec.objective_metric)
    if baseline["runner"].get("version") not in {None, spec.benchmark_version}:
        raise ExperimentValidationError(
            f"Runner version {baseline['runner'].get('version')} does not match {spec.benchmark_version}"
        )
    baseline_runner_version = baseline["runner"].get("version")
    baseline_inputs_sha256 = baseline.get("inputs_sha256")

    candidate_results: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for candidate in spec.candidates:
        config = apply_candidate_changes(spec.baseline_config, candidate.changes)
        report = runner(config)
        snapshot = _run_snapshot(report, spec.objective_metric)
        candidate_runner_version = snapshot["runner"].get("version")
        if baseline_runner_version is not None and candidate_runner_version != baseline_runner_version:
            raise ExperimentValidationError("all candidates must use the same benchmark runner version")
        if baseline_inputs_sha256 is not None and snapshot.get("inputs_sha256") != baseline_inputs_sha256:
            raise ExperimentValidationError("all candidates must use the same benchmark inputs")
        reasons: list[str] = []
        quality_delta = snapshot["objective"] - baseline["objective"]
        if quality_delta < -spec.gates.max_quality_regression:
            reasons.append("quality_regression")
        if quality_delta < spec.gates.min_objective_delta:
            reasons.append("objective_threshold_not_met")
        if spec.gates.max_latency_ms is not None and snapshot["latency_ms"] > spec.gates.max_latency_ms:
            reasons.append("latency_gate_failed")
        if spec.gates.max_cost_units is not None and snapshot["cost_units"] > spec.gates.max_cost_units:
            reasons.append("cost_gate_failed")
        for metric_path, minimum in (spec.gates.minimum_metrics or {}).items():
            if metric_at_path(report, metric_path) < minimum:
                reasons.append(f"minimum_metric_failed:{metric_path}")
        result = {
            "candidate_id": candidate.candidate_id,
            "rationale": candidate.rationale,
            "config": config.as_dict(),
            "objective": snapshot["objective"],
            "quality_delta": round(quality_delta, 4),
            "metrics": snapshot["metrics"],
            "latency_ms": snapshot["latency_ms"],
            "cost_units": snapshot["cost_units"],
            "decision": "rejected" if reasons else "accepted",
            "reasons": reasons,
        }
        candidate_results.append(result)
        proposal = _patch_proposal(candidate, spec.patch_proposals_enabled)
        if proposal is not None:
            proposal["decision"] = result["decision"]
            proposals.append(proposal)

    accepted = [result for result in candidate_results if result["decision"] == "accepted"]
    best_candidate = min(
        accepted,
        key=lambda result: (-result["objective"], result["latency_ms"], result["cost_units"], result["candidate_id"]),
        default=None,
    )
    return {
        "experiment": spec.as_dict(),
        "baseline": baseline,
        "candidates": candidate_results,
        "best_candidate": best_candidate,
        "patch_proposals": proposals,
        "execution_policy": {
            "candidate_input": "validated_configuration_only",
            "allowed_configuration_fields": list(SAFE_CONFIG_FIELDS),
            "arbitrary_code_execution": False,
            "patch_application": False,
            "deployment": False,
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    experiment = report["experiment"]
    baseline = report["baseline"]
    lines = [
        "# VideoGraph constrained optimization report",
        "",
        f"- Experiment: `{experiment['experiment_id']}`",
        f"- Benchmark version: `{experiment['benchmark_version']}`",
        f"- Objective: `{experiment['objective_metric']}`",
        "",
        "## Baseline",
        "",
        (
            f"Objective: `{baseline['objective']:.4f}`; "
            f"latency: `{baseline['latency_ms']:.3f} ms`; "
            f"cost units: `{baseline['cost_units']:.3f}`."
        ),
        "",
        "## Candidates",
        "",
        "| Candidate | Objective | Delta | Latency ms | Cost units | Decision | Reasons |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for candidate in report["candidates"]:
        lines.append(
            f"| {candidate['candidate_id']} | {candidate['objective']:.4f} | {candidate['quality_delta']:.4f} | "
            f"{candidate['latency_ms']:.3f} | {candidate['cost_units']:.3f} | {candidate['decision']} | "
            f"{', '.join(candidate['reasons']) or '-'} |"
        )
    best = report.get("best_candidate")
    lines.extend(
        [
            "",
            "## Safety boundary",
            "",
            "- Candidates are validated configuration data; arbitrary code is not executed.",
            "- Patch proposals are report metadata only and are never applied or deployed.",
            "- Latency and cost units are deterministic fixture models, not production measurements.",
            "",
            f"Best candidate: `{best['candidate_id']}`." if best else "Best candidate: none passed all gates.",
        ]
    )
    return "\n".join(lines) + "\n"


def candidate_mappings(base_config: OptimizationConfig, generator: CandidateGenerator) -> tuple[CandidateSpec, ...]:
    """Validate candidates returned by an external proposer before evaluation."""

    candidates = tuple(generator(base_config))
    if not candidates:
        raise ExperimentValidationError("candidate generator returned no candidates")
    for candidate in candidates:
        if not isinstance(candidate, CandidateSpec):
            raise ExperimentValidationError("candidate generator must return CandidateSpec values")
        apply_candidate_changes(base_config, candidate.changes)
    return candidates
