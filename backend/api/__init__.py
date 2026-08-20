"""Framework-neutral HTTP adapters for the main backend."""

from .actions import ActionHttpAdapter
from .indexing import IndexingHttpAdapter
from .privacy import PrivacyHttpAdapter
from .query import HttpResponse, QueryHttpAdapter

__all__ = ["ActionHttpAdapter", "HttpResponse", "IndexingHttpAdapter", "PrivacyHttpAdapter", "QueryHttpAdapter"]
