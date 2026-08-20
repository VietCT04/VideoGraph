# Query Flow

## 1. Goal

A viewer query has the form:

```text
@creator question
```

Example:

```text
@alice which red lipstick did she recommend for darker skin?
```

The backend should interpret the request once, then search structured graph facts and semantic Moments in parallel.

---

## 2. End-to-End Flow

```text
@creator + question
        ↓
parse creator handle
        ↓
resolve creator_id
        ↓
privacy authorization + content visibility
        ↓
small LLM planner
        ↓
validated RetrievalPlan
        │
   ┌────┴──────────────┐
   ↓                   ↓
graph plan        semantic_query
   ↓                   ↓
safe graph tools     query embedding
   ↓                   ↓
Neo4j               pgvector
   │                   │
   └────────┬──────────┘
            ↓
      fusion / rerank
            ↓
      grounded result
            ↓
   ┌────────┴────────┐
   ↓                 ↓
direct response   optional synthesis
```

The planner is not the retrieval engine. It produces instructions for retrieval components.

## 2.1 Privacy gate (#19)

The query application service performs the backend-owned creator privacy check after
creator resolution and before hybrid retrieval. The policy requires AI Memory opt-in and
at least one included public content item. Content hide/exclude/reject/delete operations
also synchronize graph and vector visibility or deletion, so the retrieval branches do
not receive stale public rows. The planner cannot override this gate, and an unauthorized
request returns `privacy_denied` before fusion or optional synthesis.

---

## 3. RetrievalPlan

The planner should output a versioned machine-validated structure.

Conceptual example:

```json
{
  "creator_id": "creator_42",
  "intent": "find_recommendation",
  "graph": {
    "relations": ["RECOMMENDS"],
    "entity_types": ["Product"],
    "filters": {
      "category": "lipstick",
      "color": "red"
    }
  },
  "semantic_query": "red lipstick recommended for darker skin",
  "temporal": null,
  "top_k": 10,
  "result_type": "product_with_evidence"
}
```

The canonical schema belongs under:

```text
contracts/retrieval-plan.schema.json
```

Unknown relations/entity types must be rejected by validation.

The #12 planner slice implements this boundary in `backend/planner/`. The parser
requires an `@creator` prefix, resolves the handle to a backend `creator_id`, and
passes only the remaining question to a provider interface. The fixture provider is
model-free and deterministic; a real provider must return structured JSON that is
validated by `contracts.validation.validate_retrieval_plan` before retrieval.

Planner results include `used_fallback`, provider error text suitable for internal
metrics, and `latency_ms`. Invalid provider output falls back to a validated plan with
separate graph intent and semantic text. Creator scope never comes from model output.

---

## 4. Why the Planner Produces Two Representations

Neo4j and vector search need different inputs.

Graph retrieval wants explicit structure:

```text
creator_id = creator_42
relation = RECOMMENDS
entity_type = Product
category = lipstick
```

Semantic retrieval wants a natural semantic representation:

```text
red lipstick recommended for darker skin
```

Do not force one rewritten sentence to serve as the full graph query specification.

---

## 5. Planner Safety

The planner must not output executable raw Cypher.

Incorrect architecture:

```text
user
→ LLM
→ arbitrary Cypher
→ Neo4j
```

Required architecture:

```text
user
→ LLM planner
→ validated structured plan
→ backend graph tools
→ parameterized Cypher
→ Neo4j
```

Benefits:

- prevents destructive/unbounded model-generated queries
- keeps creator scoping deterministic
- keeps ontology controlled
- makes tests straightforward
- allows planner-provider replacement

---

## 6. Graph Retrieval

Backend graph tools own Cypher templates.

Possible tool interface:

```text
get_creator_entities(...)
get_creator_relations(...)
get_entity_evidence(...)
get_entity_history(...)
get_relations_between(...)
get_moments_for_entity(...)
```

Every query must:

- use parameterized Cypher
- scope to the target creator
- enforce visibility
- return evidence Moment IDs/timestamps where relevant
- avoid unbounded traversal

Example conceptual query:

```cypher
MATCH (c:Creator {id: $creator_id})-[:RECOMMENDS]->(p:Product)
WHERE p.category = $category
RETURN p
```

The actual tool layer should own this query, not the planner.

## Issue #13 safe graph tool slice

`backend/graph/tools.py` validates the complete plan again at the graph boundary and
maps only the shared v1 relation/entity values to fixed Cypher templates. Creator ID,
visibility, content, entity, and time filters are parameters; there is no API field for
raw Cypher. The fixture path uses the same validated plan and repository filters, while
the Neo4j path accepts a parameterized executor callback and normalizes evidence into
the same `GraphHit` shape.

Unsupported or malformed plans fail closed with `GraphToolError`. Graph templates use
bounded `LIMIT` values and return canonical entity labels plus Moment/content evidence
timestamps for downstream fusion.

---

## 7. Semantic Retrieval

The planner's `semantic_query` is embedded using a model compatible with stored Moment embeddings.

```text
semantic_query
      ↓
query embedding
      ↓
creator-scoped pgvector ANN search
      ↓
relevant Moments
```

Search filters can include:

- creator
- content
- time range
- visibility
- top-k

Each result should preserve:

```text
moment_id
similarity score
semantic_text
content_id
start_ms
end_ms
```

## Issue #14 semantic retrieval slice

`backend/search/semantic_retrieval.py` embeds only the validated planner
`semantic_query`, builds creator/content/time/visibility filters, and returns a
normalized `SemanticHit` containing the canonical Moment ID, similarity, semantic
text, content ID, and exact timestamps. `EmbeddingProvider` keeps model-specific code
behind an adapter; `FixtureHashEmbeddingProvider` and `InMemoryVectorRepository`
provide deterministic local plumbing without external dependencies.

Fixture indexing uses `canonical_moment_id` from graph ingestion, so a vector result
resolves to the same Moment evidence as a graph result. The fixture embedding is a
repeatable hashing baseline, not a measured production semantic-quality claim.

---

## 8. Parallel Execution

When both branches are useful, execute them concurrently.

Do not do:

```text
Neo4j
  ↓ wait
pgvector
```

Do:

```text
         RetrievalPlan
          ┌───┴───┐
          ↓       ↓
       Neo4j   pgvector
          └───┬───┘
              ↓
            fusion
```

If one branch fails or times out, the other branch may still produce a valid partial result.

The retrieval orchestrator should preserve per-branch latency and failure metadata for debugging/evaluation.

## Issue #15 orchestration slice

`backend/search/orchestrator.py` submits graph and vector callables to two worker
threads from one validated plan. Each branch has an independent timeout and produces
`success`, `failed`, or `timeout` status with latency/error metadata. A valid branch's
results are retained when the other branch fails, and the `RetrievalBundle` exposes a
`partial_success` signal without performing ranking or response wording.

---

## 9. Fusion and Reranking

Graph and vector hits may refer to the same canonical entity/Moment.

Example:

```text
Graph:
Alice -[:RECOMMENDS]-> Dior 999

Vector:
Moment 83
"Alice recommends Dior 999 because it works well on deeper skin tones."
```

Shared IDs/evidence allow the system to combine them:

```text
Dior 999
- exact RECOMMENDS graph match
- strong semantic match for darker skin
- evidence: Moment 83
```

Baseline fusion should be deterministic before introducing another LLM.

Potential features:

- exact graph relation match
- graph filter match
- vector similarity
- evidence count
- recency when requested
- entity confidence
- relation confidence

Avoid overly complex learned reranking before a measurable baseline exists.

---

## 10. Direct Response vs Final Synthesis

A second LLM is optional.

### Direct response path

Use when retrieval already yields a high-confidence structured answer.

Examples:

```text
What lipsticks does she use?
Show videos where she used Rare Beauty.
What products did she recommend?
```

The backend can return entities plus evidence directly.

### Synthesis path

Use when the question requires comparison, explanation, or multi-hop reasoning.

Examples:

```text
Why did she switch from A to B?
Compare her opinions on A and B over the last year.
Did she ever return to the product she stopped using?
```

The synthesis model receives only already-authorized grounded evidence.

---

## 11. Latency Targets

These are engineering targets, not measured guarantees.

Warm-request planning direction:

| Stage | Direction |
| --- | ---: |
| creator parse/lookup | low milliseconds |
| small planner LLM | ~200–800 ms target range |
| query embedding | tens of milliseconds |
| Neo4j retrieval | tens to low hundreds of milliseconds |
| pgvector retrieval | tens of milliseconds |
| fusion/rerank | tens to low hundreds of milliseconds |

Because graph/vector search run in parallel, total retrieval time is closer to the slower branch than the sum of both branches.

A useful target for planner + retrieval + fusion without final synthesis is roughly sub-second to low-single-second behavior under demo-scale warm conditions, but only benchmark data should be used for final claims.

The optional synthesis call can add substantial latency and should not be mandatory for simple queries.

## Issue #16 fusion slice

`backend/search/fusion.py` groups graph hits by canonical entity ID and joins vector
hits through their canonical Moment IDs. It aggregates exact content/timestamp
evidence, retains graph relation and vector similarity signals, and applies a fixed
deterministic score with stable ID tie-breaking. Each result carries a
`direct_answer_eligible` signal; fusion does not invoke a second LLM or write final
response prose.

## Issue #17 query application slice

`backend/query/service.py` composes the existing planner, hybrid retrieval, and fusion
boundaries. `QueryApplicationService.execute()` resolves the `@creator` query through
the planner, sends the validated plan to both retrieval branches, and serializes fused
results with exact canonical Moment/content evidence. The framework-neutral
`backend/api/query.py` adapter exposes the same behavior as a `POST /query`-shaped
request without choosing FastAPI, Flask, or another web framework before one is part of
the repository.

The direct/synthesis decision remains explicit:

```text
fused results
   ├─ high-confidence structured query → structured response
   └─ complex or non-eligible query → optional provider over GroundedEvidenceBundle
```

The synthesis provider receives only creator ID, the remaining question, normalized
result labels/relations/scores, exact evidence timestamps, and a partial-success flag.
It cannot access graph/vector repositories or raw planner/database exceptions. If no
provider is configured or it fails, the API preserves the grounded results and returns
`grounded` with a machine-readable warning. Debug responses report planner, graph,
vector, fusion, synthesis, and total latency separately; these values are instrumentation
only until measured by the evaluation harness.

## 10.1 Grounded action tools (#25)

Actions branch from a resolved fused result, not from raw user text:

```text
grounded FusedResult
       ↓
privacy evidence check
       ↓
typed action tool
   ┌───┼──────────────┐
   ↓   ↓              ↓
jump product      similar products
```

`jump_to_timestamp` selects an exact evidence item and returns its canonical
`content_id`, `moment_id`, and timestamps. Product lookup and similarity use the
canonical Product entity ID from the fused result and a deterministic local catalog in
the fixture path. Tool results are separate from query evidence, so lookup failures do
not discard the creator's grounded source. Hidden or excluded evidence is rejected
before any action adapter runs.

---

## 12. Simple-Query Fast Path

A later optimization may bypass the planner LLM for common deterministic patterns.

Conceptual architecture:

```text
@creator query
      ↓
fast router
   ┌──┴──┐
   ↓     ↓
known   complex
intent  intent
   ↓     ↓
template small planner LLM
   └──┬──┘
      ↓
hybrid retrieval
```

Do not implement this before the planner baseline is working and measured.

---

## 13. Query Examples

### Graph-dominant

```text
@alice what products did she recommend?
```

Primary signal: `Creator -[:RECOMMENDS]-> Product`.

### Vector-dominant

```text
@alice where did she talk about makeup for dry skin?
```

Primary signal: semantic Moment similarity.

### Hybrid

```text
@alice which red lipstick did she recommend for darker skin?
```

Graph narrows relation/category; semantic search captures the contextual phrase `darker skin`.

### Temporal graph + evidence

```text
@alice what foundation did she use before switching to Rare Beauty?
```

Graph provides structured history; evidence Moments support the sequence.

---

## 14. Evaluation

The benchmark must compare:

- vector-only
- graph-only
- hybrid

Measure at least:

- retrieval Recall@K / MRR where ground truth exists
- graph query correctness
- hybrid result correctness
- answer/evidence grounding
- planner mapping accuracy
- planner latency
- graph latency
- vector latency
- fusion latency
- synthesis latency when used

The graph should remain in the architecture only if evaluation/demo use cases show value beyond vector-only retrieval.

---

## 15. Related Issues

- #2 retrieval plan contract
- #12 small LLM planner
- #13 safe graph tools
- #14 semantic retrieval
- #15 parallel retrieval
- #16 fusion/reranking
- #17 query API
- #20 viewer UI
- #23 evaluation

