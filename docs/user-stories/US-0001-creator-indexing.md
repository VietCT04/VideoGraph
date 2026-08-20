# US-0001: Creator Enables and Builds AI Memory

## User Story

As a creator, I want to explicitly enable VideoGraph and choose which videos or LIVE recordings are indexed, so that viewers can search my approved content history while I retain control over visibility, correction, and deletion.

## Context

VideoGraph creates persistent cross-video memory. That memory must begin only with creator consent and must remain controllable after indexing.

The creator experience covers opt-in, content selection, asynchronous processing, progress/error visibility, re-indexing, correction, exclusion, and deletion.

## Acceptance Criteria

- [ ] Creator memory is disabled until the creator explicitly opts in.
- [ ] Creator can choose which videos/LIVE recordings are included.
- [ ] Selected content is processed asynchronously through durable indexing jobs.
- [ ] Creator can see queued, processing, completed, and failed states.
- [ ] Retry/re-index does not create duplicate canonical Moments or vector rows.
- [ ] Creator can exclude or hide content from viewer retrieval.
- [ ] Excluded/hidden content is suppressed consistently in Neo4j and pgvector.
- [ ] Creator corrections/rejections are persisted when the corresponding UI/backend support is implemented.
- [ ] Sensitive ownership/visibility behavior is enforced server-side.
- [ ] Relevant API/database/security/product docs are updated when implementation changes these behaviors.

## Risks

- Disabling memory versus permanently deleting derived data requires an explicit retention policy.
- Re-indexing must not re-enable content the creator intentionally excluded.
- Cross-store deletion must remain consistent across PostgreSQL, Neo4j, pgvector, and any future caches.
- Creator correction UX may require reversible entity-resolution decisions.

## Follow-up Issues

- GitHub Issue: `#8` — AI Service async API
- GitHub Issue: `#9` — Neo4j ingestion
- GitHub Issue: `#11` — pgvector storage
- GitHub Issue: `#18` — indexing jobs
- GitHub Issue: `#19` — opt-in/privacy/deletion
- GitHub Issue: `#21` — creator indexing/control UI
