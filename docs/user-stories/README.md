# User Stories

User stories document product behavior that should remain stable across implementation details.

They are not substitutes for GitHub Issues. A story describes the user-facing requirement; issues split that requirement into implementable technical slices.

## Format

Use this structure when adding a story:

```text
# <Story title>

## Actor

## Goal

## Preconditions

## Primary Flow

## Alternative / Failure Flows

## Privacy / Safety Requirements

## Acceptance Examples

## Related Issues

## Open Questions
```

Keep stories implementation-light. Link to architecture docs/issues for technical design.

## Initial Stories

- [`creator-indexing.md`](creator-indexing.md) — creator opt-in, content selection, indexing, progress, correction, deletion
- [`viewer-search.md`](viewer-search.md) — `@creator` query, grounded retrieval, exact evidence, optional actions
