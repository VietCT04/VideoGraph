# AGENTS.md

## Project Overview

VideoGraph is an opt-in multimodal creator-memory system that turns selected videos and LIVE recordings into a persistent, evidence-backed creator memory.

The system combines:

- a standalone GPU-backed AI Service for video understanding
- a main backend for application state, indexing jobs, privacy, query planning, retrieval, and actions
- Neo4j for canonical structured creator memory
- PostgreSQL + pgvector for application state and semantic Moment retrieval
- a frontend for creator controls and grounded `@creator` search

The system must preserve creator control, provenance, exact source timestamps, safe graph querying, and privacy across all retrieval paths.

This repository is a monorepo.

## Repository Structure

Planned structure:

- `frontend`: frontend application
- `backend`: backend API, graph/search/planner/action services
- `ai-service`: GPU-backed video processing service
- `contracts`: shared JSON schemas, DTO/contract definitions, controlled ontology, and constants
- `docs`: product, architecture, API, database, security, AI Service, query flow, user stories, concerns, and continuity docs
- `infra`: local/deployment infrastructure

## Mandatory Working Rule

Before making changes, read the relevant docs.

After making changes, update the relevant docs.

Code and docs must stay synchronized.

If a change affects behavior, API, database, security/privacy, AI extraction, graph ontology, embeddings, query planning, retrieval, indexing, or creator visibility/deletion logic, documentation must be updated in the same change.

## Minimal Change Rule

Make the smallest correct change possible.

Do not refactor unrelated code.

Do not rename files, move folders, rewrite modules, or introduce new patterns unless the GitHub Issue explicitly requires it.

Prefer surgical fixes over broad redesigns.

When modifying existing code:

1. Understand the current pattern.
2. Follow the existing style.
3. Change only what is necessary.
4. Avoid touching unrelated files.
5. Avoid dependency additions unless clearly justified.

If requested implementation conflicts with documented architecture, do not silently redesign the system. Record the concern in `docs/CONCERNS.md` and surface it in the proposal/PR.

## Code Formatting Rules

Code must be readable and match the surrounding repository conventions. Do not compress implementation code to reduce line count.

- Use one field, statement, annotation, method declaration, and constructor assignment per logical line.
- Use explicit imports instead of wildcard imports unless the surrounding module already establishes a different convention.
- Wrap long function signatures, method calls, object construction, and boolean conditions across sensible lines with consistent indentation.
- Extract compound validation, state checks, response construction, orchestration, and lifecycle transitions into clearly named helpers when a single line would become difficult to scan.
- Keep braces, whitespace, accessors, and control flow consistent with nearby files in the same package/module.
- Do not place multiple declarations, assignments, methods, or control-flow branches on one line.
- Preserve normal formatting even when an issue defers automated formatting or verification commands; deferred verification is not permission to write compressed code.

## Documentation Update Rules

Update these docs when relevant:

| Change Type | Required Docs |
|---|---|
| API endpoint/request/response | `docs/API.md` |
| Database schema/model/index/ID linkage | `docs/DATABASE.md` |
| Security/auth/privacy/permissions | `docs/SECURITY.md` |
| System/service boundary | `docs/ARCHITECTURE.md` |
| AI pipeline/model/segmentation behavior | `docs/AI_SERVICE.md` |
| Planner/Neo4j/vector/reranking behavior | `docs/QUERY_FLOW.md` |
| Local setup/build/deployment workflow | `docs/DEVELOPMENT.md` |
| User story/product requirement | `docs/user-stories/*.md` |
| Unresolved risk/uncertainty | `docs/CONCERNS.md` |
| Work handoff/progress | `docs/CONTINUITY.md` |
| Shared schema/contract/ontology | file under `contracts/` + referencing docs |

If no documentation update is needed, explicitly mention why in the final response.

## GitHub Issues Workflow

All implementation work should be linked to a GitHub Issue in the project repository.

Open GitHub Issues represent unresolved work. Closed GitHub Issues represent completed work.

Do not create local ticket files under `docs/tickets/`. Use GitHub Issues instead.

User stories may describe broad product behavior, but GitHub Issues should be small implementation slices.

Prefer several focused issues over one large issue when work spans multiple areas such as AI preprocessing, VLM/fusion, embeddings, Neo4j, pgvector, planner, retrieval, frontend, privacy, indexing, evaluation, or infrastructure.

Each implementation issue should usually have one primary outcome, one main affected area, and acceptance criteria that can be verified independently.

Split an issue when it includes multiple deployable steps, multiple sensitive business rules, or changes across unrelated layers.

### Proposal and Approval Rule

Before resolving or implementing a GitHub Issue, write a proposal as a GitHub Issue comment and wait for user approval.

Use the GitHub Issue comment thread as the approval and revision loop.

If the user comments on that proposal in GitHub, respond with a revised proposal as another GitHub Issue comment, and repeat until the user approves the scope.

If GitHub is unavailable, write the proposal in the conversation and later mirror the approved proposal back to the GitHub Issue when access is restored.

The proposal should summarize:

- intended scope
- files/modules expected to change
- contract/schema/ontology decisions
- open questions or concerns
- verification approach
- what will be documented back to GitHub

Do not start implementation before the proposal is approved unless the user explicitly instructs you to proceed without that approval step.

After approval:

1. Implement the smallest correct change.
2. Update all affected docs.
3. Add concerns to `docs/CONCERNS.md` if any remain.
4. Update `docs/CONTINUITY.md`.
5. Add implementation/completion notes in the GitHub Issue or linked pull request.
6. Close the GitHub Issue only when the work is complete and verified.

### Avoid Duplicate Proposal Comments

Before commenting on GitHub after approval, read the issue comments and check whether the approved proposal is already present.

If the approved proposal is already present in the GitHub Issue comments, do not post it again. Add implementation or completion notes in the linked pull request instead, or add a short issue comment only when there is new information not already captured by the approved proposal or PR.

When commenting on GitHub after approval and the approved proposal is not already present, use the approved proposal as the source of truth. Do not replace it with a separately invented completion summary.

The GitHub comment should preserve the approved scope, decisions, open questions, and next steps. It may add a short factual note listing files changed, verification run, and any implementation result that differs from the proposal.

If a previous GitHub Issue comment does not match the approved proposal, add a corrective follow-up comment with the approved proposal and note that it supersedes the earlier comment.

## Issue Creation Rule

If a new task comes from a user story, create one or more focused GitHub Issues from that user story.

User stories live in:

```txt
docs/user-stories/
```

Each GitHub Issue should include:

```md
# Short Title

## Source

User Story: `docs/user-stories/US-0001-example.md`

## Context

Explain why this task exists.

## Goal

Explain the desired outcome.

## Scope

Describe the narrow implementation slice this issue covers.

## Out of Scope

List related work that should be handled by separate issues.

## Deliverables

List concrete outputs when useful.

## Acceptance Criteria

List independently verifiable criteria.

## Dependencies

**Depends on:**
**Blocks:**
**Can run in parallel with:**

## Concerns

List known risks, uncertainties, or decisions that need human review.
```

For tasks that do not originate from a user story, omit the `Source` section or link the relevant architecture/issue context instead.

## User Story Workflow

User stories describe product behavior from a user's perspective and are the source for implementation issues.

Use user stories for product-facing behavior involving:

- creator opt-in and content selection
- creator indexing/progress/correction/deletion
- viewer `@creator` search
- evidence and timestamp navigation
- product/search/jump-to-moment actions
- privacy and authorization behavior
- LIVE memory behavior
- trust/grounding behavior

User story folder:

```txt
docs/user-stories/
```

User story filename format:

```txt
US-0001-short-title.md
```

User story template:

```md
# US-0001: Short Title

## User Story

As a [user type], I want [goal], so that [benefit].

## Context

Explain why this behavior matters.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Sensitive behavior is enforced server-side where relevant
- [ ] Relevant docs are updated

## Risks

## Follow-up Issues

- GitHub Issue: `#123`
```

When a user story is ready for implementation, create follow-up GitHub Issues if work is required.

## CONCERNS.md Rule

Use `docs/CONCERNS.md` for unresolved risks, assumptions, or questions.

Add to `docs/CONCERNS.md` when:

- A requirement is ambiguous.
- A privacy/security risk exists.
- A graph ontology or entity-resolution decision is unclear.
- A database migration/index change may be risky.
- A planner/retrieval behavior has unresolved product risk.
- A model/provider/embedding choice may need review.
- A temporary workaround was used.
- A test could not be added.
- A benchmark/performance claim is not yet measured.
- A dependency or design choice may need review.

Do not hide uncertainty in code comments only. Put important concerns in `docs/CONCERNS.md`.

## CONTINUITY.md Rule

Use `docs/CONTINUITY.md` as the handoff file for future AI agents and developers.

Update it after every meaningful change.

It should contain:

```md
# Continuity

## Current Project State

Brief summary of what currently works.

## Latest Completed Work

- Date
- GitHub Issue
- Summary
- Files changed
- Verification performed

## Active Work

- Current GitHub Issue
- Current goal
- Current blocker if any

## Important User Stories

- User story links
- Summary of active or recently completed product stories

## Known Concerns

- Link to `docs/CONCERNS.md`

## Next Recommended Steps

1. Step one
2. Step two
3. Step three
```

Do not turn `CONTINUITY.md` into a full changelog. Keep information needed for a safe handoff.

## Database Rules

Before changing database structure:

1. Read `docs/DATABASE.md`.
2. Check existing PostgreSQL models/migrations, Neo4j constraints/indexes, pgvector schema/indexes, IDs, and relationships.
3. Make the smallest schema change possible.
4. Add or update migrations/setup scripts.
5. Update `docs/DATABASE.md`.
6. Update shared contracts/types under `contracts/` if needed.
7. Update API docs if database changes affect API behavior.
8. Update privacy/deletion docs if the change affects what data can surface.

Never change canonical ID or visibility semantics without checking:

- creator/content identity
- `moment_id` linkage between Neo4j and pgvector
- re-index/idempotency behavior
- deletion/suppression propagation
- entity-resolution behavior
- query filters

Do not store large embedding vectors as ordinary Neo4j properties unless an explicitly approved architecture change requires it.

## API Rules

Before changing API behavior:

1. Read `docs/API.md`.
2. Check existing request/response types and shared contracts.
3. Update shared DTOs/schemas under `contracts/` when applicable.
4. Validate backend input.
5. Update frontend API usage.
6. Update `docs/API.md`.

Do not invent new endpoints if an existing endpoint can be extended safely.

Do not change API response shapes without updating all consumers.

Long-running video inference must use asynchronous job APIs rather than keeping one HTTP request open for the full processing duration.

## Frontend Rules

- Use shared contract/types from `contracts/` or generated client types when available.
- Do not duplicate backend DTOs manually when a shared/generated source exists.
- Handle loading, empty, partial-success, success, and error states.
- Preserve exact evidence/timestamps in viewer results.
- Do not expose hidden/excluded creator content.
- Do not rely on frontend-only checks for privacy-sensitive actions.
- Keep components focused and readable.
- Frontend must not call Neo4j, pgvector, model providers, or AI Service directly.

## Backend Rules

- Validate all user/model/external input.
- Check authorization and creator visibility server-side.
- Keep business/orchestration logic outside thin route/controller layers where possible.
- Use explicit indexing job states and transitions.
- Make processing and persistence idempotent.
- Never trust client-provided creator ownership, visibility, processing status, graph predicate, or canonical ID without validation.
- Keep planner output untrusted until schema/ontology validation succeeds.
- Never execute raw model-generated Cypher.
- Use parameterized Cypher and creator-scoped graph tools.
- Filter hidden/private content before reranking, synthesis, or action tools.
- Log important processing/retrieval failures with enough context to diagnose them without leaking sensitive content/secrets.

## AI Service Rules

- AI Service owns content-local inference only.
- AI Service must not write directly to Neo4j or pgvector.
- Preserve timestamps and source evidence through every stage.
- Use a controlled entity/relation ontology.
- Reject unknown structured predicates.
- Treat model output as candidate facts, not automatically trusted canonical truth.
- Do not create persistent cross-video IDs in the AI Service.
- Do not process every video frame unless an approved issue explicitly requires dense processing.
- Support silent/low-speech fallback segmentation.
- Keep model/provider-specific implementations behind adapters when replacement is an explicit requirement.

## Query Planner Rules

The planner translates a natural-language `@creator` request into a validated structured RetrievalPlan.

The planner must not generate executable raw Cypher.

Preferred flow:

```text
user query
→ small LLM planner
→ schema-validated RetrievalPlan
→ controlled graph tools + semantic search
```

The plan should keep graph and semantic intent separate:

- graph relations/entity types/filters
- semantic query text
- optional temporal constraints
- result type / top-k

Unknown predicates or entity types must fail validation rather than pass through to Neo4j.

## Neo4j Rules

Neo4j stores canonical structured creator memory.

- Use parameterized Cypher.
- Scope viewer queries to the intended creator.
- Preserve provenance to exact `Moment`/`Content` evidence.
- Enforce visibility before graph results leave the repository/service layer.
- Use stable backend IDs rather than AI-local IDs.
- Make ingestion idempotent.
- Avoid unbounded graph traversals.
- Never execute model-generated Cypher directly.

## Vector Search Rules

pgvector is a semantic retrieval index, not the canonical source of structured truth.

Every searchable row should preserve enough metadata to resolve back to the same canonical Moment used by Neo4j, including:

- `moment_id`
- `creator_id`
- `content_id`
- timestamps
- `semantic_text`
- embedding model/version
- visibility

Semantic search must be creator-scoped and privacy-filtered.

The query embedding model/dimension must be compatible with stored embeddings.

## Shared Contract Rules

Use `contracts/` for:

- extraction DTOs/schemas
- RetrievalPlan schema
- controlled entity/relation ontology
- shared enums/constants
- API contract types that must match across services

Do not duplicate these independently across frontend, backend, and AI Service.

When shared contracts change, check every producer and consumer.

## Security Rules

- Never commit secrets.
- Never expose database URLs, API keys, model-provider keys, JWT/auth secrets, signed storage URLs, or private credentials.
- Do not trust client-provided ownership or visibility state.
- Creator memory is opt-in.
- Hidden/excluded/private content must not reach viewer results, synthesis models, or action tools.
- Admin/creator-management endpoints must require appropriate authorization when implemented.
- File/video uploads must be validated by type, size, and ownership/source rules when applicable.
- Sensitive actions and deletion/re-index operations should be auditable where practical.
- Privacy must be enforced before LLM generation, not by prompt instruction after retrieval.

## Testing Rules

Add or update tests when practical, especially for privacy/security, authorization, contract validation, graph ingestion/querying, semantic retrieval, entity resolution, indexing idempotency, deletion propagation, planner validation, and API behavior.

**For now, do not run backend or frontend test suites after coding unless the user explicitly asks for them.**

Agents may still write or update backend unit tests, frontend tests, AI pipeline tests, or other test code when practical, but running those test suites is not required by default.

Run non-test verification commands, such as lint, build, typecheck, formatting checks, schema validation, or lightweight static checks, when they are relevant and the environment supports them.

If the user explicitly approves review at the pull-request or CI level, or explicitly says local testing is not needed, do not keep attempting local test runs. Clearly state in the final response and pull request that local tests were not run by user direction.

If local tests cannot run because of environment limitations, dependency access, GPU/model availability, toolchain mismatch, or another blocker, document the reason in the final response and add/update `docs/CONCERNS.md` when the risk is meaningful.

Never claim a test, benchmark, build, lint, deployment, or manual verification was performed unless it actually was.

## Evaluation Rules

Do not claim the hybrid system is better without measurement.

The evaluation harness should distinguish at least:

- vector-only
- graph-only
- hybrid

Relevant metrics may include:

- entity/relation extraction precision/recall
- timestamp accuracy
- entity-resolution precision
- Recall@K / MRR
- graph query correctness
- hybrid answer/retrieval accuracy
- grounding correctness
- planner latency
- graph latency
- vector latency
- fusion latency
- optional synthesis latency
- indexing time and VRAM usage

Keep benchmark datasets/configuration versioned enough that results are reproducible.

Do not present planning latency/backfill estimates as measured results.

## Git and Pull Request Rules

Before changing files, inspect repository status and understand existing work.

- Do not overwrite unrelated local/user changes.
- Do not combine unrelated tickets in one PR.
- Keep commit/PR scope focused.
- Reference the GitHub Issue in the PR.
- Do not close an issue until acceptance criteria are implemented and verified.
- Do not merge a PR unless explicitly authorized.
- Do not silently rewrite an approved scope while implementing.

When documentation/planning changes are the only changes, state that application tests were not run because no executable behavior changed.

## Final Agent Report

When finishing a task, report:

1. What changed.
2. GitHub Issue/PR reference.
3. Important files changed.
4. Tests/checks actually run.
5. Documentation updated, or why no documentation update was needed.
6. Known limitations or remaining concerns.
7. Recommended next issue only when it follows directly from the completed work.

Keep the report factual. Do not claim completion beyond the actual diff and verification.
