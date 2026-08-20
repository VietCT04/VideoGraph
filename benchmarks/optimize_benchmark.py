#!/usr/bin/env python3
"""Run a constrained optimization experiment over the fixture benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .autonomous_optimization import (
        evaluate_experiment,
        fixture_runner,
        load_experiment_spec,
        render_markdown,
    )
except ImportError:
    from autonomous_optimization import evaluate_experiment, fixture_runner, load_experiment_spec, render_markdown


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    dataset = root / "datasets" / "creator-memory-demo"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment",
        type=Path,
        default=root / "benchmarks" / "experiments" / "fixture-optimization.json",
    )
    parser.add_argument("--manifest", type=Path, default=dataset / "manifest.json")
    parser.add_argument("--queries", type=Path, default=dataset / "queries.json")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory; writes optimization-report.json and optimization-report.md.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = load_experiment_spec(args.experiment)
    report = evaluate_experiment(spec, fixture_runner(args.manifest, args.queries))
    markdown = render_markdown(report)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "optimization-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (args.output_dir / "optimization-report.md").write_text(markdown, encoding="utf-8")
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
