# VideoGraph

VideoGraph is an opt-in creator-memory system that turns selected short-form videos and LIVE recordings into a persistent multimodal memory that can be queried with natural language.

The core idea is to combine two complementary retrieval systems:

- **Neo4j** for explicit creator entities, relationships, provenance, and temporal structure.
- **pgvector** for semantic retrieval over multimodally fused video Moments.

A viewer can ask:

```text
@alice which red lipstick did she recommend for darker skin?
```

VideoGraph plans the query, searches structured graph facts and semantic Moments in parallel, fuses the results, and returns grounded evidence with exact source timestamps.

> **Project status:** architecture and implementation planning. The repository is being built from the issue backlog in GitHub. Documentation describes the intended MVP and service boundaries; not every component exists yet.

---

## Product Goal

Creator knowledge is distributed across many videos:

- products they use, recommend, compare, like, or dislike
- devices, clothes, places, food, exercises, and topics
- spoken explanations and opinions
- visible OCR text and product labels
- changes in preferences over time
- silent visual demonstrations

VideoGraph converts this fragmented history into reusable creator memory while preserving the evidence that supports every fact.

Example result:

```text
Rare Beauty — Humble

Alice recommended this when discussing red lipstick for darker skin.

Evidence:
▶ Summer Makeup Guide — 00:17
▶ July LIVE — 21:42

[Jump to moment]
```

The goal is not to build a chatbot that invents an answer. The goal is to retrieve and reason over the creator's real content history.

---

## Core Query Architecture

```text
@creator + natural-language question
                ↓
        Small LLM Query Planner
                ↓
         Validated RetrievalPlan
           ┌────┴────┐
           ↓         ↓
       Neo4j      pgvector
       graph       semantic
       search       search
           ↓         ↓
           └────┬────┘
                ↓
          fuse / rerank
                ↓
        grounded evidence
                ↓
       ┌────────┴────────┐
       ↓                 ↓
 direct structured    optional LLM
     response           synthesis
```

The planner does **not** generate raw Cypher. It maps the user query into a validated structured plan using a controlled ontology, while separately generating a semantic search query for the vector branch.

Neo4j and pgvector execute in parallel when both branches are useful.

Simple factual queries can return without a second LLM call. Complex comparison, explanation, or multi-hop questions may use an optional synthesis model over already-filtered grounded evidence.

See [`docs/QUERY_FLOW.md`](docs/QUERY_FLOW.md).

---

## Why Graph + Vectors?

Vectors answer questions such as:

> Where did she talk about makeup for dry skin?

They are strong at fuzzy semantic matching even when the query wording differs from the source transcript.

The graph answers questions such as:

> What products has she recommended?

or:

> What camera did she use before switching to the current one?

It is strong at explicit relationships, exhaustive structured queries, canonical identity, and temporal connections.

Hybrid retrieval handles questions that need both:

> Which red lipstick did she recommend for darker skin?

A key evaluation goal is to compare **vector-only**, **graph-only**, and **hybrid** retrieval rather than assuming the graph is automatically better.

---

## Video Indexing Architecture

The GPU-heavy video-understanding pipeline runs in a standalone AI Service.

```text
Creator video / recorded LIVE
             ↓
        AI Service
             ↓
Timestamped multimodal Moments
- transcript
- evidence
- candidate entities
- candidate relations
- semantic_text
- embedding
             ↓
         Main Backend
          ┌───┴───┐
          ↓       ↓
       Neo4j   pgvector
```

The AI Service processes one content item at a time and returns **content-local candidate facts**. It does not create canonical cross-video identities and does not write directly to persistent databases.

The backend owns:

- canonical IDs
- cross-video entity resolution
- Neo4j ingestion
- pgvector persistence
- creator privacy and deletion
- indexing jobs
- query planning and retrieval

See [`docs/AI_SERVICE.md`](docs/AI_SERVICE.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## AI Service Pipeline

The current design is speech-aligned when speech exists and visual-first when it does not.

```text
Video
  ↓
Timestamped ASR
  ↓
Temporal segmentation
  ├── speech boundaries
  ├── scene/shot changes
  └── silent-video visual fallback
  ↓
Representative frames + OCR
  ↓
Multimodal VLM / fusion
  ↓
entities + relations + semantic_text
  ↓
Embedding model
  ↓
Moment embedding
```

For normal one-minute speech-heavy videos, the planning target is roughly:

- 8–12 semantic chunks
- 3–10 seconds per typical chunk
- 2–4 representative frames per chunk
- batched model work where possible

These are implementation targets, not benchmark guarantees.

---

## Planned Repository Structure

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

This is a monorepo, but the runtime components remain independently deployable.

---

## Runtime Boundaries

### Frontend

Owns viewer search, grounded evidence presentation, timestamp navigation, and creator memory controls.

### Main Backend

Owns APIs, creator/content state, indexing jobs, privacy, planner orchestration, Neo4j, pgvector, retrieval, reranking, and action tools.

### AI Service

Owns GPU-heavy video inference: ASR, temporal segmentation support, representative-frame processing, OCR, VLM fusion, and embedding generation.

### Neo4j

Owns canonical structured creator memory: entities, relationships, Moments, evidence links, temporal properties, and creator visibility state.

### PostgreSQL + pgvector

Owns application state and semantic Moment vectors. Vector rows share canonical `moment_id` values with Neo4j.

---

## Creator Ownership and Privacy

Persistent creator memory is opt-in.

The intended system supports:

- creator-level enable/disable
- per-content inclusion/exclusion
- hidden or rejected Moments/entities/relations
- creator corrections
- deletion propagation across Neo4j and pgvector
- privacy filtering before any LLM synthesis

The model is not trusted to enforce privacy after retrieval; the backend must filter data before it reaches downstream generation.

---

## MVP Demo Flow

1. Creator explicitly enables VideoGraph.
2. Creator selects historical videos or recorded LIVE content.
3. Backend creates asynchronous indexing jobs.
4. AI Service converts videos into timestamped multimodal Moments.
5. Backend builds graph and vector representations.
6. Viewer submits an `@creator` question.
7. Planner produces a validated graph + semantic retrieval plan.
8. Neo4j and pgvector search in parallel.
9. Fusion/reranking returns grounded results with exact evidence.
10. The viewer can jump to the supporting moment or trigger an action such as product search.

---

## Issue Backlog

The implementation is intentionally split into small agent-owned issues.

| Area | Issues |
| --- | --- |
| Architecture / contracts | #1–#2 |
| AI Service | #3–#8 |
| Neo4j / entity resolution | #9–#10 |
| Vector storage / retrieval | #11, #14 |
| Query planner / graph tools | #12–#13 |
| Hybrid retrieval | #15–#16 |
| Query API | #17 |
| Indexing / privacy | #18–#19 |
| Frontend | #20–#21 |
| Data / evaluation | #22–#23 |
| Infrastructure | #24 |
| Agent actions | #25 |
| LIVE stretch | #26 |
| Self-evolving stretch | #27 |

Every issue should remain narrow enough for one agent/session to implement and review independently.

---

## Documentation

- [`docs/README.md`](docs/README.md) — documentation index
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system boundaries and persistent data model
- [`docs/API.md`](docs/API.md) — API boundaries, query endpoints, and indexing job contracts
- [`docs/DATABASE.md`](docs/DATABASE.md) — PostgreSQL, Neo4j, pgvector, canonical IDs, and lifecycle rules
- [`docs/SECURITY.md`](docs/SECURITY.md) — creator privacy, authorization, retrieval safety, and secrets
- [`docs/AI_SERVICE.md`](docs/AI_SERVICE.md) — video-processing service and pipeline
- [`docs/QUERY_FLOW.md`](docs/QUERY_FLOW.md) — planner, Neo4j, semantic search, fusion, and latency path
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — repository and development workflow
- [`docs/CONTINUITY.md`](docs/CONTINUITY.md) — handoff/current-state record
- [`docs/CONCERNS.md`](docs/CONCERNS.md) — unresolved risks and architecture concerns
- [`docs/user-stories/README.md`](docs/user-stories/README.md) — `US-0001-*` user-story convention
- [`AGENTS.md`](AGENTS.md) — mandatory operating rules for coding agents

---

## Current Priorities

The implementation order should favor a thin end-to-end slice before advanced optimization:

```text
contracts
   ↓
fixture Moment data
   ↓
Neo4j + pgvector
   ↓
query planner
   ↓
hybrid retrieval
   ↓
viewer result
```

In parallel, the AI team can build:

```text
video → ASR/chunks → frames/OCR → VLM fusion → embeddings
```

This lets backend/search/frontend agents work against fixtures without waiting for the full GPU pipeline.

---

## One-Sentence Pitch

**VideoGraph turns a creator's selected video history into an evidence-backed multimodal knowledge graph plus semantic vector memory, allowing `@creator` natural-language queries to retrieve exact relationships and moments through fast hybrid graph/vector search.**
