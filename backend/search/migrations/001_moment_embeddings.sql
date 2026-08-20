-- Issue #11: semantic Moment storage. Apply with the deployment's pgvector version.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS moment_embeddings (
    moment_id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    content_id TEXT NOT NULL,
    start_ms BIGINT NOT NULL CHECK (start_ms >= 0),
    end_ms BIGINT NOT NULL CHECK (end_ms > start_ms),
    semantic_text TEXT NOT NULL,
    embedding vector NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_version TEXT,
    visibility TEXT NOT NULL DEFAULT 'public'
        CHECK (visibility IN ('public', 'creator_only', 'hidden', 'excluded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS moment_embeddings_creator_visibility
    ON moment_embeddings (creator_id, visibility);
CREATE INDEX IF NOT EXISTS moment_embeddings_content_time
    ON moment_embeddings (content_id, start_ms, end_ms);

-- Use the deployment's configured embedding dimension and index type. The repository
-- rejects mismatched query dimensions before a search is issued.
CREATE INDEX IF NOT EXISTS moment_embeddings_embedding_cosine
    ON moment_embeddings USING hnsw (embedding vector_cosine_ops);

