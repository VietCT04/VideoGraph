# Frontend

The frontend owns viewer search, grounded evidence presentation, timestamp navigation,
and creator memory controls.

## Boundary

- Calls the main backend over its documented HTTP API.
- Uses shared contract definitions from `contracts/` where applicable.
- Must not connect directly to Neo4j, PostgreSQL/pgvector, model providers, or the AI Service.

The application implementation is introduced by the frontend issues; this file records
the ownership boundary for the monorepo skeleton.
