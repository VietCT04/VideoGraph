# System Architecture

## 1. Purpose

VideoGraph builds an opt-in persistent creator memory from selected video and LIVE content.

The architecture intentionally separates:

- **content understanding** — GPU-heavy inference over one piece of content
- **canonical memory** — stable entities and relationships across many content items
- **semantic retrieval** — vector search over fused temporal Moments
- **query planning** — translating natural language into safe structured retrieval operations
- **viewer actions** — timestamp navigation, product lookup, and other permissioned tools

---

## 2. High-Level Architecture

```text
                           FRONTEND
                              │
                              ↓
                    ┌──────────────────┐
                    │   MAIN BACKEND   │
                    │                  │
                    │ APIs             │
                    │ creator/privacy  │
                    │ indexing jobs    │
                    │ query planner    │
                    │ graph retrieval  │
                    │ vector retrieval │
                    │ reranking        │
                    │ action tools     │
                    └────────┬─────────┘
                             │
             ┌───────────────┼─────────────────┐
             ↓               ↓                 ↓
        PostgreSQL         Neo4j            pgvector
        app state     canonical memory    Moment index
             │
             │ HTTPS
             ↓
      ┌──────────────────────┐
      │      AI SERVICE      │
      │      GPU HOST        │
      │                      │
      │ ASR / chunking       │
      │ frames / OCR         │
      │ VLM fusion           │
      │ embeddings           │
      └──────────────────────┘
```

---

## 3. Service Ownership

The repository skeleton reflects these ownership boundaries in separate top-level
directories. A directory-level README records the contract for `frontend/`, `backend/`,
`ai-service/`, `contracts/`, and `infra/`; implementation issues may add code within
those boundaries without changing the ownership model.

### Frontend

Owns:

- `@creator` search experience
- creator selection/autocomplete
- grounded evidence cards
- exact timestamp navigation
- creator opt-in/indexing controls
- progress/error states

The frontend calls the main backend only.

Issue #20 adds a framework-free fixture-backed viewer demo. It owns input parsing,
creator autocomplete presentation, loading/error/empty/success rendering, and
timestamp navigation affordances. It does not own retrieval, ranking, authorization,
or privacy filtering; those remain backend responsibilities.

Issue #21 adds a matching fixture-backed creator-control preview. Its local reducer
demonstrates opt-in, explicit content selection, indexing-job status, and memory
correction/visibility actions while keeping the viewer-visible projection empty for
disabled or excluded content. It is a UI/state slice, not a replacement for backend
authorization or persistent job/privacy services.

### Main Backend

Owns:

- creator/content/application state
- authorization and privacy
- indexing job lifecycle
- AI Service client/orchestration
- shared-contract validation
- canonical ID assignment
- Neo4j ingestion/querying
- pgvector persistence/querying
- cross-video entity resolution
- small LLM query planner
- hybrid retrieval and reranking
- direct structured response path
- optional final synthesis path
- action/tool orchestration

### AI Service

Owns content-local inference:

- audio/video preprocessing
- timestamped ASR
- temporal segmentation signals
- representative frames
- OCR
- visual/VLM understanding
- multimodal fusion
- candidate entities/relations
- `semantic_text`
- Moment embeddings

It does not own canonical entity identity and must not write directly to backend databases.

---

## 4. Persistent Data Model

### PostgreSQL

Stores normal application state such as:

- creators/users
- content metadata
- opt-in/settings
- indexing jobs
- processing status
- provider/configuration metadata as appropriate

### Neo4j

Stores canonical structured creator memory.

Initial node vocabulary:

```text
Creator
Content
├── Video
└── LiveStream
Moment
Product
Brand
Object
Place
Topic
Person
```

Initial controlled relationships may include:

```text
USES
WEARS
OWNS
MENTIONS
LIKES
DISLIKES
RECOMMENDS
VISITS
COMPARES
PREFERS_OVER
SWITCHED_TO
EVIDENCED_BY
PART_OF
BRAND
CATEGORY
ABOUT
LOCATED_AT
```

Do not let extraction/query models invent arbitrary predicates that bypass validation.

### pgvector

Stores semantic retrieval rows for searchable Moments.

Expected fields include:

```text
moment_id
creator_id
content_id
start_ms
end_ms
semantic_text
embedding
embedding_model
visibility
```

The vector index is not the source of canonical graph truth.

---

## 5. Shared IDs

Neo4j and pgvector must link through stable backend-owned IDs.

```text
                    moment_id
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
           Neo4j             pgvector
       Moment/evidence       embedding row
```

The AI Service can return local IDs such as:

```text
moment_1
entity_1
```

Those IDs are scoped to one extraction payload only.

The backend maps them to stable persistent IDs such as:

```text
moment_video_123_5000_11000
product_42
```

---

## 6. Video Indexing Flow

```text
creator selects content
        ↓
backend creates durable job
        ↓
backend submits content to AI Service
        ↓
AI Service processes asynchronously
        ↓
shared extraction payload
        ↓
backend validates contract
        ↓
canonicalize / resolve entities
        ↓
┌───────────────────────┬───────────────────────┐
↓                                               ↓
Neo4j graph upsert                         pgvector upsert
└───────────────────────┬───────────────────────┘
                        ↓
                 content searchable
```

Reprocessing must be idempotent.

---

## 7. Query Flow

```text
@creator + question
        ↓
creator resolution
        ↓
small LLM planner
        ↓
validated RetrievalPlan
    ┌───────┴────────┐
    ↓                ↓
Neo4j tools      semantic query
    ↓                ↓
 graph search       pgvector
    └───────┬────────┘
            ↓
      fuse / rerank
            ↓
     grounded evidence
            ↓
 direct result OR optional synthesis
```

The planner outputs structured intent. It does not output executable Cypher.

See [`QUERY_FLOW.md`](QUERY_FLOW.md).

---

## 8. Privacy Boundary

Persistent memory is opt-in.

Privacy must be enforced in backend/database retrieval before any data reaches:

- reranking output
- final synthesis LLM
- agent tools
- frontend response

Required controls include:

- creator enable/disable
- per-content include/exclude
- Moment/entity/relation visibility
- creator rejection/correction
- deletion/suppression propagation across Neo4j and pgvector

An LLM prompt is not an access-control mechanism.

---

## 9. Deployment Model

Planned deployment:

```text
frontend     → web hosting
backend      → normal CPU application host
PostgreSQL   → container/managed database
Neo4j        → container/managed graph database
ai-service   → GPU host
```

During development, backend/databases can run locally while the AI Service runs remotely on a GPU machine.

The monorepo does not imply a single deployment unit.

Issue #24 adds root-context Dockerfiles and `infra/compose.yaml` for the static frontend,
backend placeholder, PostgreSQL/pgvector, and Neo4j. The AI Service image is available
under the optional `gpu` Compose profile. These files establish build context, volumes,
and process-level health checks; the backend and AI Service business routes remain
placeholders until their implementation issues land.

---

## 10. Scalability Direction

Video indexing is the expensive path; viewer retrieval should be comparatively cheap.

Production scaling can use:

- asynchronous historical backfill
- recent/high-value content first
- incremental processing for new content
- incremental LIVE chunks
- reuse of precomputed platform features when available
- smaller-model routing for easy segments
- batched VLM/embedding work
- read-many reuse of once-indexed creator memory

Do not present planning estimates as measured performance. Use the benchmark harness before making performance claims.

The fixture benchmark in `benchmarks/run_benchmark.py` is an evaluation aid, not a
replacement for the production graph/vector services. It keeps graph intent matching,
semantic matching, and hybrid fusion as separate baselines and reports their evidence
metrics independently. It must not be used to claim model, database, GPU, or audiovisual
performance until those components are connected to measured inputs.

---

## 11. Related Issues

- #1 repository/service boundaries
- #2 shared contracts
- #8 AI Service API
- #9 Neo4j schema/ingestion
- #10 entity resolution
- #11 pgvector storage
- #12 planner
- #13 graph tools
- #14 semantic retrieval
- #15–#16 hybrid retrieval/fusion
- #18 indexing jobs
- #19 privacy/deletion
- #24 deployment
