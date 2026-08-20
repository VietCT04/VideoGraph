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

### Constrained optimization loop (#27)

The benchmark can optionally evaluate a finite candidate set against the same versioned
fixture baseline. The candidate surface is configuration-only:

- chunk target duration and frames per chunk
- VLM prompt version identifier
- graph/vector reranking weights
- retrieval `top_k`

The evaluator rejects unknown or out-of-range fields before running a candidate. It applies
quality-regression, minimum-metric, latency, and relative-cost gates, and chooses the best
passing candidate deterministically by objective, latency, cost, and candidate ID. The
current fixture adapter uses deterministic relative latency/cost models; it does not claim
production query performance. Optional patch proposals are report metadata only and cannot
apply code or deploy changes.

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
- #27 constrained benchmark optimization
