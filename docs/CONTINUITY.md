# Continuity

This file records only the project state needed for the next agent/session to continue safely.

Do not use it as a full changelog.

---

## Current Project State

**Date:** 2026-08-20

VideoGraph is at architecture/backlog bootstrap stage.

The repository has a complete initial GitHub issue backlog covering:

- architecture/contracts
- AI Service ingestion
- Neo4j canonical memory
- pgvector semantic indexing
- small LLM query planner
- safe graph tools
- semantic retrieval
- parallel hybrid retrieval
- fusion/reranking
- query API
- indexing jobs/privacy
- frontend
- data/evaluation
- infrastructure
- agent actions
- LIVE and self-evolving stretch work

The intended core query architecture is:

```text
@creator query
→ small LLM planner
→ validated RetrievalPlan
→ Neo4j + pgvector in parallel
→ fusion/rerank
→ grounded response
→ optional synthesis only when needed
```

The intended indexing architecture is:

```text
video
→ AI Service
→ timestamped Moments
→ candidate entities/relations + semantic_text + embedding
→ backend canonicalization
→ Neo4j + pgvector
```

No application implementation should be assumed complete yet.

---

## Latest Completed Work

### 2026-08-20 — Initial project planning

**Issues:** #1–#27

Summary:

- Created the initial small, dependency-aware issue backlog.
- Split AI work into preprocessing/segmentation, ASR, frames/OCR, VLM fusion, embeddings, and serving.
- Split backend retrieval into planner, safe graph tools, semantic search, parallel orchestration, and fusion/reranking.
- Added separate creator indexing/privacy, frontend, dataset, benchmark, deployment, and stretch issues.

Verification:

- GitHub issue list was checked after creation.

---

## Active Work

Initial documentation/bootstrap PR work:

- root `README.md`
- root `AGENTS.md`
- architecture/query/AI/development docs
- continuity and concerns docs
- user-story convention

No implementation issue should be marked complete solely because these planning documents exist.

---

## Important User Stories

Current highest-value product flows:

1. **Creator opt-in and indexing**
   - creator explicitly enables memory
   - selects content
   - sees processing progress
   - can exclude/delete/correct memory

2. **Viewer `@creator` search**
   - viewer asks a natural-language question about one creator
   - system retrieves graph + semantic evidence
   - result includes exact source moments/timestamps

3. **Cross-video structured memory**
   - repeated entities across different videos resolve to canonical identities
   - explicit relationships and temporal changes remain queryable

4. **Semantic rewind**
   - fuzzy contextual questions retrieve relevant Moments even when wording differs from source transcript

5. **Actionable result**
   - grounded result can trigger jump-to-timestamp or product/search tool actions

See `docs/user-stories/` as stories are added.

---

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Highest-priority unresolved concerns currently include:

- exact model/provider choices are not frozen
- controlled graph ontology is not yet frozen in a shared contract
- embedding model/dimension is not yet selected
- graph-only vs vector-only vs hybrid value has not yet been benchmarked
- latency/backfill figures discussed so far are planning estimates, not measurements
- demo/public dataset licensing and controlled creator dataset details remain to be finalized

---

## Next Recommended Steps

1. Complete #1 repository/service skeleton.
2. Freeze #2 shared extraction and retrieval-plan contracts.
3. Create fixture payloads so graph/search/frontend work can proceed without the AI Service.
4. Build a thin seeded-data query path through Neo4j + pgvector + planner before waiting for full video inference.
5. In parallel, implement AI issues #3–#8.
6. Begin #22 controlled dataset early enough that #23 evaluation can measure real progress.

Do not start stretch issues #26/#27 before the core path is demonstrable unless the team explicitly reprioritizes them.
