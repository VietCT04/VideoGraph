# Continuity

This file records only the project state needed for the next agent/session to continue safely.

Do not use it as a full changelog.

---

## Current Project State

**Date:** 2026-08-20

VideoGraph is at the first implementation stage. The repository skeleton now exists,
with explicit ownership READMEs under the frontend, backend, AI Service, contracts, and
infrastructure directories. Executable application code is still pending.

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

The repository now includes a small fixture-backed viewer search demo from issue #20.
It is executable in a browser as a static preview, but no production frontend or
backend query endpoint is implemented yet.

The root `AGENTS.md` now includes the repository's full issue proposal/approval workflow, documentation synchronization rules, user-story convention, testing policy, database/API/security rules, and component-specific safety rules.

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

### 2026-08-20 — Documentation and agent workflow bootstrap

**PR:** #28

Summary:

- Added root README and full agent operating rules.
- Added architecture, AI Service, query flow, API, database, security, development, concerns, continuity, and user-story docs.
- Restored mandatory proposal-before-implementation workflow for GitHub Issues.
- Restored default policy not to run backend/frontend test suites unless explicitly requested.
- Standardized user-story filenames to `US-0001-*` format.

Important files:

- `AGENTS.md`
- `README.md`
- `docs/API.md`
- `docs/DATABASE.md`
- `docs/SECURITY.md`
- `docs/ARCHITECTURE.md`
- `docs/AI_SERVICE.md`
- `docs/QUERY_FLOW.md`
- `docs/DEVELOPMENT.md`
- `docs/CONCERNS.md`
- `docs/user-stories/*`

Verification:

- Documentation branch compared against `main`.
- No executable application code is part of this bootstrap documentation work.

---

## Active Work

Issue #20's viewer slice is implemented on its stacked branch. The next workstream
slice is issue #21's creator control UI; shared contracts and live query/indexing APIs
remain separate planned work.

Do not mark later implementation issues complete solely because their directories or
documentation exist.

Future implementation work must follow the proposal/approval workflow in `AGENTS.md` before coding unless the user explicitly waives that step.

---

## Important User Stories

1. [`US-0001-creator-indexing.md`](user-stories/US-0001-creator-indexing.md)
   - creator explicitly enables memory
   - selects content
   - sees processing progress
   - can exclude/delete/correct memory

2. [`US-0002-viewer-search.md`](user-stories/US-0002-viewer-search.md)
   - viewer asks a natural-language question about one creator
   - system retrieves graph + semantic evidence
   - result includes exact source moments/timestamps

Additional important product behaviors to preserve:

- cross-video canonical entity identity
- temporal structured memory
- semantic rewind over fuzzy contextual queries
- grounded action tools such as jump-to-moment/product search

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

1. Review the stacked issue #20 viewer PR and merge it when approved.
2. Implement issue #21 creator controls against mocked indexing/privacy responses.
3. Freeze #2 shared extraction and retrieval-plan contracts.
4. Build a thin seeded-data query path through Neo4j + pgvector + planner before waiting for full video inference.
5. In parallel, implement AI issues #3–#8 after their proposals are approved.
6. Begin #22 controlled dataset early enough that #23 evaluation can measure real progress.

Do not start stretch issues #26/#27 before the core path is demonstrable unless the team explicitly reprioritizes them.
