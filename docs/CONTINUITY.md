# Continuity

This file records only the project state needed for the next agent/session to continue safely.

Do not use it as a full changelog.

---

## Current Project State

**Date:** 2026-08-20

VideoGraph is at the first implementation stage. The repository skeleton now exists,
with explicit ownership READMEs under the frontend, backend, AI Service, contracts, and
infrastructure directories. Issue #2 adds the first executable, dependency-free
contract boundary; the AI pipeline and application services remain fixture-backed.

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

The backend query application slice is now implemented as a framework-neutral,
fixture-backed path on top of issues #12, #15, and #16. Indexing, privacy controls, and
action tools remain to be added in the current Workstream D stack.

The root `AGENTS.md` now includes the repository's full issue proposal/approval workflow, documentation synchronization rules, user-story convention, testing policy, database/API/security rules, and component-specific safety rules.

---

## Latest Completed Work

### 2026-08-20 — Issue #17 query application service

**Issue:** #17

Summary:

- Added a framework-neutral `POST /query`-shaped adapter and application service.
- Connected `@creator` parsing, creator resolution, planner, concurrent graph/vector
  retrieval, deterministic fusion, and canonical evidence serialization.
- Added direct structured responses and an optional synthesis provider boundary that
  receives only normalized grounded evidence.
- Added debug timing for planner, graph, vector, fusion, synthesis, and total latency.
- Added fixture-backed query service coverage over the shared beauty extraction fixture.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #16 deterministic result fusion

**Issue:** #16

Summary:

- Added canonical graph/vector deduplication, evidence aggregation, deterministic
  baseline scoring, stable ranking, and direct-answer eligibility.
- Preserved exact Moment/content IDs and timestamps without final LLM synthesis.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #15 parallel retrieval orchestration

**Issue:** #15

Summary:

- Added concurrent graph/vector execution with independent timeouts.
- Added branch status, latency, error, source-result preservation, and partial-success
  bundle semantics without ranking or response synthesis.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #14 semantic Moment retrieval

**Issue:** #14

Summary:

- Added embedding-provider and normalized semantic-hit interfaces.
- Added creator/time/content/visibility-filtered retrieval over the vector repository
  with latency instrumentation and a deterministic fixture embedding fallback.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Vector-database runtime and backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #13 safe graph query tools

**Issue:** #13

Summary:

- Added validated graph-tool planning and fixed relation/entity Cypher templates.
- Added creator/visibility/time/content filtering, bounded results, fixture execution,
  and evidence-preserving `GraphHit` normalization.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Neo4j runtime and backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #12 validated @creator planner

**Issue:** #12

Summary:

- Added strict `@creator` parsing, creator resolution, provider abstraction, and a
  deterministic fixture provider.
- Added schema validation, safe fallback plans, and planner latency instrumentation.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #11 pgvector repository

**Issue:** #11

Summary:

- Added a Moment embedding row contract and dependency-free in-memory cosine-search
  fallback with creator/content/time/visibility filters.
- Added parameterized DB-API PostgreSQL/pgvector upsert/search/delete operations and
  the pgvector schema/index migration.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- PostgreSQL/pgvector runtime and backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #10 deterministic entity resolution

**Issue:** #10

Summary:

- Added normalized candidate scoring with exact-ID, alias, compatibility, and optional
  similarity signals.
- Added high-confidence merge, reversible ambiguous link, create, alias, and evidence
  preservation behavior.

Verification:

- `python -m compileall -q backend contracts` passed.
- `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #9 Neo4j ingestion foundation

**Issue:** #9

Summary:

- Added canonical graph models, stable ID mapping, evidence-preserving ingestion, and
  an idempotent in-memory repository.
- Added Neo4j constraints/indexes in `backend/graph/schema.cypher` without embedding
  storage.

Verification:

- Static Python compilation and `git diff --check` are pending until the stacked slice
  is published.
- Backend/frontend test suites are not being run by direction.

### 2026-08-20 — Issue #2 shared contracts

**Issue:** #2

Summary:

- Added versioned extraction and retrieval-plan JSON Schemas.
- Added a closed v1 ontology and standard-library boundary validator.
- Added beauty, technology, and travel extraction fixtures plus targeted tests.

Verification:

- `python -m unittest contracts.test_validation` passed (5 tests).
- `python -m compileall -q contracts` and `git diff --check` passed.
- Backend/frontend suites are not in scope.

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

Issue #17 is implemented on `codex/issue-17-query-api` and is ready for its draft PR.
The next stacked slice is issue #18 indexing jobs; after that continue with #19 privacy
controls and #25 action tools.

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

1. Review the issue #2 draft PR and merge the stacked foundation when ready.
2. Implement #3 temporal segmentation on top of the shared contracts.
3. Build a thin seeded-data query path through Neo4j + pgvector + planner before waiting for full video inference.
4. Continue AI issues #4–#8 in the requested dependency order.
5. Begin #22 controlled dataset early enough that #23 evaluation can measure real progress.

Do not start stretch issues #26/#27 before the core path is demonstrable unless the team explicitly reprioritizes them.

