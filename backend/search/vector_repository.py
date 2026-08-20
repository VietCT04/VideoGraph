"""pgvector repository interface with a dependency-free fixture fallback."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from backend.graph.model import VISIBILITIES


@dataclass(frozen=True)
class MomentEmbeddingRow:
    moment_id: str
    creator_id: str
    content_id: str
    start_ms: int
    end_ms: int
    semantic_text: str
    embedding: tuple[float, ...]
    embedding_model: str
    embedding_version: str | None = None
    visibility: str = "public"


@dataclass(frozen=True)
class VectorSearchFilters:
    creator_id: str
    content_id: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    allowed_visibility: tuple[str, ...] = ("public",)

    def __post_init__(self) -> None:
        if not self.creator_id:
            raise ValueError("creator_id is required")
        if not self.allowed_visibility or not set(self.allowed_visibility).issubset(VISIBILITIES):
            raise ValueError(f"allowed_visibility must be a subset of {VISIBILITIES}")
        if self.start_ms is not None and self.start_ms < 0:
            raise ValueError("start_ms must be non-negative")
        if self.end_ms is not None and (self.end_ms < 0 or (self.start_ms is not None and self.end_ms <= self.start_ms)):
            raise ValueError("end_ms must be after start_ms")


class VectorRepository(Protocol):
    def upsert(self, row: MomentEmbeddingRow) -> MomentEmbeddingRow:
        ...

    def search(self, query_embedding: Sequence[float], filters: VectorSearchFilters, top_k: int = 10) -> list[tuple[MomentEmbeddingRow, float]]:
        ...

    def delete_by_content(self, content_id: str) -> int:
        ...


class InMemoryVectorRepository:
    """Deterministic cosine-search fallback used by fixtures and local development."""

    def __init__(self) -> None:
        self.rows: dict[str, MomentEmbeddingRow] = {}

    def upsert(self, row: MomentEmbeddingRow) -> MomentEmbeddingRow:
        _validate_row(row)
        self.rows[row.moment_id] = row
        return row

    def get(self, moment_id: str) -> MomentEmbeddingRow | None:
        return self.rows.get(moment_id)

    def search(
        self,
        query_embedding: Sequence[float],
        filters: VectorSearchFilters,
        top_k: int = 10,
    ) -> list[tuple[MomentEmbeddingRow, float]]:
        if not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        query = _validated_vector(query_embedding)
        results: list[tuple[MomentEmbeddingRow, float]] = []
        for row in self.rows.values():
            if not _matches_filters(row, filters):
                continue
            if len(row.embedding) != len(query):
                raise ValueError("query embedding dimension does not match stored row")
            results.append((row, _cosine_similarity(query, row.embedding)))
        results.sort(key=lambda item: (-item[1], item[0].moment_id))
        return results[:top_k]

    def set_visibility(self, content_id: str, visibility: str) -> int:
        _check_visibility(visibility)
        updated = 0
        for moment_id, row in list(self.rows.items()):
            if row.content_id == content_id and row.visibility != visibility:
                self.rows[moment_id] = MomentEmbeddingRow(
                    **{**row.__dict__, "visibility": visibility}
                )
                updated += 1
        return updated

    def delete_by_content(self, content_id: str) -> int:
        ids = [moment_id for moment_id, row in self.rows.items() if row.content_id == content_id]
        for moment_id in ids:
            del self.rows[moment_id]
        return len(ids)


class PostgresVectorRepository:
    """DB-API adapter whose SQL values and visibility filters are parameterized."""

    UPSERT_SQL = """
        INSERT INTO moment_embeddings
            (moment_id, creator_id, content_id, start_ms, end_ms, semantic_text,
             embedding, embedding_model, embedding_version, visibility)
        VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s, %s, %s)
        ON CONFLICT (moment_id) DO UPDATE SET
            creator_id = EXCLUDED.creator_id,
            content_id = EXCLUDED.content_id,
            start_ms = EXCLUDED.start_ms,
            end_ms = EXCLUDED.end_ms,
            semantic_text = EXCLUDED.semantic_text,
            embedding = EXCLUDED.embedding,
            embedding_model = EXCLUDED.embedding_model,
            embedding_version = EXCLUDED.embedding_version,
            visibility = EXCLUDED.visibility
    """

    SEARCH_SQL = """
        SELECT moment_id, creator_id, content_id, start_ms, end_ms, semantic_text,
               embedding_model, embedding_version, visibility, embedding,
               1 - (embedding <=> %s::vector) AS similarity
        FROM moment_embeddings
        WHERE creator_id = %s
          AND visibility = ANY(%s)
          AND (%s IS NULL OR content_id = %s)
          AND (%s IS NULL OR end_ms > %s)
          AND (%s IS NULL OR start_ms < %s)
        ORDER BY embedding <=> %s::vector, moment_id
        LIMIT %s
    """

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def upsert(self, row: MomentEmbeddingRow) -> MomentEmbeddingRow:
        _validate_row(row)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                self.UPSERT_SQL,
                (
                    row.moment_id,
                    row.creator_id,
                    row.content_id,
                    row.start_ms,
                    row.end_ms,
                    row.semantic_text,
                    _vector_literal(row.embedding),
                    row.embedding_model,
                    row.embedding_version,
                    row.visibility,
                ),
            )
            self.connection.commit()
        finally:
            cursor.close()
        return row

    def search(
        self,
        query_embedding: Sequence[float],
        filters: VectorSearchFilters,
        top_k: int = 10,
    ) -> list[tuple[MomentEmbeddingRow, float]]:
        if not 1 <= top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        query = _validated_vector(query_embedding)
        vector = _vector_literal(query)
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                self.SEARCH_SQL,
                (
                    vector,
                    filters.creator_id,
                    list(filters.allowed_visibility),
                    filters.content_id,
                    filters.content_id,
                    filters.start_ms,
                    filters.start_ms,
                    filters.end_ms,
                    filters.end_ms,
                    vector,
                    top_k,
                ),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
        return [(_row_from_database(row, query), float(row[-1])) for row in rows]

    def set_visibility(self, content_id: str, visibility: str) -> int:
        _check_visibility(visibility)
        cursor = self.connection.cursor()
        try:
            cursor.execute("UPDATE moment_embeddings SET visibility = %s WHERE content_id = %s", (visibility, content_id))
            count = cursor.rowcount
            self.connection.commit()
        finally:
            cursor.close()
        return count

    def delete_by_content(self, content_id: str) -> int:
        cursor = self.connection.cursor()
        try:
            cursor.execute("DELETE FROM moment_embeddings WHERE content_id = %s", (content_id,))
            count = cursor.rowcount
            self.connection.commit()
        finally:
            cursor.close()
        return count


def _validate_row(row: MomentEmbeddingRow) -> None:
    if row.start_ms < 0 or row.end_ms <= row.start_ms:
        raise ValueError("embedding timestamps must be a non-empty non-negative range")
    if not row.moment_id or not row.creator_id or not row.content_id or not row.semantic_text:
        raise ValueError("embedding metadata is incomplete")
    _check_visibility(row.visibility)
    _validated_vector(row.embedding)


def _validated_vector(vector: Sequence[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in vector)
    if not result or any(not math.isfinite(value) for value in result):
        raise ValueError("embedding must contain finite values")
    return result


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in vector) + "]"


def _matches_filters(row: MomentEmbeddingRow, filters: VectorSearchFilters) -> bool:
    return (
        row.creator_id == filters.creator_id
        and row.visibility in filters.allowed_visibility
        and (filters.content_id is None or row.content_id == filters.content_id)
        and (filters.start_ms is None or row.end_ms > filters.start_ms)
        and (filters.end_ms is None or row.start_ms < filters.end_ms)
    )


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _row_from_database(row: Sequence[Any], query: Sequence[float]) -> MomentEmbeddingRow:
    return MomentEmbeddingRow(
        moment_id=row[0],
        creator_id=row[1],
        content_id=row[2],
        start_ms=int(row[3]),
        end_ms=int(row[4]),
        semantic_text=row[5],
        embedding=tuple(float(value) for value in row[9]) if isinstance(row[9], (list, tuple)) else tuple(query),
        embedding_model=row[6],
        embedding_version=row[7],
        visibility=row[8],
    )


def _check_visibility(value: str) -> None:
    if value not in VISIBILITIES:
        raise ValueError(f"unknown visibility {value!r}")

