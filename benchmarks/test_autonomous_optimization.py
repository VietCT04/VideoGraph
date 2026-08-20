#!/usr/bin/env python3
"""Focused checks for the constrained optimization loop."""

from __future__ import annotations

import unittest
from pathlib import Path

from benchmarks.autonomous_optimization import (
    CandidateSpec,
    ExperimentSpec,
    ExperimentValidationError,
    OptimizationConfig,
    apply_candidate_changes,
    evaluate_experiment,
    fixture_runner,
    load_experiment_spec,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "creator-memory-demo"


class AutonomousOptimizationTests(unittest.TestCase):
    def test_unknown_candidate_field_is_rejected(self) -> None:
        with self.assertRaises(ExperimentValidationError):
            apply_candidate_changes(OptimizationConfig.from_mapping(), {"shell_command": "rm -rf"})

    def test_out_of_range_configuration_is_rejected(self) -> None:
        with self.assertRaises(ExperimentValidationError):
            OptimizationConfig.from_mapping({"retrieval_top_k": 1000})

    def test_candidate_generator_shape_is_validated_by_spec(self) -> None:
        with self.assertRaises(ExperimentValidationError):
            CandidateSpec.from_mapping(
                {
                    "candidate_id": "bad",
                    "changes": {"retrieval_top_k": 5},
                    "patch_proposal": {"diff": "code"},
                }
            )

    def test_fixture_experiment_returns_gated_result_and_non_applied_proposal(self) -> None:
        spec = load_experiment_spec(ROOT / "benchmarks" / "experiments" / "fixture-optimization.json")
        report = evaluate_experiment(
            spec,
            fixture_runner(DATASET / "manifest.json", DATASET / "queries.json"),
        )
        self.assertEqual(len(report["candidates"]), 2)
        self.assertIn(report["candidates"][0]["decision"], {"accepted", "rejected"})
        self.assertEqual(report["patch_proposals"][0]["applied"], False)
        self.assertEqual(report["execution_policy"]["deployment"], False)

    def test_quality_regression_fails_gate(self) -> None:
        spec = ExperimentSpec.from_mapping(
            {
                "experiment_id": "regression-test",
                "benchmark_version": "test",
                "objective_metric": "metrics.hybrid.recall_at_10",
                "baseline_config": {},
                "gates": {"max_quality_regression": 0},
                "candidates": [
                    {
                        "candidate_id": "smaller-top-k",
                        "changes": {"retrieval_top_k": 1},
                    }
                ],
            }
        )

        def runner(config: OptimizationConfig) -> dict[str, object]:
            quality = 1.0 if config.retrieval_top_k == 10 else 0.5
            return {
                "runner": {"version": "test"},
                "metrics": {"hybrid": {"recall_at_10": quality}},
                "optimization_measurement": {"latency_ms": 10, "cost_units": 1},
            }

        report = evaluate_experiment(spec, runner)
        self.assertEqual(report["candidates"][0]["decision"], "rejected")
        self.assertIn("quality_regression", report["candidates"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
