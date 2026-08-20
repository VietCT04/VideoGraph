# AI Service

The AI Service is an independently deployable, GPU-capable service for content-local
video understanding.

## Service areas

- `app/` — HTTP job/status API and in-process worker queue
- `pipeline/` — metadata, preprocessing, segmentation, OCR, fusion, and orchestration
- `models/` — replaceable ASR, VLM, and embedding adapters
- `workers/` — asynchronous execution and temporary result handling

## Boundary

The service receives one selected content item and returns a versioned extraction
payload. It may return content-local IDs, but it must not assign persistent cross-video
IDs or write directly to Neo4j, PostgreSQL, or pgvector.

The current `pipeline/metadata.py`, `pipeline/segmentation.py`, `pipeline/asr.py`,
`pipeline/frames.py`, `pipeline/ocr.py`, `pipeline/fusion.py`, and
`pipeline/embeddings.py` modules provide dependency-free implementations of issues
#3–#7. Real media probing, scene detection, Whisper-compatible transcription, frame
decoding, OCR, structured VLM inference, and production embeddings can be supplied
behind the same boundaries later; fixture inputs make local behavior deterministic.

Issue #8 adds `app/jobs.py` and `app/api.py`. The job service uses a temporary,
thread-safe in-process store and worker pool for local development. `create_app()`
returns a FastAPI application when FastAPI is installed; otherwise
`StandardLibraryApplication` exposes the same routes through `http.server`. Run the
fallback from this directory with `python -m app`.
