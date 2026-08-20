# Concerns

This file records unresolved project risks, ambiguity, technical debt, and architecture questions that should survive individual coding sessions.

Remove or mark a concern resolved only when the relevant decision/implementation is actually settled.

---

## C-001 — Graph value must be demonstrated

**Status:** Partially mitigated
**Component:** Retrieval / Evaluation

### Context

Many creator-search queries can be solved with semantic vectors alone. Neo4j adds complexity and should remain only if explicit structure provides measurable or demonstrable value.

### Risk

The project could become a more complex version of video RAG without showing why the graph is needed.

### Recommended next action

Issue #23 now compares deterministic fixture baselines:

- vector-only
- graph-only
- hybrid

The demo should still include at least one cross-video structured/temporal query where
graph structure clearly improves correctness, completeness, or interpretability on real
authorized retrieval inputs. The fixture harness alone does not settle that question.

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

**Status:** Open; deterministic fixture baseline recorded, production choice pending
**Component:** AI Service / pgvector / Search

### Context

The architecture assumes one fused `semantic_text` embedding per searchable Moment. Issue #7 records a deterministic `hashing-fixture` v1 baseline at dimension 32 for offline tests, but no production model or final dimension has been chosen.

### Risk

AI Service and backend pgvector schema could become incompatible, and switching dimensions later may require re-indexing.

### Recommended next action

Choose and benchmark a production embedding model before #11 integration, record model/version/dimension in the shared contract, and keep the provider replaceable. Do not treat the dimension-32 fixture as a production benchmark.

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

Use #23's harness for reproducible fixture comparisons, then connect it to representative
videos and live graph/vector services before reporting production measurements. Clearly
label local fixture timings and any extrapolation.

---

## C-007 — Public video dataset does not perfectly match creator-memory use case

**Status:** Open  
**Component:** Data / Evaluation

### Context

Public video datasets usually optimize for action recognition, recommendation, captioning, or grounding rather than repeated creator entities, opinions, temporal preference changes, and exact cross-video memory queries. Issue #22 now provides a controlled synthetic metadata fixture for these cases.

### Risk

Evaluation data may fail to exercise the core innovation.

### Recommended next action

The synthetic fixture now covers:

- repeated entities
- recommendations/dislikes
- comparisons
- temporal changes
- vague references
- silent clips
- OCR-visible products
- graph-only, vector-only, and hybrid questions

The remaining concern is audiovisual validity: no copyrighted or external media is
included, so media-level model quality and licensing remain unverified until separately
licensed or locally generated clips are added.

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

Issue #19 now provides the fixture policy boundary and synchronized graph/vector
suppression, including creator opt-in and fail-closed query authorization. The concern
remains open for production database transactions, cache invalidation, and integration
coverage across real Neo4j/pgvector deployments.

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

Issue #17 keeps this boundary explicit: direct structured results do not call a synthesis
provider, and the optional provider receives only a normalized grounded evidence bundle.
The risk remains open until synthesis grounding and answer quality are measured by #23.

## C-012 — Indexing job fixture store is not process-durable

**Status:** Open
**Component:** Backend / PostgreSQL / Indexing

### Context

Issue #18 defines the durable job contract and state transitions, but the current local
implementation uses `InMemoryIndexingJobRepository` so the fixture path has no database
dependency.

### Risk

Jobs, progress, retry counts, and completed-store flags are lost when the process exits;
the fixture cannot yet provide crash recovery or multi-worker coordination.

### Recommended next action

Implement the PostgreSQL job repository and migration before production indexing. Keep
the processing-key uniqueness and explicit state transitions identical to the fixture
contract.

## C-013 — Product action catalog is a fixture boundary

**Status:** Open
**Component:** Action Tools / Commerce

### Context

Issue #25 uses a deterministic local catalog so canonical Product-to-action behavior can
be demonstrated without an external commerce provider.

### Risk

Fixture prices, URLs, similarity behavior, and availability are not live commerce data
and must not be presented as current market information.

### Recommended next action

Add an approved commerce adapter with provider-specific freshness, failure, and privacy
policies before exposing product actions beyond the demo.

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

---

## C-012 — Production multimodal fusion provider is not selected

**Status:** Open
**Component:** AI Service / VLM Fusion

### Context

Issue #6 provides a structured `VLMProvider` boundary and deterministic beauty,
technology, and travel fixtures, but no production multimodal model or prompt/runtime
has been selected.

### Risk

Provider-specific structured-output limits, latency, and evidence grounding behavior
may differ from the fixture contract and require adapter changes.

### Recommended next action

Select and benchmark a production structured-output provider under #23/#24. Keep the
fixture provider and shared contract as the offline fallback until that decision is
measured.

---

## C-013 — AI Service worker and result retention are process-local

**Status:** Open
**Component:** AI Service / Deployment

### Context

Issue #8 uses an in-process thread pool and memory-only result store so the API can be
tested without Redis, a broker, or a database. The main backend remains the owner of
durable indexing state.

### Risk

Process restart, multiple replicas, or worker failure can lose queued jobs and temporary
results. This is not a production reliability guarantee.

### Recommended next action

Define the production queue, retry, idempotency, and result handoff under the deployment
and indexing issues before connecting this service to durable backend jobs.
