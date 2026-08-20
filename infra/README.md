# Infrastructure

Infrastructure owns local and deployment configuration for the independently deployed
frontend, backend, databases, and AI Service.

## Local Compose

From the repository root:

```text
Copy-Item .env.example .env
docker compose --env-file .env -f infra/compose.yaml up --build
```

This starts the static frontend, a health-aware backend placeholder, PostgreSQL with
pgvector, and Neo4j. Persistent volumes are named `postgres-data`, `neo4j-data`, and
`neo4j-logs`. The backend image does not yet implement query, indexing, or persistence
routes; those remain owned by later issues.

The local compose path intentionally does not require a GPU. Point `AI_SERVICE_URL` in
the untracked `.env` file at a remote AI Service when the backend implementation is
available. The optional local GPU placeholder can be started with:

```text
docker compose --env-file .env -f infra/compose.yaml --profile gpu up --build ai-service
```

The GPU image uses the NVIDIA CUDA runtime and copies `contracts/` from the repository
root. It currently serves only health/placeholder responses; model dependencies and
provider deployment choices belong to later AI Service issues.

## Health checks

- frontend: `GET http://localhost:3000/healthz`
- backend placeholder: `GET http://localhost:8000/healthz` or `/readyz`
- AI Service placeholder: `GET http://localhost:8001/healthz` or `/health`
- Neo4j: browser HTTP health probe on port `7474`
- PostgreSQL/pgvector: `pg_isready` health probe

The placeholder readiness responses report `dependencies_checked: false`; a 200 status
means the process is alive, not that the eventual application is ready for production
traffic.

## Deployment boundary

Build each image from the repository root so shared contracts are available:

```text
docker build -f frontend/Dockerfile .
docker build -f backend/Dockerfile .
docker build -f ai-service/Dockerfile .
```

The intended hosted topology remains frontend web hosting, a CPU backend host, managed
or containerized PostgreSQL/pgvector and Neo4j, and a separate GPU host for AI Service.
This repository does not commit credentials, provider keys, signed URLs, or deployment
state.
