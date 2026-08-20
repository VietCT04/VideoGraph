# API

This document is the source of truth for VideoGraph backend and AI Service API behavior as endpoints are implemented.

Do not add or change request/response behavior without updating this file in the same change.

## API Boundaries

### Frontend → Main Backend

The frontend communicates only with the main backend.

Planned API areas include:

- creator lookup / `@creator` resolution
- viewer query submission
- grounded query results
- creator opt-in/settings
- content selection
- indexing job creation/status/retry
- memory inspection/correction/deletion
- action/tool requests where exposed to clients

### Main Backend → AI Service

The backend communicates with the AI Service over an asynchronous job API.

Planned endpoints:

```text
POST /jobs/process-video
GET  /jobs/{job_id}
GET  /jobs/{job_id}/result
GET  /health
```

The AI Service does not expose Neo4j or pgvector operations.

## Query API Direction

Planned viewer request:

```text
POST /query
```

Conceptual request:

```json
{
  "query": "@alice which red lipstick did she recommend for darker skin?"
}
```

Conceptual backend flow:

```text
resolve creator
→ small LLM planner
→ validated RetrievalPlan
→ Neo4j + pgvector
→ fusion/rerank
→ direct result or optional synthesis
```

Conceptual response should preserve grounded evidence:

```json
{
  "creator_id": "creator_42",
  "results": [
    {
      "entity_id": "product_99",
      "label": "Example Lipstick",
      "evidence": [
        {
          "content_id": "video_123",
          "moment_id": "moment_video_123_17000_23000",
          "start_ms": 17000,
          "end_ms": 23000
        }
      ]
    }
  ]
}
```

The exact schema is not frozen yet. Once implemented, replace conceptual examples with canonical request/response contracts.

### Fixture-backed viewer slice (#20)

The initial viewer implementation is a dependency-free demo under `frontend/demo/`.
It uses `frontend/fixtures/viewer-query-fixtures.json` through a local fixture client;
the fixture client is not a network endpoint and does not define a new backend route.

The fixture mirrors the conceptual response above and adds display-only fields for the
demo, including an optional `answer`, a result `summary`, evidence `title`, and
`source_kind`. Every evidence item still carries the canonical `content_id`,
`moment_id`, `start_ms`, and `end_ms` values. A future backend adapter must map its
authorized response into this shape without moving privacy checks into the frontend.

## API Rules

- Validate all external input at the backend boundary.
- Do not expose internal database/provider exceptions directly to clients.
- Do not accept model-generated raw Cypher from any API input.
- Do not return hidden/excluded creator content.
- Keep long-running video processing asynchronous.
- Preserve stable machine-readable error/status values where practical.
- Update every frontend/backend consumer when response shapes change.
- Prefer shared/generated contracts under `contracts/` when available.

## Planned Indexing Job States

Initial direction:

```text
queued
preprocessing
transcribing
segmenting
extracting_frames
running_ocr
fusing
embedding
persisting
completed
failed
```

Final names belong in shared contracts once issue #2 is implemented.

## Related Issues

- #2 shared contracts
- #8 AI Service async API
- #17 viewer query API
- #18 creator indexing jobs
- #19 creator privacy/deletion
- #20 viewer UI
- #21 creator UI
