# Continuity

This file records only the project state needed for the next agent/session to continue safely.

Do not use it as a full changelog.

---

## Current Project State

**Date:** 2026-08-20

VideoGraph is at the first implementation stage. The repository skeleton now exists,
with explicit ownership READMEs under the frontend, backend, AI Service, contracts, and
infrastructure directories. Issues #2–#8 add dependency-free contract, temporal
segmentation, timestamped ASR, visual evidence, structured multimodal fusion, semantic
embeddings, and asynchronous serving boundaries; later application services remain
fixture-backed.

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

The repository now includes fixture-backed viewer and creator-control demos from issues
#20 and #21 plus a controlled synthetic creator-memory metadata dataset from issue #22.
The demos are executable in a browser as static previews, but no production frontend,
backend query endpoint, indexing API, or privacy API is implemented yet.

The root `AGENTS.md` now includes the repository's full issue proposal/approval workflow, documentation synchronization rules, user-story convention, testing policy, database/API/security rules, and component-specific safety rules.

---

## Latest Completed Work

### 2026-08-20 — Issue #19 privacy and deletion controls

**Issue:** #19

Summary:

- Added creator AI Memory opt-in and creator-authorized content management.
- Added include/exclude/hidden/correction/rejection/deletion state and a framework-neutral privacy adapter.
- Enforced fail-closed query authorization before hybrid retrieval, fusion, and synthesis.
- Synchronized graph and vector visibility changes and deleted both representations together.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #18 creator indexing jobs

**Issue:** #18

Summary:

- Added a durable backend-owned indexing job state machine with progress, retry, AI, graph, vector, ready, and failed metadata.
- Added an asynchronous `AIServiceClient` protocol with a deterministic fixture adapter.
- Validated the complete extraction payload before graph/vector mutation and reused canonical Moment IDs for idempotent upserts.
- Added framework-neutral create/status/retry API models and fixture-backed coverage.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #17 grounded viewer query API

**Issue:** #17

Summary:

- Added a framework-neutral `POST /query`-shaped HTTP adapter.
- Connected `@creator` parsing, creator resolution, planning, parallel graph/vector retrieval, fusion, and grounded evidence serialization.
- Added direct structured responses and an optional synthesis provider boundary over normalized evidence only.
- Added debug timing for planner, graph, vector, fusion, synthesis, and total latency.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #16 graph/vector fusion and reranking

**Issue:** #16

Summary:

- Added canonical graph/vector deduplication through entity and Moment IDs.
- Added deterministic score fusion with relation/evidence features and stable tie-breaking.
- Preserved exact evidence timestamps and exposed direct-answer eligibility without synthesis.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #15 parallel graph-vector retrieval

**Issue:** #15

Summary:

- Added concurrent graph/vector invocation from one validated plan.
- Added independent timeouts and failure/partial-success metadata.
- Preserved branch result objects, evidence, source scores, and latency without fusion.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #14 semantic retrieval

**Issue:** #14

Summary:

- Added embedding-provider and normalized semantic-hit interfaces.
- Added creator-scoped vector retrieval with content/time/visibility filters and latency metadata.
- Added deterministic fixture embedding/indexing fallback linked by canonical Moment ID.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Vector-database runtime and backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #13 safe graph tools

**Issue:** #13

Summary:

- Added fixed relation/entity Cypher templates selected only from the shared allowlist.
- Added creator/visibility/time/content scope and bounded top-k parameters.
- Added fixture-backed graph execution and normalized evidence-preserving hits.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Neo4j runtime and backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #12 validated query planner

**Issue:** #12

Summary:

- Added strict `@creator` parsing and backend-owned creator resolution.
- Added planner provider interface and a controlled ontology prompt.
- Added schema validation, deterministic fixture planning, fallback, and latency metadata.
- Raw Cypher is neither accepted nor generated.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- Backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #11 pgvector repository

**Issue:** #11

Summary:

- Added a Moment embedding row contract and dependency-free in-memory cosine-search fallback with creator/content/time/visibility filters.
- Added parameterized DB-API PostgreSQL/pgvector upsert/search/delete operations and the pgvector schema/index migration.

Verification:

- `python -m compileall -q backend contracts` and `git diff --check` passed.
- PostgreSQL/pgvector runtime and backend/frontend test suites were not run by direction.

### 2026-08-20 — Issue #8 AI Service serving boundary

**Issue:** #8

Summary:

- Added testable in-process asynchronous job orchestration with stable stage states and normalized failures.
- Added contract-aware completion validation and temporary result retention.
- Added FastAPI-compatible routes with a standard-library HTTP fallback and an end-to-end fixture pipeline.

Verification:

- `python -m unittest discover -s ai-service/tests -p 'test_*.py'` passed (20 tests).
- `python -m compileall -q ai-service contracts` and `git diff --check` passed.
- FastAPI app instantiation and route-table checks passed; backend/frontend suites are not in scope.

### 2026-08-20 — Issue #7 semantic embeddings

**Issue:** #7

Summary:

- Added replaceable embedding metadata, batch, and provider models.
- Added a deterministic normalized-hashing fixture with batching and semantic sanity checks.
- Integrated embeddings over fused `semantic_text` into validated extraction payloads.

Verification:

- `python -m unittest discover -s ai-service/tests -p 'test_*.py'` passed (17 tests).
- `python -m compileall -q ai-service contracts` and `git diff --check` passed.
- Backend/frontend suites are not in scope.

### 2026-08-20 — Issue #6 multimodal fusion

**Issue:** #6

Summary:

- Added timestamp-preserving multimodal input assembly and structured fusion models.
- Added controlled-ontology/evidence validation and extraction-payload integration.
- Added beauty, technology, and travel fixture outputs with focused tests.

Verification:

- `python -m unittest discover -s ai-service/tests -p 'test_*.py'` passed (14 tests).
- `python -m compileall -q ai-service contracts` and `git diff --check` passed.
- Backend/frontend suites are not in scope.

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

### 2026-08-20 — Issue #5 representative frames and OCR

**Issue:** #5

Summary:

- Added representative frame candidate/sampling models with anchor selection and near-duplicate reduction.
- Added timestamped OCR item/frame result models with optional bounding boxes.
- Added deterministic frame/OCR fixtures and focused tests without OpenCV/Tesseract dependencies.

Verification:

- `python -m unittest discover -s ai-service/tests -p 'test_*.py'` passed (11 tests).
- `python -m compileall -q ai-service` and `git diff --check` passed.
- Backend/frontend suites are not in scope.

### 2026-08-20 — Issue #4 timestamped ASR

**Issue:** #4

Summary:

- Added replaceable ASR input, segment, result, and configuration models.
- Added a deterministic fixture provider with no-speech filtering and batching.
- Added direct conversion from ASR output to temporal segmenter speech spans.

Verification:

- `python -m unittest discover -s ai-service/tests -p 'test_*.py'` passed (8 tests).
- `python -m compileall -q ai-service` and `git diff --check` passed.
- Backend/frontend suites are not in scope.

### 2026-08-20 — Issue #9 Neo4j ingestion foundation

**Issue:** #9

Summary:

- Added canonical graph models, stable ID mapping, evidence-preserving ingestion, and an idempotent in-memory repository.
- Added Neo4j constraints and indexes without embedding storage.

Verification:

- Python compilation and git diff check were completed for the stacked slice.
- Neo4j runtime and backend/frontend suites were not run.

### 2026-08-20 — Issue #3 temporal segmentation

**Issue:** #3

Summary:

- Added metadata inspection and temporal segmentation interfaces under `ai-service/pipeline/`.
- Added deterministic speech-boundary merging, strong scene-boundary preservation, long-chunk splitting, and representative timestamps.
- Added silent fallback and focused unit tests without FFmpeg/OpenCV dependencies.

Verification:

- `python -m unittest discover -s ai-service/tests -p 'test_*.py'` passed (5 tests).
- `python -m compileall -q ai-service` and `git diff --check` passed.
- Backend/frontend suites are not in scope.

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

### 2026-08-20 — Issue #20 viewer search demo

**Issue:** #20

Summary:

- Added a dependency-free viewer search demo with creator mention parsing and autocomplete.
- Added loading, error, empty, and success states over local query fixtures.
- Preserved canonical evidence IDs and exact source timestamps with jump-to-moment affordances.

Verification:

- Node syntax check and fixture parsing passed.
- Browser checks and full frontend/backend suites were not run.

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

Issues #1–#19 are implemented, including the AI-service pipeline, canonical graph
ingestion, entity resolution, pgvector storage, the validated query planner,
creator-scoped safe graph tools, semantic retrieval, parallel graph/vector
orchestration, result fusion, the grounded viewer query API, and durable creator
indexing jobs and privacy/deletion controls. Issue #21's creator-control slice is
implemented on top of the issue-20 branch, and issue #22's dataset slice is implemented.
The next workstream slice is issue #23's benchmark harness; shared contracts and live
query/indexing/privacy APIs remain separate planned work.

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

1. Implement issue #23's reproducible graph/vector/hybrid benchmark harness.
3. Freeze #2 shared extraction and retrieval-plan contracts.
4. Build a thin seeded-data query path through Neo4j + pgvector + planner before waiting for full video inference.
5. Use #23 to measure graph-only, vector-only, and hybrid retrieval against the dataset.
6. Keep media licensing and audiovisual validity explicit if clips are added later.

Do not start stretch issues #26/#27 before the core path is demonstrable unless the team explicitly reprioritizes them.


