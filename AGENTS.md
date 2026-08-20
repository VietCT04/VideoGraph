# AGENTS.md

This file is the operating manual for coding agents working in this repository.

The rules below are mandatory unless a more specific nested `AGENTS.md` overrides them for a subdirectory.

---

## 1. Repository Goal

VideoGraph builds an opt-in multimodal creator memory from selected videos and LIVE recordings.

The system combines:

- a standalone GPU-backed **AI Service** for video understanding
- a **main backend** for application state, indexing jobs, privacy, query planning, retrieval, and actions
- **Neo4j** for canonical structured creator memory
- **PostgreSQL + pgvector** for semantic Moment retrieval
- a **frontend** for creator controls and grounded viewer search

The important architectural boundary is:

```text
AI Service
raw content → content-local candidate facts

Backend
candidate facts → canonical creator memory
```

The AI Service must not write directly to Neo4j or pgvector.

---

## 2. Mandatory Working Rule

**Make the smallest correct change possible.**

Before editing code:

1. Read all applicable `AGENTS.md` files.
2. Read the GitHub Issue you are implementing.
3. Read `docs/CONTINUITY.md`.
4. Read the relevant architecture/domain docs.
5. Inspect the existing implementation, tests, dependencies, and git status.
6. Identify the smallest set of files required for the ticket.

Do not refactor unrelated code. Do not add dependencies unless the issue genuinely requires them. Do not rename or reorganize modules merely because a different structure looks cleaner.

If the requested implementation conflicts with documented architecture, stop implementation of that conflicting part and record the concern in `docs/CONCERNS.md` rather than silently changing the architecture.

---

## 3. Ticket-Driven Workflow

Implementation work must be tied to a GitHub Issue.

Preferred unit of work:

```text
one issue
→ one focused branch/session
→ one focused implementation
→ one PR
```

An issue should be narrow enough for one agent to complete and review independently.

Before coding, extract from the issue:

- goal
- in-scope behavior
- out-of-scope behavior
- dependencies
- acceptance criteria
- required tests/validation

If the ticket is too broad, split it instead of implementing unrelated concerns in one PR.

When creating new issues, use this structure when practical:

```text
## Goal

## Context

## Scope

## Out of Scope

## Deliverables

## Acceptance Criteria

## Dependencies
**Depends on:**
**Blocks:**
**Can run in parallel with:**

## Concerns
```

---

## 4. Documentation Discipline

Read relevant docs before changing a subsystem and update them when behavior, contracts, architecture, risks, or operating procedures change.

Documentation ownership matrix:

| Change | Update |
| --- | --- |
| system/service boundary | `docs/ARCHITECTURE.md` |
| AI pipeline/model/segmentation behavior | `docs/AI_SERVICE.md` |
| query planner/retrieval/reranking behavior | `docs/QUERY_FLOW.md` |
| local setup/build/test/deployment workflow | `docs/DEVELOPMENT.md` |
| unresolved architectural or implementation risk | `docs/CONCERNS.md` |
| completed work / handoff / next steps | `docs/CONTINUITY.md` |
| user-visible requirement or flow | relevant file under `docs/user-stories/` |
| shared schema/contract | contract file + referencing docs |

Do not leave documentation describing behavior that no longer exists.

---

## 5. CONTINUITY.md

`docs/CONTINUITY.md` is the handoff file between sessions/agents.

Keep these sections current:

- Current Project State
- Latest Completed Work
- Active Work
- Important User Stories
- Known Concerns
- Next Recommended Steps

When finishing meaningful work, add a concise entry containing:

- date
- issue number
- summary
- important files changed
- verification performed
- follow-up work if any

Do not turn `CONTINUITY.md` into a full changelog. Record only information a future agent needs to continue safely.

---

## 6. CONCERNS.md

Use `docs/CONCERNS.md` for unresolved risks, ambiguity, debt, or architecture questions that should survive the current session.

Each concern should include:

- title
- status
- affected component
- context
- risk
- recommended next action

Do not hide known uncertainty in code comments alone.

---

## 7. Architecture Boundaries

### Frontend

May call the main backend only.

Do not call Neo4j, pgvector, model providers, or the AI Service directly from the browser.

### Main Backend

Owns:

- creator/content/application state
- indexing jobs
- privacy and visibility
- AI Service orchestration
- canonical IDs
- Neo4j access
- pgvector access
- query planning
- hybrid retrieval
- reranking
- optional synthesis
- tool/action orchestration

### AI Service

Owns:

- video/audio preprocessing
- ASR
- temporal segmentation support
- representative frame extraction
- OCR
- VLM/fusion
- candidate entities and relations
- `semantic_text`
- embedding generation

It returns content-local extraction payloads only.

### Shared Contracts

Cross-service interfaces live under `contracts/`.

Do not maintain separate hand-written incompatible schemas in backend and AI Service code. Prefer generated/validated models from the same contract when practical.

---

## 8. Query Planner Rules

The small LLM planner translates a natural-language `@creator` request into a validated structured retrieval plan.

The planner must not generate executable raw Cypher.

Preferred flow:

```text
user query
→ planner
→ schema-validated RetrievalPlan
→ controlled graph tools + semantic search
```

The plan should keep graph and semantic intent separate:

- graph relations/entity types/filters
- semantic query text
- optional temporal constraints
- result type / top-k

Unknown predicates or entity types must fail validation rather than pass through to Neo4j.

---

## 9. Neo4j Rules

Neo4j stores canonical structured creator memory.

Requirements:

- use parameterized Cypher
- scope viewer queries to the intended creator
- preserve provenance to exact `Moment` / `Content`
- enforce visibility before results leave the repository/service layer
- use stable backend IDs rather than AI-local IDs
- make ingestion idempotent
- avoid unbounded graph traversals

Do not execute model-generated Cypher directly.

Do not store large embedding vectors as normal Neo4j properties.

---

## 10. Vector Search Rules

pgvector is a semantic retrieval index, not the canonical source of structured truth.

Every searchable row should preserve enough metadata to resolve back to the same canonical Moment used by Neo4j, including:

- `moment_id`
- `creator_id`
- `content_id`
- timestamps
- `semantic_text`
- embedding model/version
- visibility

Semantic search must be creator-scoped and privacy-filtered.

The query embedding model must be compatible with the stored embedding model/dimension.

---

## 11. AI / ML Grounding Rules

Model output is evidence-derived candidate data, not automatically trusted truth.

Requirements:

- preserve source timestamps
- preserve transcript/OCR/frame evidence
- retain confidence where available
- distinguish explicit evidence from inference when relevant
- use a controlled relationship vocabulary
- reject unknown structured relation names
- do not create persistent canonical IDs in the AI Service
- do not infer a fact merely because no contradictory evidence exists

Example:

```text
last observed using Product A in March
```

must not silently become:

```text
stopped using Product A in March
```

unless source evidence explicitly supports the latter.

---

## 12. Video Processing Rules

Do not process every frame unless a ticket explicitly requires a dense pass.

Current intended direction:

- ASR timestamps are the primary semantic boundary for speech-heavy content
- silent/low-speech content falls back to scene/visual segmentation
- merge tiny speech fragments
- split very long Moments
- sample representative frames
- retain important shot/scene changes
- batch expensive VLM work when practical

Keep intermediate outputs timestamped so later stages can always reconstruct provenance.

---

## 13. Backend / API Rules

- Validate all external input at the service boundary.
- Keep API DTOs separate from persistence objects when this prevents coupling.
- Make asynchronous job state transitions explicit.
- Make reprocessing/idempotency behavior explicit.
- Return stable machine-readable error codes where practical.
- Do not expose internal provider/model/database exceptions directly to clients.
- Keep optional debug/latency information out of normal production responses unless explicitly enabled.

For long-running video inference, use asynchronous job APIs rather than keeping one request open.

---

## 14. Privacy and Security

Creator memory is opt-in.

Never rely on an LLM prompt to enforce access control.

Privacy/visibility must be applied before data reaches:

- hybrid retrieval output
- optional synthesis models
- agent/action tools
- frontend responses

Do not trust client-provided ownership or visibility state without server-side validation.

Do not commit secrets, API keys, model tokens, database credentials, signed URLs, or private datasets.

Use environment variables and documented `.env.example` files.

---

## 15. Database Changes

For schema changes:

- use migrations where the selected stack supports them
- preserve backwards compatibility when practical
- document destructive migrations explicitly
- make uniqueness/idempotency constraints explicit
- keep Neo4j and pgvector canonical ID linkage consistent

If deleting content, ensure deletion/suppression propagates to every representation that can surface it.

---

## 16. Code Style

Follow the conventions already present in the relevant component.

General rules:

- prefer clear domain-specific names
- prefer explicit imports
- keep functions/modules focused
- avoid hidden global state
- do not add abstractions before there is a concrete second use case
- keep provider-specific logic behind adapters when model/vendor replacement is an explicit project requirement
- preserve readable formatting over clever compression

Do not perform formatting-only changes in unrelated files.

---

## 17. Testing and Verification

Add or update targeted tests when practical for the issue being implemented.

Prefer focused checks over running every expensive suite by default.

Relevant checks may include:

- unit tests
- contract validation
- integration tests against local Neo4j/PostgreSQL fixtures
- lint
- type checking
- formatting checks
- frontend build/typecheck
- benchmark smoke tests

Never claim a test, benchmark, build, lint, deployment, or manual verification was performed unless it actually was.

If tests were not run, state that clearly in the PR/final report.

---

## 18. Evaluation Discipline

Do not claim the hybrid system is better without measurement.

The evaluation harness should distinguish at least:

- vector-only
- graph-only
- hybrid

Relevant metrics may include:

- entity/relation extraction precision/recall
- timestamp accuracy
- entity-resolution precision
- Recall@K / MRR
- graph query correctness
- hybrid answer/retrieval accuracy
- grounding correctness
- planner latency
- graph latency
- vector latency
- fusion latency
- optional synthesis latency
- indexing time and VRAM usage

Keep benchmark datasets/configuration versioned enough that results are reproducible.

---

## 19. Git Discipline

Before changing files, inspect repository status and understand existing work.

Rules:

- do not overwrite unrelated local/user changes
- do not combine unrelated tickets in one PR
- keep commit/PR scope focused
- reference the GitHub Issue in the PR
- do not close an issue until acceptance criteria are implemented and verified
- do not merge a PR unless explicitly authorized

When documentation/planning changes are the only changes, state that application tests were not run because no executable behavior changed.

---

## 20. Final Agent Report

When finishing a task, report:

1. what changed
2. issue/PR reference
3. important files changed
4. tests/checks actually run
5. known limitations or remaining concerns
6. recommended next issue only when it follows directly from the completed work

Keep the report factual. Do not claim completion beyond the actual diff and verification.
