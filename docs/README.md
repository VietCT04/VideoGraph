# Documentation

This directory contains the durable product, architecture, API, database, security, workflow, and handoff documentation for VideoGraph.

Agents must read the relevant documents before changing a subsystem and update them when behavior or architectural decisions change.

## Core Documents

| Document | Purpose |
| --- | --- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System boundaries, persistent data ownership, canonical IDs, privacy, and deployment model |
| [`API.md`](API.md) | Frontend/backend and backend/AI Service API behavior, job/query contract direction |
| [`DATABASE.md`](DATABASE.md) | PostgreSQL, Neo4j, pgvector, canonical IDs, indexes, lifecycle, deletion, and migration rules |
| [`SECURITY.md`](SECURITY.md) | Creator opt-in, authorization, privacy filtering, planner/graph safety, secrets, and media handling |
| [`AI_SERVICE.md`](AI_SERVICE.md) | Video preprocessing, ASR, temporal segmentation, OCR, VLM fusion, embeddings, async serving |
| [`QUERY_FLOW.md`](QUERY_FLOW.md) | `@creator` planner flow, safe Neo4j tools, semantic search, hybrid retrieval, reranking, optional synthesis |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Repository workflow, planned component layout, local development principles, issue/PR discipline |
| [`CONTINUITY.md`](CONTINUITY.md) | Current project state and handoff notes between agents/sessions |
| [`CONCERNS.md`](CONCERNS.md) | Unresolved risks, architecture questions, and technical debt |
| [`user-stories/README.md`](user-stories/README.md) | `US-0001-*` user-story convention and product-flow documentation |

The root [`AGENTS.md`](../AGENTS.md) is the mandatory operating manual for coding agents.

## Source of Truth

Use this precedence when documents disagree:

1. explicitly approved GitHub Issue proposal or approved architecture decision
2. canonical shared contract files under `contracts/`
3. subsystem documentation in this directory
4. root `README.md`

Do not silently resolve contradictions. Record unresolved conflicts in `CONCERNS.md` and fix the stale source in the same PR when practical.

## Documentation Rules

- Keep implementation details close to the subsystem that owns them.
- Keep README focused on product direction and system-level navigation.
- Do not duplicate large schema definitions in multiple documents; link to canonical contracts once created.
- Update `API.md` when endpoint/request/response behavior changes.
- Update `DATABASE.md` when persistent schema, IDs, indexes, relationships, or lifecycle rules change.
- Update `SECURITY.md` when privacy, authorization, upload, secret-handling, or retrieval-safety behavior changes.
- Update `CONTINUITY.md` after meaningful implementation work so another agent can resume without reconstructing context.
- Record unresolved questions in `CONCERNS.md` rather than burying them in chat history or code comments.
