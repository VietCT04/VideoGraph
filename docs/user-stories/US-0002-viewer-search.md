# US-0002: Viewer Searches a Creator's Memory

## User Story

As a viewer, I want to ask a natural-language `@creator` question and receive grounded answers linked to exact source Moments, so that I can explore a creator's real historical content without relying on unsupported generation.

## Context

Viewer search is the core consumption flow for VideoGraph.

The backend resolves the creator, uses a small LLM planner to create a validated RetrievalPlan, searches Neo4j and pgvector in parallel, fuses/reranks results, and returns grounded evidence. A final synthesis LLM is optional and should be used only when the question genuinely needs reasoning or explanation.

## Acceptance Criteria

- [ ] Viewer can submit an `@creator` natural-language query.
- [ ] Backend resolves the handle to one canonical creator before retrieval.
- [ ] Planner output is schema/ontology validated before graph/vector execution.
- [ ] No raw model-generated Cypher is executed.
- [ ] Neo4j and semantic search can run in parallel when both branches are useful.
- [ ] Graph-only or vector-only partial success can still produce valid results when appropriate.
- [ ] Results preserve exact `content_id`, `moment_id`, and timestamps.
- [ ] Hidden/excluded/private content is filtered before fusion, synthesis, or action tools.
- [ ] Simple structured questions can return without a final synthesis LLM.
- [ ] Reasoning-heavy questions may use optional synthesis over grounded authorized evidence only.
- [ ] When no grounded evidence exists, the system does not fabricate a creator-specific fact.
- [ ] Relevant API/security/query-flow docs are updated when implementation changes these behaviors.

## Risks

- Planner latency may dominate simple queries.
- Hybrid retrieval must prove value over vector-only search through evaluation.
- Final synthesis can hide poor retrieval if grounding is not exposed separately.
- Direct-result confidence thresholds are not yet frozen.

## Follow-up Issues

- GitHub Issue: `#12` — small LLM query planner
- GitHub Issue: `#13` — safe Neo4j graph tools
- GitHub Issue: `#14` — semantic Moment retrieval
- GitHub Issue: `#15` — parallel retrieval orchestration
- GitHub Issue: `#16` — fusion/reranking
- GitHub Issue: `#17` — query API
- GitHub Issue: `#20` — viewer search UI
- GitHub Issue: `#25` — action tools
