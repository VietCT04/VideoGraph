# Concerns

This file records unresolved project risks, ambiguity, technical debt, and architecture questions that should survive individual coding sessions.

Remove or mark a concern resolved only when the relevant decision/implementation is actually settled.

---

## C-001 — Graph value must be demonstrated

**Status:** Open  
**Component:** Retrieval / Evaluation

### Context

Many creator-search queries can be solved with semantic vectors alone. Neo4j adds complexity and should remain only if explicit structure provides measurable or demonstrable value.

### Risk

The project could become a more complex version of video RAG without showing why the graph is needed.

### Recommended next action

Issue #23 must compare:

- vector-only
- graph-only
- hybrid

The demo should include at least one cross-video structured/temporal query where graph structure clearly improves correctness, completeness, or interpretability.

---

## C-002 — Controlled graph ontology is not frozen

**Status:** Resolved for v1; future additions require a versioned contract change
**Component:** Contracts / AI Service / Neo4j / Planner

### Context

The v1 entity and relation vocabulary is canonical in `contracts/ontology.py` and the
two JSON Schemas. It is intentionally small and closed.

### Risk

Future additions could still create incompatible ontology versions if they bypass the
shared contract.

### Recommended next action

Future ontology work must use the v1 vocabulary from:

- extraction schema
- VLM structured output
- planner schema
- graph ingestion
- graph query tools

Reject unknown predicates at validation boundaries and version any incompatible change.

---

## C-003 — Embedding model and dimension are not selected

**Status:** Open  
**Component:** AI Service / pgvector / Search

### Context

The architecture assumes one fused `semantic_text` embedding per searchable Moment, but no final model/dimension has been chosen.

### Risk

AI Service and backend pgvector schema could become incompatible, and switching dimensions later may require re-indexing.

### Recommended next action

Choose a baseline embedding model before #7/#11 integration, record model/version/dimension in the shared contract, and keep the provider replaceable.

---

## C-004 — Entity resolution can create destructive false merges

**Status:** Open  
**Component:** Knowledge Graph

### Context

Mentions such as `Rare Beauty Humble`, `my Rare Beauty lipstick`, and `this lipstick` may or may not refer to the same real-world product.

### Risk

Aggressive merging corrupts canonical creator memory and makes later corrections difficult.

### Recommended next action

Issue #10 should support:

- high-confidence automatic merge
- ambiguous candidate links
- reversible decisions
- source-evidence preservation
- explicit thresholds/configuration

Prefer false splits over irreversible false merges in the MVP.

---

## C-005 — Planner latency/provider is not benchmarked

**Status:** Open  
**Component:** Query Planner

### Context

The query architecture uses a small LLM before graph/vector retrieval.

### Risk

Planner latency could dominate otherwise-fast retrieval and make simple queries feel slow.

### Recommended next action

Instrument #12 from the start. After the baseline works, evaluate whether common deterministic intents justify a non-LLM fast path.

Do not optimize this before measuring the baseline.

---

## C-006 — Backfill and query latency figures are estimates only

**Status:** Open  
**Component:** Performance / Evaluation

### Context

Planning discussions include rough indexing and query latency ranges, but they have not been measured on the actual models, dataset, hardware, and database configuration.

### Risk

The team could make unsupported performance claims in the demo/presentation.

### Recommended next action

Use #23 to measure representative videos and queries. Report measured values and clearly label any extrapolation.

---

## C-007 — Public video dataset does not perfectly match creator-memory use case

**Status:** Open  
**Component:** Data / Evaluation

### Context

Public video datasets usually optimize for action recognition, recommendation, captioning, or grounding rather than repeated creator entities, opinions, temporal preference changes, and exact cross-video memory queries.

### Risk

Evaluation data may fail to exercise the core innovation.

### Recommended next action

Build #22 controlled creator-memory dataset with:

- repeated entities
- recommendations/dislikes
- comparisons
- temporal changes
- vague references
- silent clips
- OCR-visible products
- graph-only, vector-only, and hybrid questions

Document license/source terms for external media.

---

## C-008 — Silent-video segmentation needs measurable fallback behavior

**Status:** Open  
**Component:** AI Service

### Context

Speech-aligned chunking is strong for creator speech, but some TikTok-style content has music, text overlays, or purely visual product demonstrations.

### Risk

A Whisper-first pipeline may produce poor or empty Moments for silent content.

### Recommended next action

Issue #3 should combine scene/shot detection with visual/OCR change signals and test against silent clips from #22.

Do not equate one camera shot with one semantic Moment by definition.

---

## C-009 — Privacy must stay consistent across duplicated representations

**Status:** Open  
**Component:** Backend / Neo4j / pgvector

### Context

The same Moment/fact can be represented in application state, Neo4j, and pgvector.

### Risk

Excluding/deleting content in one store while leaving it searchable in another can expose data the creator intended to remove.

### Recommended next action

Issue #19 must define deletion/suppression propagation and retrieval filters across every representation. Add integration tests that verify hidden content cannot surface through either graph or vector paths.

---

## C-010 — Final synthesis LLM can hide retrieval quality

**Status:** Open  
**Component:** Query API / Evaluation

### Context

A powerful final LLM can make weak retrieval appear plausible by generating fluent answers.

### Risk

The demo may overstate retrieval correctness and lose the evidence-backed product distinction.

### Recommended next action

Keep direct structured results as the default for simple queries. Evaluate retrieval/evidence correctness separately from synthesis quality. Always expose exact source Moments.

---

## C-011 — GPU/provider choice remains open

**Status:** Open  
**Component:** AI Service / Infra

### Context

The system is designed to allow the AI Service to move between GPU classes/providers, but the baseline deployment has not been selected.

### Risk

Model memory requirements, availability, and cost can block integration late in the project.

### Recommended next action

During #24, benchmark the selected VLM/ASR stack on the intended development GPU and keep deployment/provider assumptions out of shared backend contracts.
