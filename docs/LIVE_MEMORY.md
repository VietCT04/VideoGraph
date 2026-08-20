# Incremental LIVE Memory

Issue #26 adds a small, fixture-backed state model for incremental LIVE memory. It is
not a stream ingest service and does not write directly to Neo4j or pgvector.

## State model

A rolling chunk carries:

- a deterministic temporary ID scoped to the LIVE content and chunk ID
- stream-time start_ms and end_ms
- wall-clock start/end timestamps
- the validated content-local extraction concepts used by the prerecorded pipeline
- temporary or finalized state

Repeated delivery of the same chunk ID updates the existing temporary record. This keeps
rolling inference idempotent without reprocessing all completed chunks.

When a LIVE ends, finalize maps each temporary record to a backend-owned persistent
Moment ID of the form moment:<content_id>:<start_ms>:<end_ms>. The resulting records are
then handed to the normal graph/vector indexing path; this module intentionally does not
perform that persistence itself.

## Scope and limitation

backend/services/live_memory.py is a standard-library local/demo implementation for
simulated chunks. A production adapter still needs a stream source, durable temporary
state, authorization/visibility checks, restart recovery, and integration with the
indexing job service. Those concerns remain open until a deployment-ready LIVE issue is
approved.
