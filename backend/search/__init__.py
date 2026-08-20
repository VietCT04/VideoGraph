"""Semantic storage and retrieval interfaces."""

from .vector_repository import (
    InMemoryVectorRepository,
    MomentEmbeddingRow,
    PostgresVectorRepository,
    VectorSearchFilters,
)
from .embeddings import EmbeddingProvider, FixtureHashEmbeddingProvider
from .semantic_retrieval import SemanticHit, SemanticMomentRetriever, SemanticSearchResult, index_extraction_fixture

__all__ = [
    "InMemoryVectorRepository",
    "MomentEmbeddingRow",
    "PostgresVectorRepository",
    "VectorSearchFilters",
    "EmbeddingProvider",
    "FixtureHashEmbeddingProvider",
    "SemanticHit",
    "SemanticMomentRetriever",
    "SemanticSearchResult",
    "index_extraction_fixture",
]

