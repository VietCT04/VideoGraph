# Fixture benchmark harness

`run_benchmark.py` is a dependency-free, reproducible harness for the synthetic
metadata fixture from issue #22. It loads `manifest.json` and `queries.json`, scopes
Moments to the requested creator, and evaluates three explicit baselines:

- `graph-only` — controlled relation/entity intent matching
- `vector-only` — deterministic lexical matching over transcript, visual text, and context
- `hybrid` — reciprocal-rank fusion of those two fixture baselines

Run the Markdown report with:

```text
python benchmarks/run_benchmark.py
```

Run machine-readable output or write both report formats:

```text
python benchmarks/run_benchmark.py --format json
python benchmarks/run_benchmark.py --output-dir benchmarks/results
```

The report includes Recall@5/10, MRR, evidence hit rate, structured-answer hit rate,
per-category metrics, and planner/graph/vector/fusion/synthesis/end-to-end timings.
The report is deterministic in ranking and metric definitions and includes hashes of the
fixture inputs. Timings are measurements of the local Python harness, not claims about
Neo4j, pgvector, model, GPU, or hosted-service performance. Video indexing wall-clock
time and peak VRAM are explicitly reported as `not_measured` because the dataset has no
media blobs.

## Constrained optimization loop

`optimize_benchmark.py` evaluates a versioned experiment specification from
`benchmarks/experiments/` against the same fixture baseline. Candidates may change only
the typed fields `chunk_target_duration_s`, `frames_per_chunk`, `vlm_prompt_version`,
`reranking_weights`, and `retrieval_top_k`. Unknown fields, out-of-range values, and
unsupported patch-proposal properties are rejected before execution.

Run the sample experiment with:

```text
python benchmarks/optimize_benchmark.py
python benchmarks/optimize_benchmark.py --format json --output-dir benchmarks/results
```

The evaluator compares every candidate with one baseline and applies quality-regression,
minimum-metric, latency, and relative-cost gates. The fixture adapter uses deterministic
relative latency/cost models; these are not production measurements or provider billing.
Reports can include a patch proposal as review metadata, but the evaluator does not run
arbitrary candidate code, edit repository files, push changes, or deploy anything.
