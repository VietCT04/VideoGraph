# Frontend

The frontend owns viewer search, grounded evidence presentation, timestamp navigation,
and creator memory controls.

## Boundary

- Calls the main backend over its documented HTTP API.
- Uses shared contract definitions from `contracts/` where applicable.
- Must not connect directly to Neo4j, PostgreSQL/pgvector, model providers, or the AI Service.

The fixture-backed viewer implementation is under `demo/` and its local response data is
under `fixtures/`. It is intentionally framework-free so the interaction can be reviewed
before the backend query contract is frozen.

To preview it without adding dependencies, serve the repository root and open
`frontend/demo/index.html`:

```text
python -m http.server 8080
http://localhost:8080/frontend/demo/
```

The demo uses only the conceptual query shape in `docs/API.md`. It does not call a live
backend or implement ranking logic. The eventual frontend adapter must preserve the
backend's authorized evidence and exact timestamps.

The creator-control preview is available at `frontend/demo/creator-controls.html`.
It uses `frontend/fixtures/creator-controls-fixtures.json` to demonstrate explicit opt-in,
per-content selection, queued/failed jobs, retry, and correction/visibility actions. Its
local reducer prevents disabled or excluded content from entering the viewer-visible
projection; real authorization remains a backend responsibility.
