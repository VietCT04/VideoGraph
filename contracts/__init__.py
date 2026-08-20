"""Versioned, dependency-free shared contracts for VideoGraph."""

from .ontology import ENTITY_TYPES, RELATION_TYPES
from .validation import (
    ContractValidationError,
    validate_extraction,
    validate_retrieval_plan,
)

__all__ = [
    "ContractValidationError",
    "ENTITY_TYPES",
    "RELATION_TYPES",
    "validate_extraction",
    "validate_retrieval_plan",
]
