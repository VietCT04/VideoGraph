#!/usr/bin/env python3
"""Run deterministic graph/vector/hybrid retrieval checks over the demo metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any


RUNNER_VERSION = "0.2.0"
MODES = ("graph-only", "vector-only", "hybrid")
STAGES = ("planner", "graph", "vector", "fusion", "synthesis", "end_to_end")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def normalize_token(token: str) -> str:
    """Apply a small deterministic stem so 'recommended' matches 'recommend'."""

    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token


def tokenize(text: str) -> set[str]:
    return {normalize_token(token) for token in TOKEN_RE.findall(text.lower())}


def moment_text(moment: dict[str, Any]) -> str:
    parts = [
        str(moment.get("transcript", "")),
        str(moment.get("visual_text", "")),
        " ".join(str(value) for value in moment.get("contexts", [])),
    ]
    return " ".join(parts)


def graph_score(moment: dict[str, Any], query: dict[str, Any]) -> float:
    intent = query.get("graph_intent", {})
    predicates = set(intent.get("predicates", []))
    entity_ids = set(intent.get("entity_ids", []))
    relations = moment.get("relations", [])
    score = 0.0

    for relation in relations:
        if relation.get("predicate") in predicates:
            score += 3.0
        if relation.get("subject_id") in entity_ids or relation.get("object_id") in entity_ids:
            score += 2.0
    score += 2.0 * len(entity_ids.intersection(moment.get("entities", [])))
    return score


def vector_score(moment: dict[str, Any], query_text: str) -> float:
    query_tokens = tokenize(query_text)
    moment_tokens = tokenize(moment_text(moment))
    if not query_tokens:
        return 0.0

    overlap = query_tokens.intersection(moment_tokens)
    return len(overlap) / math.sqrt(len(query_tokens) * max(len(moment_tokens), 1))


def rank_graph(moments: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        moments,
        key=lambda moment: (-graph_score(moment, query), moment["moment_id"]),
    )


def rank_vector(moments: list[dict[str, Any]], query: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        moments,
        key=lambda moment: (-vector_score(moment, query["text"]), moment["moment_id"]),
    )


def rank_hybrid(
    graph: list[dict[str, Any]],
    vector: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    weights = weights or {"graph": 1.0, "vector": 1.0}
    graph_weight = float(weights.get("graph", 1.0))
    vector_weight = float(weights.get("vector", 1.0))
    graph_rank = {moment["moment_id"]: index + 1 for index, moment in enumerate(graph)}
    vector_rank = {moment["moment_id"]: index + 1 for index, moment in enumerate(vector)}
    moments_by_id = {moment["moment_id"]: moment for moment in graph + vector}
    return sorted(
        moments_by_id.values(),
        key=lambda moment: (
            -(
                graph_weight / (60 + graph_rank[moment["moment_id"]])
                + vector_weight / (60 + vector_rank[moment["moment_id"]])
            ),
            moment["moment_id"],
        ),
    )


def retrieval_metrics(
    ranked: list[dict[str, Any]],
    query: dict[str, Any],
    retrieval_top_k: int = 10,
) -> dict[str, float | int]:
    expected = set(query["expected_moment_ids"])
    expected_entities = set(query.get("expected_entity_ids", []))
    ranked = ranked[:retrieval_top_k]
    ranked_ids = [moment["moment_id"] for moment in ranked]
    top_five = set(ranked_ids[:5])
    top_ten = set(ranked_ids[:10])
    first_rank = next(
        (index + 1 for index, moment_id in enumerate(ranked_ids) if moment_id in expected),
        None,
    )
    top_ten_entities = {
        entity_id
        for moment in ranked[:10]
        for entity_id in moment.get("entities", [])
    }
    return {
        "recall_at_5": len(expected.intersection(top_five)) / len(expected),
        "recall_at_10": len(expected.intersection(top_ten)) / len(expected),
        "mrr": 1 / first_rank if first_rank else 0.0,
        "evidence_hit_rate": int(bool(expected.intersection(top_ten))),
        "structured_answer_hit_rate": int(bool(expected_entities.intersection(top_ten_entities))),
    }


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)


def summarize_timings(rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for stage in STAGES:
        values = [row[stage] for row in rows]
        summary[stage] = {
            "mean_ms": round(statistics.fmean(values), 3),
            "median_ms": round(statistics.median(values), 3),
            "max_ms": round(max(values), 3),
        }
    return summary


def average_metrics(rows: list[dict[str, float | int]]) -> dict[str, float]:
    names = (
        "recall_at_5",
        "recall_at_10",
        "mrr",
        "evidence_hit_rate",
        "structured_answer_hit_rate",
    )
    return {name: round(statistics.fmean(float(row[name]) for row in rows), 4) for name in names}


def sha256_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run_benchmark(
    manifest: dict[str, Any],
    queries_file: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    retrieval_top_k = int(config.get("retrieval_top_k", 10))
    reranking_weights = config.get("reranking_weights", {"graph": 1.0, "vector": 1.0})
    if not isinstance(reranking_weights, dict):
        raise ValueError("reranking_weights must be an object")
    effective_config = {
        "retrieval_top_k": retrieval_top_k,
        "reranking_weights": {
            "graph": float(reranking_weights.get("graph", 1.0)),
            "vector": float(reranking_weights.get("vector", 1.0)),
        },
    }
    moments_by_creator: dict[str, list[dict[str, Any]]] = {}
    for moment in manifest["moments"]:
        moments_by_creator.setdefault(moment["creator_id"], []).append(moment)

    per_query: list[dict[str, Any]] = []
    mode_metrics: dict[str, list[dict[str, float | int]]] = {mode: [] for mode in MODES}
    mode_timings: dict[str, list[dict[str, float]]] = {mode: [] for mode in MODES}
    category_metrics: dict[str, dict[str, list[dict[str, float | int]]]] = {
        category: {mode: [] for mode in MODES}
        for category in {query["category"] for query in queries_file["queries"]}
    }

    for query in queries_file["queries"]:
        creator_moments = moments_by_creator.get(query["creator_id"], [])
        planner_start = time.perf_counter()
        plan = {
            "creator_id": query["creator_id"],
            "graph_intent": query.get("graph_intent", {}),
            "semantic_query": query["text"],
        }
        planner_ms = elapsed_ms(planner_start)

        graph_start = time.perf_counter()
        graph_ranked = rank_graph(creator_moments, query)
        graph_ms = elapsed_ms(graph_start)

        vector_start = time.perf_counter()
        vector_ranked = rank_vector(creator_moments, query)
        vector_ms = elapsed_ms(vector_start)

        fusion_start = time.perf_counter()
        hybrid_ranked = rank_hybrid(graph_ranked, vector_ranked, effective_config["reranking_weights"])
        fusion_ms = elapsed_ms(fusion_start)

        mode_rankings = {
            "graph-only": graph_ranked,
            "vector-only": vector_ranked,
            "hybrid": hybrid_ranked,
        }
        query_modes: dict[str, Any] = {}
        for mode in MODES:
            end_to_end_ms = round(planner_ms + graph_ms + vector_ms + fusion_ms, 3)
            stage_timings = {
                "planner": planner_ms,
                "graph": graph_ms if mode in ("graph-only", "hybrid") else 0.0,
                "vector": vector_ms if mode in ("vector-only", "hybrid") else 0.0,
                "fusion": fusion_ms if mode == "hybrid" else 0.0,
                "synthesis": 0.0,
                "end_to_end": end_to_end_ms,
            }
            metrics = retrieval_metrics(mode_rankings[mode], query, retrieval_top_k)
            mode_metrics[mode].append(metrics)
            mode_timings[mode].append(stage_timings)
            category_metrics[query["category"]][mode].append(metrics)
            query_modes[mode] = {
                "ranked_moment_ids_at_10": [
                    moment["moment_id"] for moment in mode_rankings[mode][:retrieval_top_k][:10]
                ],
                "metrics": metrics,
                "timings_ms": stage_timings,
            }

        per_query.append(
            {
                "query_id": query["query_id"],
                "category": query["category"],
                "creator_id": query["creator_id"],
                "expected_moment_ids": query["expected_moment_ids"],
                "modes": query_modes,
                "plan": plan,
            }
        )

    return {
        "runner": {
            "name": "videograph-fixture-benchmark",
            "version": RUNNER_VERSION,
            "python": platform.python_version(),
        },
        "configuration": effective_config,
        "dataset": {
            "dataset_id": manifest["dataset_id"],
            "version": manifest["version"],
            "creator_count": len(manifest["creators"]),
            "content_count": len(manifest["content"]),
            "moment_count": len(manifest["moments"]),
            "query_count": len(queries_file["queries"]),
        },
        "measurement_notes": [
            (
                "Graph and vector retrieval are deterministic in-memory fixture baselines, "
                "not Neo4j or pgvector measurements."
            ),
            (
                "Stage timings measure this Python harness on the current machine and are "
                "not model, GPU, or service latency claims."
            ),
            (
                "Only retrieval_top_k and reranking_weights alter this metadata-only fixture; "
                "chunking, frame, and prompt settings remain unmeasured here."
            ),
            (
                "Video indexing wall-clock time and peak VRAM are not measured because this "
                "dataset contains metadata only."
            ),
            "No synthesis stage is invoked; synthesis timing is reported as zero.",
        ],
        "metrics": {mode: average_metrics(rows) for mode, rows in mode_metrics.items()},
        "metrics_by_category": {
            category: {mode: average_metrics(rows) for mode, rows in modes.items()}
            for category, modes in category_metrics.items()
        },
        "stage_timings_ms": {
            mode: summarize_timings(rows) for mode, rows in mode_timings.items()
        },
        "indexing_measurement": {
            "status": "not_measured",
            "reason": "The controlled fixture has no audiovisual media or indexing pipeline input.",
        },
        "queries": per_query,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# VideoGraph fixture benchmark",
        "",
        f"- Dataset: `{report['dataset']['dataset_id']}` v{report['dataset']['version']}",
        f"- Content records: {report['dataset']['content_count']}",
        f"- Ground-truth Moments: {report['dataset']['moment_count']}",
        f"- Queries: {report['dataset']['query_count']}",
        "",
        "## Retrieval metrics",
        "",
        "| Mode | Recall@5 | Recall@10 | MRR | Evidence hit | Structured answer hit |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for mode in MODES:
        metrics = report["metrics"][mode]
        lines.append(
            f"| {mode} | {metrics['recall_at_5']:.4f} | {metrics['recall_at_10']:.4f} | "
            f"{metrics['mrr']:.4f} | {metrics['evidence_hit_rate']:.4f} | "
            f"{metrics['structured_answer_hit_rate']:.4f} |"
        )

    lines.extend(["", "## Stage timings", "", "Timings are local harness measurements in milliseconds.", ""])
    lines.extend([
        "| Mode | Planner mean | Graph mean | Vector mean | Fusion mean | Synthesis mean | End-to-end mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for mode in MODES:
        timings = report["stage_timings_ms"][mode]
        lines.append(
            f"| {mode} | {timings['planner']['mean_ms']:.3f} | {timings['graph']['mean_ms']:.3f} | "
            f"{timings['vector']['mean_ms']:.3f} | {timings['fusion']['mean_ms']:.3f} | "
            f"{timings['synthesis']['mean_ms']:.3f} | {timings['end_to_end']['mean_ms']:.3f} |"
        )

    lines.extend(["", "## Measurement notes", ""])
    lines.extend(f"- {note}" for note in report["measurement_notes"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    default_dataset = root / "datasets" / "creator-memory-demo"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=default_dataset / "manifest.json")
    parser.add_argument("--queries", type=Path, default=default_dataset / "queries.json")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional directory; writes benchmark-report.json and benchmark-report.md.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json(args.manifest)
    queries_file = load_json(args.queries)
    report = run_benchmark(manifest, queries_file)
    report["inputs_sha256"] = sha256_files([args.manifest, args.queries])
    markdown = render_markdown(report)

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "benchmark-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (args.output_dir / "benchmark-report.md").write_text(markdown, encoding="utf-8")

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
