# Development Workflow

## 1. Current State

VideoGraph is currently documentation- and issue-driven. The top-level implementation
directories now exist as an ownership skeleton; executable services will be added by
their focused issues.

Do not assume a component exists until it is present in the repository.

---

## 2. Planned Monorepo Layout

```text
VideoGraph/
├── frontend/
├── backend/
│   ├── api/
│   ├── services/
│   ├── graph/
│   ├── search/
│   ├── planner/
│   └── agent/
├── ai-service/
│   ├── app/
│   ├── pipeline/
│   ├── models/
│   └── workers/
├── contracts/
├── docs/
├── infra/
├── AGENTS.md
└── README.md
```

The repository is a monorepo for coordination and shared contracts. Runtime services remain independently deployable.

---

## 3. Work by GitHub Issue

Every implementation task should start from one focused issue.

Preferred workflow:

```text
read AGENTS.md
    ↓
read issue + dependencies
    ↓
read relevant docs
    ↓
inspect current code/tests
    ↓
implement smallest correct change
    ↓
run targeted validation
    ↓
update docs/CONTINUITY.md
    ↓
open focused PR linked to issue
```

Avoid combining unrelated issues in one branch/PR.

---

## 4. Parallel Development Strategy

The architecture is intentionally designed so workstreams can proceed with fixtures.

```text
                     shared contracts
                           │
          ┌────────────────┼────────────────┐
          ↓                ↓                ↓
     AI Service       Backend Graph/Search Frontend
          │                │                │
 video → payload     fixtures → stores   mock API → UI
          │                │                │
          └────────────────┼────────────────┘
                           ↓
                       integration
```

Examples:

- AI agent can build ASR/OCR/VLM output without Neo4j.
- Graph agent can ingest hand-written extraction fixtures without GPU models.
- Search agent can use seeded vectors without the AI pipeline.
- Planner agent can test against a fixture ontology/schema.
- Frontend agent can consume mocked query/job responses.

Do not create hidden cross-component dependencies that defeat this separation.

---

## 5. Shared Contracts

Implemented v1 contracts:

```text
contracts/
├── multimodal-extraction.schema.json
├── retrieval-plan.schema.json
├── ontology.py
└── validation.py
```

Rules:

- one canonical schema per cross-service interface
- validate at service boundaries
- version schemas
- reject unknown relationship/entity values when the ontology is closed
- do not maintain divergent backend/AI copies manually

The standard-library validator and fixtures can be run without backend, frontend, or
model dependencies. See `contracts/test_validation.py`.

See issue #2.

---

## 6. Local Runtime Direction

Planned local development topology:

```text
Developer machine
├── frontend
├── backend
├── Neo4j
└── PostgreSQL + pgvector

Remote or local GPU host
└── AI Service
```

The initial local port convention is recorded in the root `.env.example`:

| Component | Default port | Environment variable |
| --- | ---: | --- |
| Frontend | `3000` | `FRONTEND_PORT` |
| Backend | `8000` | `BACKEND_PORT` |
| AI Service | `8001` | `AI_SERVICE_PORT` |

These are development defaults, not a deployment guarantee. Framework-specific
configuration belongs to the owning implementation issue.

The dependency-free AI Service fallback can be started from the repository root with
`PYTHONPATH=ai-service python -m app` (PowerShell users can set `$env:PYTHONPATH` for
the process). It serves the documented AI job routes on port 8001. FastAPI/ASGI
deployment remains optional and is not required for the fixture-backed checks.

Use `.env.example` files for documented configuration and keep real `.env` files untracked.

---

## 7. Provider Abstractions

Model/provider integrations should use adapters where provider replacement is an explicit requirement.

Examples:

```text
ASRProvider
VLMProvider
EmbeddingProvider
PlannerProvider
SynthesisProvider
```

Do not build unnecessary abstraction layers for components that have no plausible alternate implementation.

---

## 8. Backend Integration Principles

### AI Service

Backend calls AI Service through HTTP/job APIs.

The backend must be testable with mocked AI responses.

### Neo4j

Use a repository/service layer with parameterized Cypher and creator scoping.

### pgvector

Keep vector persistence/querying behind a search repository/service boundary.

### Query Planner

Treat planner output as untrusted external structured input until it passes schema/ontology validation.

### Frontend

Frontend should depend on documented backend response contracts rather than database-specific details.

---

## 9. Testing Direction

Prefer targeted tests aligned to issue acceptance criteria.

Expected test categories as implementation appears:

### AI Service

- timestamped ASR tests
- silent-video behavior
- segmentation heuristics
- OCR timestamp preservation
- structured VLM output validation
- embedding dimension/model compatibility

### Backend

- contract validation
- idempotent indexing jobs
- graph ingestion/query tests
- privacy filters
- vector filtering/retrieval tests
- planner schema tests
- hybrid retrieval partial-failure tests

### Frontend

- query input/results
- timestamp navigation
- creator opt-in/indexing state
- privacy/control state

### Evaluation

- vector-only baseline
- graph-only baseline
- hybrid baseline
- latency instrumentation

Do not claim checks that were not run.

---

## 10. Documentation Updates

When implementation changes behavior, update the owning document in the same PR when practical.

Use:

- `ARCHITECTURE.md` for system boundaries/data ownership
- `AI_SERVICE.md` for inference pipeline
- `QUERY_FLOW.md` for planner/retrieval behavior
- `CONCERNS.md` for unresolved risks
- `CONTINUITY.md` for handoff/current state

---

## 11. Branch and PR Discipline

Preferred branch naming:

```text
agent/<short-issue-description>
```

PR body should state:

- linked issue
- what changed
- why
- important implementation decisions
- tests/checks actually run
- documentation updated
- known follow-ups

Keep documentation-only PRs explicit that application tests were not run because executable code did not change.

Do not merge without explicit authorization.

---

## 12. Initial Work Order

A practical thin-slice order is:

```text
#1 architecture skeleton
#2 shared contracts
   ↓
#9 Neo4j fixtures       #11 pgvector fixtures
       \                 /
        \               /
          #12 planner
          #13/#14 retrieval
              ↓
          #15/#16 hybrid
              ↓
             #17 API
              ↓
             #20 UI
```

In parallel:

```text
#3/#4 preprocessing + ASR
      ↓
#5 frames/OCR
      ↓
#6 VLM fusion
      ↓
#7 embeddings
      ↓
#8 AI API
      ↓
#18 real indexing integration
```

The exact order can change as long as dependencies in the issues remain respected.
