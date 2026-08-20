# AI Service

## 1. Responsibility

The AI Service is a standalone GPU-backed inference service that converts one video or recorded LIVE item into timestamped multimodal candidate facts.

It answers:

> What did we detect in this piece of content?

It does **not** answer:

> What does this creator know across all videos?

Cross-video canonical identity, persistent graph memory, vector persistence, privacy, and query retrieval belong to the main backend.

---

## 2. Service Boundary

```text
MAIN BACKEND
     │
     │ POST /jobs/process-video
     ↓
┌─────────────────────┐
│      AI SERVICE     │
│                     │
│ API / Job Manager   │
└─────────┬───────────┘
          ↓
      worker/queue
          ↓
   video preprocessing
          ↓
   ASR + segmentation
          ↓
 frames + OCR evidence
          ↓
    VLM / fusion
          ↓
     semantic_text
          ↓
      embedding
          ↓
 extraction payload
          │
          ↓
     MAIN BACKEND
```

The AI Service must not connect directly to Neo4j or pgvector.

---

## 3. Current Pipeline

### Speech-heavy content

```text
Video
  ↓
Timestamped ASR
  ↓
ASR-aligned candidate boundaries
  ↓
merge tiny fragments
split unusually long fragments
add important scene boundaries
  ↓
semantic Moments
```

Initial planning target:

- roughly 8–12 semantic chunks for a normal one-minute speech-heavy video
- roughly 3–10 seconds per typical chunk
- split around 12–15 seconds when needed
- use small visual padding around boundaries where useful

Issue #3 provides this boundary in `ai-service/pipeline/segmentation.py`. Speech spans
and optional scene boundaries are merged into ordered `TemporalChunk` descriptors. Tiny
non-strong fragments are merged, long intervals are split at a deterministic target,
and each result carries three representative timestamps plus a `has_speech` flag.

### Silent / low-speech content

Speech cannot be the only temporal signal.

When no speech spans are supplied, the same segmenter uses scene boundaries when
available and falls back to deterministic target-duration chunks. It never fabricates
transcript evidence. Metadata inspection is an adapter boundary in
`ai-service/pipeline/metadata.py`; the checked-in fixture inspector avoids requiring
FFmpeg/OpenCV for unit tests.

Fallback direction:

```text
video
  ↓
shot / scene changes
+ visual embedding changes
+ OCR changes
+ object/action continuity
+ maximum chunk duration
  ↓
visual candidate segments
  ↓
semantic merge/split
```

Shot boundaries are proposals, not final semantic Moments. Multiple camera shots can describe one event, while one continuous shot can contain several semantic events.

---

## 4. ASR

The ASR stage should return ordered timestamped segments and a no-speech/low-confidence signal.

Conceptual output:

```json
{
  "segments": [
    {
      "start_ms": 5000,
      "end_ms": 11000,
      "text": "This one is probably my favorite.",
      "confidence": 0.94
    }
  ]
}
```

The ASR component does not own final semantic chunk construction.

A provider abstraction should allow model replacement without changing downstream interfaces.

Issue #4 implements this boundary in `ai-service/pipeline/asr.py`. `ASRProvider` returns
ordered `ASRSegment` values, language and speech-ratio metadata, an explicit `no_speech`
flag, and provider/model metadata. `ASRResult.to_speech_spans()` maps directly to the
temporal segmenter. The checked-in `FixtureASRProvider` filters high no-speech
probability segments and supports deterministic batching without loading Whisper.

---

## 5. Representative Frames and OCR

Do not send raw 30 FPS video to the VLM.

For each semantic Moment, select a small set of useful frames.

Initial planning target:

- roughly 2–4 representative frames per chunk
- retain important scene-change frames
- deduplicate near-identical frames
- preserve exact frame timestamps

OCR output must preserve:

- text
- confidence when available
- source timestamp
- bounding box when available

OCR is evidence, not automatically a canonical entity.

Issue #5 implements `FrameCandidate`, `RepresentativeFrame`, and
`DeterministicFrameSampler` in `ai-service/pipeline/frames.py`. The sampler considers
chunk start/middle/end anchors and scene-change candidates, removes near duplicates by
a cheap fingerprint similarity check, and returns at most the configured frame count.
`ai-service/pipeline/ocr.py` provides timestamped `OCRFrameResult` and `OCRItem` models,
including optional bounding boxes, plus a fixture provider. No OpenCV, FFmpeg, or OCR
model is required by the focused tests.

---

## 6. Multimodal Fusion

The fusion stage combines evidence from the same temporal Moment.

Example:

```text
00:05–00:11

ASR:
"This one is probably my favorite for everyday use."

OCR:
RARE BEAUTY
HUMBLE

Vision:
creator holds and applies lipstick
```

Expected structured output:

```json
{
  "entities": [
    {
      "local_id": "entity_1",
      "type": "Product",
      "name": "Rare Beauty Humble",
      "confidence": 0.95
    }
  ],
  "relations": [
    {
      "subject": "creator",
      "predicate": "USES",
      "object": "entity_1",
      "confidence": 0.94
    },
    {
      "subject": "creator",
      "predicate": "LIKES",
      "object": "entity_1",
      "confidence": 0.89
    }
  ],
  "semantic_text": "Creator uses and likes Rare Beauty Humble lipstick for everyday use."
}
```

The fusion model receives a controlled ontology and should not invent arbitrary graph relation names.

---

## 7. semantic_text

The semantic representation exists because raw transcript alone can miss visual and OCR meaning.

Example:

```text
Transcript:
"I really like this one."

OCR:
RARE BEAUTY
HUMBLE

Vision:
creator applies lipstick
```

Fused representation:

```text
Creator uses and likes Rare Beauty Humble lipstick.
```

This is the preferred embedding input for semantic Moment search.

The text does not need to be stylistically polished. It needs to encode supported multimodal meaning compactly and consistently.

Issue #6 implements `MultimodalBundle`, `FusionOutput`, and the `VLMProvider` boundary
in `ai-service/pipeline/fusion.py`. The fixture provider loads beauty, technology, and
travel payloads, validates candidate entities and relations through the shared v1
ontology, and requires every relation to carry evidence references. The provider emits
content-local IDs only; persistent cross-video resolution remains a backend concern.
`build_extraction_payload` revalidates the assembled Moments before returning them.

---

## 8. Embeddings

Each searchable Moment should produce an embedding payload with model metadata.

Conceptual shape:

```json
{
  "model": "<embedding-model>",
  "dimension": 1024,
  "vector": [0.012, -0.031, 0.044]
}
```

The vector above is abbreviated.

Requirements:

- batch generation where practical
- record model/version/dimension
- keep query/store model compatibility explicit
- do not persist vectors inside the AI Service as creator memory

The backend stores the final vector row under the canonical `moment_id`.

---

## 9. Extraction Contract

The shared contract belongs under:

```text
contracts/multimodal-extraction.schema.json
```

The v1 schema and its dependency-free Python validator are implemented. The closed
ontology is shared with `retrieval-plan.schema.json`: unknown entity types and relation
predicates are rejected before any graph or vector operation. The examples under
`contracts/examples/` cover beauty, technology, and travel content so consumers can
develop without model dependencies. Local extraction IDs remain content-local.

Conceptual payload:

```json
{
  "schema_version": "1.0",
  "content_id": "video_123",
  "moments": [
    {
      "local_id": "moment_1",
      "start_ms": 5000,
      "end_ms": 11000,
      "transcript": "This Rare Beauty lipstick is probably my favorite.",
      "semantic_text": "Creator uses and likes Rare Beauty Humble lipstick.",
      "entities": [],
      "relations": [],
      "evidence": {},
      "embedding": {}
    }
  ]
}
```

Local IDs are valid only inside one extraction payload.

---

## 10. Async API

Video processing must not keep one HTTP request open for the full inference duration.

Initial API direction:

```text
POST /jobs/process-video
GET  /jobs/{job_id}
GET  /jobs/{job_id}/result
GET  /health
```

Possible states:

```text
queued
preprocessing
transcribing
segmenting
extracting_frames
running_ocr
fusing
embedding
completed
failed
```

The main backend owns durable application/job state. The AI Service may maintain its own lightweight execution queue for GPU scheduling.

---

## 11. GPU / CPU Split

Planning direction:

```text
GPU
├── multimodal VLM / fusion
└── ASR when beneficial

CPU
├── video download / decoding
├── FFmpeg preprocessing
├── temporal chunk construction
├── scene detection
├── representative-frame extraction
└── lightweight OCR when practical

CPU or GPU
└── embedding model
```

The VLM/fusion stage is expected to dominate GPU cost.

Do not hardcode model-provider assumptions into the backend contract.

---

## 12. Deployment

During development:

```text
Developer machine
├── frontend
├── backend
├── Neo4j
└── PostgreSQL + pgvector

Remote GPU host
└── AI Service
```

When the AI Service image needs shared contracts, use the repository root as Docker build context or an equivalent monorepo setup that makes `contracts/` available.

---

## 13. Evaluation

At minimum benchmark:

- ASR quality / failure rate
- semantic chunk quality
- entity extraction precision/recall
- relation extraction precision/recall
- timestamp grounding
- silent-video behavior
- VLM latency
- ASR latency
- frames/Moment
- Moments/video
- wall-clock indexing time
- peak VRAM

Before extrapolating to hundreds of videos, measure a representative sample first.

---

## 14. Related Issues

- #3 temporal segmentation
- #4 ASR
- #5 frames/OCR
- #6 VLM fusion
- #7 embeddings
- #8 async API
- #22 demo dataset
- #23 benchmark harness
- #24 deployment
- #26 LIVE stretch
