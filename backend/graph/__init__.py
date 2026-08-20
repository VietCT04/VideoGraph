"""Canonical graph models, ingestion, and repository interfaces."""

from .ingestion import ExtractionGraphIngestor, canonical_entity_id, canonical_moment_id
from .model import EvidenceRef, GraphEntity, GraphMoment, GraphRelation
from .repository import InMemoryGraphRepository
from .entity_resolution import (
    DeterministicCandidateScorer,
    EntityCandidate,
    EntityResolver,
    ResolutionDecision,
    normalize_entity_name,
)
from .tools import GraphHit, ParameterizedCypher, SafeGraphQueryService

__all__ = [
    "EvidenceRef",
    "ExtractionGraphIngestor",
    "GraphEntity",
    "GraphMoment",
    "GraphRelation",
    "InMemoryGraphRepository",
    "DeterministicCandidateScorer",
    "EntityCandidate",
    "EntityResolver",
    "ResolutionDecision",
    "canonical_entity_id",
    "canonical_moment_id",
    "normalize_entity_name",
    "GraphHit",
    "ParameterizedCypher",
    "SafeGraphQueryService",
]

