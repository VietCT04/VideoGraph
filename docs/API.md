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
- indexing job creation/status/retry (implemented as a framework-neutral adapter in #18)
- memory inspection/correction/deletion
- action/tool requests where exposed to clients

### Main Backend → AI Service

The backend communicates with the AI Service over an asynchronous job API.

The #18 backend client uses an asynchronous submit/status/result contract:

```text
POST /jobs/process-video
GET  /jobs/{job_id}
GET  /jobs/{job_id}/result
GET  /health
```

`backend.indexing.AIServiceClient` is the provider-neutral client boundary. The fixture
adapter is immediate but still exposes submit/status/result methods, so a real HTTP
client or callback/polling implementation can replace it without changing job
orchestration. The AI Service does not expose Neo4j or pgvector operations.

## Query API (#17)

The framework-neutral `backend.api.query.QueryHttpAdapter` is the current HTTP
boundary for the viewer query path. It accepts the following `POST /query`-shaped
JSON body and delegates application behavior to
`backend.query.QueryApplicationService`:

```json
{
  "query": "@alice which red lipstick did she recommend for darker skin?",
  "debug": true
}
```

`query` must start with one `@creator` handle and a non-empty question. `debug` is
optional and defaults to `false`. Unsupported request fields, malformed JSON-shaped
bodies, invalid handles, and unknown creators return a stable `400 invalid_query`
error without exposing provider or database exceptions.

The application flow is:

```text
@creator query
→ creator resolution + validated planner
→ concurrent graph/vector retrieval
→ deterministic fusion/rerank
→ structured direct result or optional synthesis over evidence
```

The response preserves canonical result identity and exact source evidence:

```json
{
  "creator_id": "creator_42",
  "answer_type": "structured",
  "answer": null,
  "results": [
    {
      "result_id": "entity_creator_42_product_...",
      "entity": {"id": "entity_creator_42_product_...", "name": "Example Lipstick"},
      "label": "Example Lipstick",
      "score": 0.91,
      "relations": ["RECOMMENDS"],
      "direct_answer_eligible": true,
      "evidence": [
        {
          "content_id": "video_123",
          "moment_id": "moment_video_123_17000_23000",
          "start_ms": 17000,
          "end_ms": 23000
        }
      ]
    }
  ],
  "warnings": []
}
```

`answer_type` is `structured` for a direct high-confidence response, `synthesized`
when an optional provider returns prose from the normalized evidence bundle, `grounded`
when results exist but the synthesis path is unavailable, and `empty` when no result
was retrieved. `answer` is populated only for `synthesized` responses. Every result
evidence item contains `moment_id`, `content_id`, `start_ms`, and `end_ms`; semantic
text is carried as supporting context when available.

When `debug` is true, the response additionally contains `timing_ms` entries for
`planner`, `graph`, `vector`, `fusion`, `synthesis`, and `total`, plus non-sensitive
branch status metadata. Timing is omitted by default.

## Indexing Jobs (#18)

The framework-neutral `backend.api.indexing.IndexingHttpAdapter` exposes these
`POST`/`GET`-shaped operations:

```text
POST /indexing/jobs
GET  /indexing/jobs/{job_id}
POST /indexing/jobs/{job_id}/retry
```

Create request:

```json
{
  "creator_id": "creator-42",
  "content_id": "beauty-video-001",
  "pipeline_version": "fixture-v1"
}
```

Creation returns `202` and a durable job identity. The backend worker advances the job
through `queued → submitted → ai_processing → ai_done → ingesting_graph →
ingesting_vector → ready`; failures expose `failed_stage`, `error_code`, progress,
attempt count, and per-store completion flags. A retry resumes the failed stage when
possible, so a vector failure does not rerun GPU extraction or duplicate graph records.
Invalid request bodies return `400 invalid_indexing_request`, unknown jobs return
`404 job_not_found`, and non-retryable jobs return `409 job_not_retryable`.

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
API but does not perform free-form synthesis. The #17 query application service now
owns the response boundary: direct structured results bypass synthesis, while complex
questions may call an injected synthesis provider with only normalized authorized
evidence.

## API Rules

- Validate all external input at the backend boundary.
- Do not expose internal database/provider exceptions directly to clients.
- Do not accept model-generated raw Cypher from any API input.
- Do not return hidden/excluded creator content.
- Keep long-running video processing asynchronous.
- Preserve stable machine-readable error/status values where practical.
- Update every frontend/backend consumer when response shapes change.
- Prefer shared/generated contracts under `contracts/` when available.

## AI Pipeline States

The detailed AI pipeline states remain internal to the AI Service. Main-backend durable
job states are defined by issue #18 above and deliberately track orchestration stages,
not every GPU substep.

## Related Issues

- #2 shared contracts
- #8 AI Service async API
- #17 viewer query API
- #18 creator indexing jobs
- #19 creator privacy/deletion
- #20 viewer UI
- #21 creator UI

