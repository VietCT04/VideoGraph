# Security and Privacy

VideoGraph handles creator-controlled content and derived memory. Privacy, authorization, and retrieval filtering must be enforced server-side.

## Core Principles

- Creator memory is opt-in.
- Hidden/excluded/private content must not surface in viewer search.
- Access control must happen before optional LLM synthesis or action tools.
- Do not trust client-provided ownership, visibility, or canonical IDs without validation.
- Do not use prompts as a substitute for authorization.
- Never commit secrets or private credentials.

## Creator Controls

The intended system supports:

- creator-level enable/disable
- per-content include/exclude
- Moment/entity/relation visibility
- creator correction/rejection
- deletion/re-index operations

The backend must treat these controls as authoritative retrieval constraints.

The fixture-backed creator UI in issue #21 mirrors these constraints locally for demo
state only. Its reducer requires explicit opt-in before content can be selected, turns
included content into excluded content when memory is disabled, and filters disabled,
excluded, or hidden items out of its viewer-visible projection. These checks improve the
demo's state transitions but do not replace server-side authorization, database filters,
or cross-store deletion enforcement.

## Retrieval Privacy

Privacy filters must be applied to both retrieval branches.

```text
User query
   ↓
creator resolution + authorization
   ↓
validated retrieval plan
   ↓
┌───────────────┬───────────────┐
↓                               ↓
Neo4j                         pgvector
creator/visibility filters    creator/visibility filters
└───────────────┬───────────────┘
                ↓
          fusion/reranking
                ↓
       optional synthesis/tools
```

A hidden Moment must not be available through one store simply because it was filtered in the other.

## Query Planner Safety

The small LLM planner is untrusted input to retrieval.

Requirements:

- schema validation
- controlled entity/relation vocabulary
- reject unknown predicates
- no executable raw Cypher from model output
- creator scope determined by backend, not model guess

## Neo4j Safety

- Use parameterized Cypher.
- Use controlled graph tools/templates.
- Avoid unbounded traversals.
- Enforce creator scope and visibility in the repository/service layer.
- Never expose database connection details to clients.

## AI Service Safety

The AI Service must not own authorization or persistent creator-memory decisions.

- Backend controls which content may be processed.
- AI Service returns candidate facts only.
- AI model output is not trusted as canonical truth.
- Preserve evidence and confidence so backend/humans can review uncertain facts.
- Do not log raw private media/transcripts unnecessarily.

## Upload / Media Handling

When upload support is implemented:

- validate file type
- validate size/duration limits
- validate creator ownership/source authorization where relevant
- use bounded temporary storage
- avoid exposing internal object-storage URLs
- remove temporary artifacts according to retention policy

## Secrets

Never commit:

- API/model-provider keys
- database credentials/URLs containing secrets
- JWT/auth secrets
- cloud credentials
- signed storage URLs
- private dataset credentials

Use environment variables and `.env.example` files.

## Logging

Logs should contain enough context to diagnose processing/retrieval failures without leaking unnecessary sensitive data.

Prefer IDs/statuses over full transcripts or raw extracted media in normal application logs.

## Deletion and Re-indexing

Deletion/exclusion must propagate across:

- PostgreSQL application state
- Neo4j
- pgvector
- caches/indexes if introduced later

Re-index operations must not unintentionally restore content the creator has excluded.

## Optional LLM Synthesis

The synthesis model may only receive already-authorized grounded evidence.

It must not have direct unrestricted database access.

A synthesis response must not replace the underlying evidence path for creator-specific factual claims.

## Action Tools

Action tools such as product search or jump-to-moment must consume authorized canonical retrieval results.

Tool failures must not cause the system to expose hidden data or bypass normal permission checks.

## Related Issues

- #12 planner
- #13 safe graph tools
- #17 query API
- #18 indexing jobs
- #19 privacy/deletion
- #20–#21 frontend flows
- #25 action tools
