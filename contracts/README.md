# Shared Contracts

This directory is the canonical home for versioned cross-component schemas and
controlled ontology definitions.

Contracts are validated at service boundaries. Producers and consumers must not keep
independent copies of the extraction or retrieval-plan shapes.

## v1 contracts

- [`multimodal-extraction.schema.json`](multimodal-extraction.schema.json) carries
  content-local Moments, evidence, candidate graph facts, semantic text, and optional
  embedding metadata.
- [`retrieval-plan.schema.json`](retrieval-plan.schema.json) carries creator-scoped
  graph and semantic intent. It intentionally has no executable Cypher field.
- [`ontology.py`](ontology.py) is the Python view of the closed v1 entity and relation
  vocabulary used by both validators and fixtures.
- [`validation.py`](validation.py) provides a dependency-free boundary validator for
  the checked-in schemas. Unknown properties, entity types, and relation predicates
  fail closed.

Schema version `1.0` is part of every payload. Local IDs such as `moment_1` and
`entity_1` are valid only within one extraction payload; persistent identity remains a
backend responsibility.

The beauty, technology, and travel fixtures under `examples/` are intentionally
model-free inputs for backend and AI Service development.
