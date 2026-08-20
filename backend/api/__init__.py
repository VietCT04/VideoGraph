"""Framework-neutral HTTP adapters for the main backend."""

from .indexing import IndexingHttpAdapter
from .privacy import PrivacyHttpAdapter
from .query import HttpResponse, QueryHttpAdapter

__all__ = ["HttpResponse", "IndexingHttpAdapter", "PrivacyHttpAdapter", "QueryHttpAdapter"]
