# User Stories

User stories describe product behavior from a user's perspective and are the source for implementation issues.

They are not substitutes for GitHub Issues. A user story captures broad product behavior; implementation work should be split into focused GitHub Issues.

## Filename Format

```text
US-0001-short-title.md
```

Use monotonically increasing story numbers.

## Template

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

Keep user stories implementation-light. Put technical design in architecture docs and focused GitHub Issues.

## Initial Stories

- [`US-0001-creator-indexing.md`](US-0001-creator-indexing.md) — creator opt-in, content selection, indexing, progress, correction, deletion
- [`US-0002-viewer-search.md`](US-0002-viewer-search.md) — `@creator` query, grounded retrieval, exact evidence, optional actions
