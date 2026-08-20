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
