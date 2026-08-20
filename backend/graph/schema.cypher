// Run this setup against the Neo4j database before ingestion.
// Every write in the application must use the parameterized repository queries.
CREATE CONSTRAINT creator_id_unique IF NOT EXISTS
FOR (node:Creator) REQUIRE node.id IS UNIQUE;
CREATE CONSTRAINT content_id_unique IF NOT EXISTS
FOR (node:Content) REQUIRE node.id IS UNIQUE;
CREATE CONSTRAINT moment_id_unique IF NOT EXISTS
FOR (node:Moment) REQUIRE node.id IS UNIQUE;
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (node:Entity) REQUIRE node.id IS UNIQUE;
CREATE CONSTRAINT relation_id_unique IF NOT EXISTS
FOR (node:RelationAssertion) REQUIRE node.id IS UNIQUE;

CREATE INDEX moment_creator_visibility IF NOT EXISTS
FOR (node:Moment) ON (node.creator_id, node.visibility);
CREATE INDEX moment_content_time IF NOT EXISTS
FOR (node:Moment) ON (node.content_id, node.start_ms, node.end_ms);
CREATE INDEX entity_creator_type IF NOT EXISTS
FOR (node:Entity) ON (node.creator_id, node.entity_type);
CREATE INDEX relation_creator_predicate IF NOT EXISTS
FOR (node:RelationAssertion) ON (node.creator_id, node.predicate);

// Embeddings belong in PostgreSQL + pgvector, never on Neo4j nodes.

