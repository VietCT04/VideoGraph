# Viewer Searches a Creator's Memory

## Actor

Viewer searching one opted-in creator's indexed content history.

## Goal

Ask a natural-language `@creator` question and receive grounded results linked to the creator's actual source Moments.

## Preconditions

- The creator has opted in.
- At least some allowed content has completed indexing.
- The viewer query can resolve to a valid creator identity.

## Primary Flow

1. Viewer enters a query such as:

   ```text
   @alice which red lipstick did she recommend for darker skin?
   ```

2. Backend resolves `@alice` to a canonical `creator_id`.
3. Small LLM planner converts the request into a validated RetrievalPlan.
4. Neo4j structured retrieval and pgvector semantic retrieval run in parallel when useful.
5. Backend fuses/deduplicates/reranks the evidence.
6. If the evidence already answers the query confidently, backend returns a direct structured result.
7. If the question requires synthesis/reasoning, an optional LLM receives only authorized grounded evidence.
8. UI shows the answer/result plus exact content/timestamp evidence.
9. Viewer may jump to a source Moment or invoke an allowed action.

## Alternative / Failure Flows

### Creator not found

Return a clear creator-resolution error. Do not search all creators by default.

### Creator has not opted in

Return an unavailable/not-enabled result without exposing indexed or private data.

### Planner output invalid

Reject/fallback safely. Do not execute unknown relations or raw generated Cypher.

### Graph branch fails

Semantic results may still be returned if valid and sufficient.

### Vector branch fails

Graph results may still be returned if valid and sufficient.

### No grounded evidence

Return no result or insufficient evidence rather than fabricating a creator-specific answer.

## Privacy / Safety Requirements

- Retrieval is creator-scoped.
- Hidden/excluded/private content is filtered before fusion/synthesis.
- The final synthesis model cannot override access control.
- Every surfaced creator-specific fact should retain source evidence when available.

## Acceptance Examples

### Graph-dominant query

```text
@alice what products did she recommend?
```

Expected behavior:

- retrieve explicit `RECOMMENDS` relationships
- return products with evidence Moments
- final synthesis LLM is not required

### Vector-dominant query

```text
@alice where did she talk about makeup for dry skin?
```

Expected behavior:

- semantic search retrieves matching Moments despite wording mismatch
- result links to exact source timestamps

### Hybrid query

```text
@alice which red lipstick did she recommend for darker skin?
```

Expected behavior:

- graph branch enforces recommendation/product structure
- semantic branch captures the contextual `darker skin` meaning
- fused result preserves the strongest exact evidence

### Reasoning-heavy query

```text
@alice why did she switch from foundation A to foundation B?
```

Expected behavior:

- retrieve temporal graph facts and relevant explanatory Moments
- optional synthesis summarizes only retrieved evidence
- source Moments remain visible

## Related Issues

- #12 query planner
- #13 safe Neo4j tools
- #14 semantic retrieval
- #15 parallel retrieval
- #16 fusion/reranking
- #17 query API
- #20 viewer UI
- #25 action tools

## Open Questions

- Exact confidence threshold for direct response versus synthesis.
- Whether simple deterministic intents should later bypass the planner LLM.
- Final ranking formula before benchmark data exists.
