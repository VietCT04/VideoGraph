"""Strict parsing of the viewer-facing @creator query prefix."""

from __future__ import annotations

import re
from dataclasses import dataclass


_CREATOR_QUERY = re.compile(r"^\s*@(?P<handle>[A-Za-z0-9_][A-Za-z0-9_.-]{0,63})(?:\s+(?P<question>.*))?\s*$")


class CreatorQueryParseError(ValueError):
    """Raised when a query is not addressed to one creator."""


@dataclass(frozen=True)
class CreatorQuery:
    handle: str
    question: str
    raw_query: str


def parse_creator_query(raw_query: str) -> CreatorQuery:
    if not isinstance(raw_query, str) or not raw_query.strip():
        raise CreatorQueryParseError("query must be a non-empty string")
    match = _CREATOR_QUERY.match(raw_query)
    if match is None:
        raise CreatorQueryParseError("query must start with @creator")
    question = (match.group("question") or "").strip()
    if not question:
        raise CreatorQueryParseError("query must include a question after the creator handle")
    return CreatorQuery(handle=match.group("handle").casefold(), question=question, raw_query=raw_query)

