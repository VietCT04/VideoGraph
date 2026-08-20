"""The closed v1 ontology shared by extraction and retrieval boundaries."""

from typing import Final

ONTOLOGY_VERSION: Final[str] = "1.0"
EXTRACTION_SCHEMA_VERSION: Final[str] = "1.0"
RETRIEVAL_PLAN_SCHEMA_VERSION: Final[str] = "1.0"

ENTITY_TYPES: Final[tuple[str, ...]] = (
    "Content",
    "Event",
    "Organization",
    "Person",
    "Place",
    "Product",
    "Technology",
    "Topic",
)

RELATION_TYPES: Final[tuple[str, ...]] = (
    "ABOUT",
    "APPEARS_IN",
    "COMPARES",
    "CREATED_BY",
    "DISLIKES",
    "LOCATED_IN",
    "LIKES",
    "MENTIONS",
    "OWNS",
    "PART_OF",
    "PREFERS_OVER",
    "RECOMMENDS",
    "SWITCHED_TO",
    "USES",
    "VISITS",
    "WEARS",
)

RESULT_TYPES: Final[tuple[str, ...]] = (
    "Entity",
    "Moment",
    "Relation",
)

CONTENT_SOURCE_TYPES: Final[tuple[str, ...]] = (
    "live",
    "video",
)


def is_entity_type(value: object) -> bool:
    """Return whether ``value`` is a known v1 entity type."""

    return isinstance(value, str) and value in ENTITY_TYPES


def is_relation_type(value: object) -> bool:
    """Return whether ``value`` is a known v1 relation predicate."""

    return isinstance(value, str) and value in RELATION_TYPES
