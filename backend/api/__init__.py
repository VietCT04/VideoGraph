"""Framework-neutral HTTP adapters for the main backend."""

from .indexing import IndexingHttpAdapter
from .query import HttpResponse, QueryHttpAdapter

__all__ = ["HttpResponse", "IndexingHttpAdapter", "QueryHttpAdapter"]
