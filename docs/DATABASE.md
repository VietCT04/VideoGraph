# Database

This document is the source of truth for VideoGraph persistent data ownership, canonical IDs, database schemas, indexes, and cross-store lifecycle rules as implementation lands.

## Persistent Stores

VideoGraph uses three logical persistence roles.

### PostgreSQL

Owns normal application state, including planned data such as:

- creators/users
- content metadata
- creator opt-in/settings
- indexing jobs and status
- processing/provider metadata where appropriate

Issue #18's job model is expected to persist at least:

```text
job_id
creator_id
content_id
pipeline_version
state
progress
attempts
ai_job_id
graph_complete
vector_complete
failed_stage
error_code
```

The uniqueness key is `(creator_id, content_id, pipeline_version)`. It prevents a
duplicate submission from creating a second logical processing job while allowing an
explicit retry to resume a failed persistence stage.

### Neo4j

Owns canonical structured creator memory:

- `Creator`
- `Content` / `Video` / `LiveStream`
- `Moment`
- `Product`
- `Brand`
- `Object`
- `Place`
- `Topic`
- `Person`
- controlled relationships and provenance

### PostgreSQL + pgvector

Owns semantic Moment retrieval rows.

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

Do not store large embedding vectors as ordinary Neo4j properties under the current architecture.

## Canonical ID Rules

AI Service local IDs are temporary and scoped to one extraction payload.

Example:

```text
AI local:
moment_1
entity_1

Backend canonical:
moment_video_123_5000_11000
product_42
```

The same canonical `moment_id` must link Neo4j and pgvector:

```text
                  moment_id
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
       Neo4j                 pgvector
   structured Moment       embedding row
```

Changing canonical-ID semantics requires review of ingestion, re-indexing, deletion, entity resolution, graph retrieval, vector retrieval, and API behavior.

## Neo4j Relationship Direction

Initial controlled relationship vocabulary includes candidates such as:

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

The final v1 ontology must be frozen in shared contracts before multiple components independently depend on it.

## Provenance

Viewer-facing structured facts must remain traceable to source evidence.

Desired invariant:

```text
viewer-facing fact
→ one or more Moment IDs
→ source Content
→ exact timestamps/evidence
```

## Idempotency

Re-ingesting the same logical content must not create duplicate canonical Moments, graph facts, or vector rows.

Indexing/retry behavior should use stable identifiers and explicit upsert semantics.

The #18 fixture repository implements this contract in memory for local development.
A production PostgreSQL repository must preserve the same processing-key uniqueness,
state transitions, progress, retry metadata, and completed-store flags.

## Deletion / Visibility

The same content can appear in multiple stores, so deletion/exclusion must propagate consistently.

When creator content is hidden/excluded/deleted:

- PostgreSQL visibility/state must update.
- Neo4j facts/Moments must be removed or suppressed consistently.
- pgvector rows must be removed or excluded from retrieval.
- downstream caches/indexes must not continue surfacing the content.

Issue #19 owns the detailed implementation behavior.

## Entity Resolution

Cross-video entity resolution maps content-local candidates into stable canonical entities.

MVP guidance:

- high-confidence duplicate → merge
- ambiguous candidate → keep separate or link reversibly
- preserve all original evidence
- avoid irreversible aggressive merges

See issue #10 and `docs/CONCERNS.md`.

## Migration Rules

Before database structure changes:

1. Inspect current schemas/models/indexes.
2. Make the smallest schema change possible.
3. Add/update migration or setup scripts.
4. Update this document.
5. Update shared contracts if needed.
6. Update `docs/API.md` if externally observable behavior changes.
7. Update `docs/SECURITY.md` if visibility/privacy behavior changes.

## Related Issues

- #9 Neo4j schema/ingestion
- #10 entity resolution
- #11 pgvector storage
- #18 indexing jobs
- #19 privacy/deletion
- #24 infrastructure

## Issue #18 indexing implementation

`backend/indexing/jobs.py` owns the backend job state machine. It validates the complete
AI extraction payload before mutating either persistent representation, uses the graph
ingestor and vector upsert boundary with the same canonical Moment IDs, and records
which store completed. `InMemoryIndexingJobRepository` is a fixture-backed durable
boundary for one process; it is intentionally replaceable by PostgreSQL.

## Issue #9 implementation slice

`backend/graph/ingestion.py` maps a validated extraction payload into stable
`Creator`, `Content`, `Moment`, and entity/relation records. Moment IDs use the
canonical `moment_<content>_<start_ms>_<end_ms>` form, while entity IDs are
deterministic backend IDs derived from creator, type, and normalized name; AI local
IDs are retained only as properties. `InMemoryGraphRepository` provides idempotent
upserts and fixture evidence queries, and `backend/graph/schema.cypher` contains the
Neo4j constraints and indexes.

Ingestion keeps evidence on entity and relation assertions as exact Moment/content
timestamp references. The fixture adapter is intentionally dependency-free; a
Neo4j driver implementation can satisfy the same repository boundary later.

## Issue #10 entity resolution

`backend/graph/entity_resolution.py` normalizes candidate names and scores creator/type
compatible candidates using exact external IDs, normalized names, name similarity,
brand/category compatibility, optional semantic/visual signals, and creator-history
context. A score at the configured merge threshold updates one canonical entity and
retains the source alias/evidence. A score in the ambiguous band creates a reversible
link decision without merging; lower scores create a new canonical entity.

Resolution decisions are deterministic for the same inputs and configuration. Every
decision records its aliases and Moment evidence and can be reverted in the fixture
resolver, preventing an uncertain mention from becoming an irreversible merge.

## Issue #11 pgvector storage

`backend/search/vector_repository.py` defines the `MomentEmbeddingRow` and
`VectorRepository` boundary. `InMemoryVectorRepository` supports deterministic cosine
search for fixtures, creator/content/time/visibility filters, idempotent `moment_id`
upserts, visibility changes, and content deletion. `PostgresVectorRepository` uses
DB-API parameter binding for all values and filter inputs; it never interpolates a
creator ID, content ID, or visibility into SQL.

`backend/search/migrations/001_moment_embeddings.sql` creates the pgvector-backed
metadata table and creator/content indexes. Embedding dimensions remain deployment
configuration, and `embedding_model` plus `embedding_version` are stored with every
row so incompatible models can be rejected or reindexed deliberately.

