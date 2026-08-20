"""Replaceable embedding boundary with a deterministic local hashing fixture."""

from __future__ import annotations

import copy
import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from contracts.validation import validate_extraction


@dataclass(frozen=True)
class EmbeddingMetadata:
    """Model identity required to compare stored vectors safely."""

    model: str
    version: str
    dimension: int
    normalized: bool

    def __post_init__(self) -> None:
        if not self.model.strip() or not self.version.strip():
            raise ValueError("embedding model and version must not be empty")
        if self.dimension <= 0:
            raise ValueError("embedding dimension must be positive")


@dataclass(frozen=True)
class EmbeddingBatch:
    """Ordered vectors plus metadata for one provider call."""

    metadata: EmbeddingMetadata
    vectors: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        for vector in self.vectors:
            if len(vector) != self.metadata.dimension:
                raise ValueError("embedding vector length must match metadata dimension")

    def vector_payload(self, index: int) -> dict[str, object]:
        """Return one vector in the shared extraction embedding shape."""

        vector = self.vectors[index]
        return {
            "model": self.metadata.model,
            "version": self.metadata.version,
            "dimension": self.metadata.dimension,
            "vector": list(vector),
            "normalized": self.metadata.normalized,
        }


class EmbeddingProvider(Protocol):
    """Replaceable boundary for a local or hosted embedding model."""

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        """Embed fused semantic text in input order."""


class HashingEmbeddingProvider:
    """A deterministic, dependency-free baseline for local development."""

    _SYNONYMS = {
        "recommends": "recommend",
        "recommend": "recommend",
        "suggests": "recommend",
        "suggest": "recommend",
        "suggesting": "recommend",
        "darker": "deep",
        "deeper": "deep",
        "dark": "deep",
        "deep": "deep",
        "lipsticks": "lipstick",
        "skins": "skin",
        "tones": "tone",
        "explains": "explain",
        "explaining": "explain",
        "installing": "install",
        "she": "creator",
    }

    def __init__(
        self,
        dimension: int = 32,
        batch_size: int = 32,
        model: str = "hashing-fixture",
        version: str = "1",
        normalized: bool = True,
    ) -> None:
        self.metadata = EmbeddingMetadata(model, version, dimension, normalized)
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.batch_size = batch_size

    def embed(self, texts: Sequence[str]) -> EmbeddingBatch:
        """Return one deterministic vector per input text, preserving order."""

        vectors: list[tuple[float, ...]] = []
        for batch_start in range(0, len(texts), self.batch_size):
            batch = texts[batch_start : batch_start + self.batch_size]
            vectors.extend(self._embed_batch(batch))
        return EmbeddingBatch(self.metadata, tuple(vectors))

    def _embed_batch(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.metadata.dimension
        for token in _canonical_tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.metadata.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        if self.metadata.normalized:
            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]
        return tuple(vector)


def embed_extraction(
    extraction: dict[str, object],
    provider: EmbeddingProvider,
) -> dict[str, object]:
    """Embed each fused Moment's semantic text and revalidate the payload."""

    validate_extraction(extraction)
    result = copy.deepcopy(extraction)
    moments = result["moments"]
    if not isinstance(moments, list):
        raise ValueError("validated extraction moments must be a list")
    texts = [moment["semantic_text"] for moment in moments]
    if not all(isinstance(text, str) for text in texts):
        raise ValueError("validated semantic_text values must be strings")
    batch = provider.embed(texts)
    if len(batch.vectors) != len(moments):
        raise ValueError("embedding provider returned the wrong number of vectors")
    for index, moment in enumerate(moments):
        moment["embedding"] = batch.vector_payload(index)
    pipeline = result.get("pipeline")
    if isinstance(pipeline, dict):
        pipeline["embedding_model"] = batch.metadata.model
    validate_extraction(result)
    return result


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Return cosine similarity for sanity checks and provider-neutral callers."""

    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")
    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _canonical_tokens(text: str) -> tuple[str, ...]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return tuple(HashingEmbeddingProvider._SYNONYMS.get(token, token) for token in tokens)
