# AI Service

The AI Service is an independently deployable, GPU-capable service for content-local
video understanding.

## Planned areas

- `app/` — HTTP job/status API
- `pipeline/` — preprocessing, segmentation, OCR, fusion, and orchestration
- `models/` — replaceable ASR, VLM, and embedding adapters
- `workers/` — asynchronous execution and temporary result handling

## Boundary

The service receives one selected content item and returns a versioned extraction
payload. It may return content-local IDs, but it must not assign persistent cross-video
IDs or write directly to Neo4j, PostgreSQL, or pgvector.
