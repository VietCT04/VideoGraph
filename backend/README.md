# Backend

The main backend owns application state and all persistent creator-memory operations.

## Planned areas

- `api/` — HTTP endpoints and request/response validation
- `services/` — application orchestration and lifecycle logic
- `graph/` — Neo4j ingestion and safe graph query tools
- `search/` — pgvector persistence and semantic retrieval
- `planner/` — validated `@creator` RetrievalPlan generation
- `agent/` — permissioned action tools over grounded evidence

## Boundary

The backend is the only component that owns canonical IDs, Neo4j, PostgreSQL/pgvector,
creator visibility, indexing jobs, and retrieval authorization. It calls the AI Service
through its asynchronous HTTP contract and can use fixtures when that service is absent.
