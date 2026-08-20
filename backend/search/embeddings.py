"""Embedding-provider boundary and deterministic fixture embedding adapter."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    model: str
    version: str
    dimension: int

    def embed(self, text: str) -> tuple[float, ...]:
        ...


class FixtureHashEmbeddingProvider:
    """Dependency-free token/character hashing adapter for local fixtures.

    This provides repeatable vector plumbing, not a quality semantic model. Production
    providers must use the same dimension/model/version for indexed and query vectors.
    """

    def __init__(self, dimension: int = 32, model: str = "fixture-hash", version: str = "1") -> None:
        if dimension < 4:
            raise ValueError("fixture embedding dimension must be at least 4")
        self.dimension = dimension
        self.model = model
        self.version = version

    def embed(self, text: str) -> tuple[float, ...]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be non-empty")
        values = [0.0] * self.dimension
        normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold())
        tokens = normalized.split()
        features = tokens + [normalized[index:index + 3] for index in range(max(0, len(normalized) - 2))]
        for feature in features:
            digest = hashlib.sha256(feature.encode()).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 else -1.0
            values[bucket] += sign
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / norm for value in values)

