# Creator Enables and Builds AI Memory

## Actor

Creator whose video/LIVE content will become searchable through VideoGraph.

## Goal

Explicitly enable creator memory, choose which content can be indexed, see processing progress, and retain control over corrections, visibility, exclusion, and deletion.

## Preconditions

- Creator identity is known to the backend.
- Creator is authorized to manage the selected content.
- VideoGraph memory is disabled by default until the creator opts in.

## Primary Flow

1. Creator opens VideoGraph memory settings.
2. Creator explicitly enables AI Memory.
3. Creator chooses videos/LIVE recordings to include.
4. Backend creates asynchronous indexing jobs.
5. UI shows queued/processing/completed/failed status.
6. Completed extraction is written into canonical graph and vector representations.
7. Creator can inspect basic extracted memory/evidence.
8. Creator can correct/reject/hide content or facts when supported.
9. Included content becomes available to viewer `@creator` search.

## Alternative / Failure Flows

### Processing failure

- Failed job remains visible.
- Error state is actionable.
- Creator can retry/re-index without duplicating persistent Moments.

### Creator excludes content

- Excluded content becomes unavailable to viewer retrieval.
- Graph and vector representations are removed or suppressed consistently.

### Creator disables AI Memory

- Viewer search must not surface persistent creator memory while disabled.
- Data-retention/deletion behavior must follow the backend policy defined by the implementation issue/contract.

## Privacy / Safety Requirements

- Opt-in is explicit.
- Private/excluded content is never implicitly indexed for viewer search.
- Visibility is enforced by the backend before any LLM sees retrieval results.
- Client-provided ownership/visibility values are not trusted without server validation.
- Deletion/exclusion must apply across all searchable representations.

## Acceptance Examples

### Successful indexing

```text
Creator selects 10 videos
→ 10 durable jobs are created
→ jobs complete asynchronously
→ creator sees status
→ searchable Moments appear only for allowed content
```

### Re-index

```text
Creator retries one failed video
→ same logical content/Moments are updated
→ no duplicate graph/vector rows are created
```

### Exclusion

```text
Creator hides Video A
→ graph retrieval cannot return Video A evidence
→ vector search cannot return Video A Moments
```

## Related Issues

- #18 indexing jobs
- #19 opt-in/privacy/deletion
- #21 creator UI
- #8 AI Service API
- #9 Neo4j ingestion
- #11 pgvector storage

## Open Questions

- Exact creator review/correction UX for v1.
- Retention behavior when AI Memory is disabled versus content explicitly deleted.
- Which content-source integrations are available in the hackathon environment.
