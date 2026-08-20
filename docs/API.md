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

The AI Service does not expose Neo4j or pgvector operations. Issue #8 implements these
routes with a FastAPI adapter when the optional dependency is installed and a matching
standard-library fallback otherwise.

#### `POST /jobs/process-video`

Request:

```json
{
  "content_id": "video_123",
  "creator_id": "creator_42",
  "upload_ref": "selected-upload-ref"
}
```

Exactly one of `video_url` or `upload_ref` is required. The response returns immediately:

```json
{
  "job_id": "opaque-job-id",
  "status": "queued"
}
```

#### `GET /jobs/{job_id}`

Returns the job identity and one of the stable states:

```text
queued
preprocessing
transcribing
segmenting
extracting_visuals
fusing
embedding
completed
failed
```

Failures include a machine-readable `error.code` and an actionable message. No partial
result is published for a failed job.

#### `GET /jobs/{job_id}/result`

Returns the validated `multimodal-extraction.schema.json` payload when the job is
`completed`, `202` while it is still running, and `409` with the normalized failure
object when it is `failed`. Results are temporary service-local data; the main backend
owns durable application state and persistence.

#### `GET /health`

Returns a small service health object and identifies whether the FastAPI or
standard-library adapter is serving the routes.

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

### Fixture-backed creator controls (#21)

The creator preview under `frontend/demo/creator-controls.html` uses
`frontend/fixtures/creator-controls-fixtures.json`. It models the planned settings,
content-selection, indexing-job, and memory-review API areas without inventing endpoint
paths before issues #18 and #19 freeze those contracts.

The fixture state includes `memory_enabled`, per-content `included`/`excluded` flags,
job `status`/`progress`/`stage`, and fact `visibility`/`review_status`. The local state
adapter enforces the important transition rules: indexing requires explicit opt-in and
selection; disabling memory removes all content from the viewer-visible projection; and
re-enabling memory does not silently restore previously excluded content.

## Implemented internal planner contract (#12)

Before a viewer query endpoint is added, the dependency-free
`backend.planner.RetrievalPlanner` provides the internal request boundary. It accepts a
string beginning with `@creator`, resolves the handle through a backend-owned mapping
or callback, and returns a validated `RetrievalPlan` plus fallback and latency
metadata. Planner providers return structured data only; raw Cypher is not an accepted
field or execution path. The fixture provider is the current local adapter.

The internal `HybridRetrievalOrchestrator` accepts the validated plan and returns a
bundle containing independent graph/vector outcomes, source result objects, branch
latencies, timeout/error status, and a partial-success flag. It is an orchestration
boundary, not a final answer or synthesis API.

The internal `ResultFusionService` consumes a `RetrievalBundle` and returns ranked
results with graph/vector source scores, relation matches, canonical Moment evidence,
and a direct-answer eligibility signal. The result set is suitable for a later query
API but does not perform free-form synthesis.

## API Rules

- Validate all external input at the backend boundary.
- Do not expose internal database/provider exceptions directly to clients.
- Do not accept model-generated raw Cypher from any API input.
- Do not return hidden/excluded creator content.
- Keep long-running video processing asynchronous.
- Preserve stable machine-readable error/status values where practical.
- Update every frontend/backend consumer when response shapes change.
- Prefer shared/generated contracts under `contracts/` when available.
- Keep AI Service results content-local and contract-validated; never persist directly
  to Neo4j or pgvector from this service.

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
