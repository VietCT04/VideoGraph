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
