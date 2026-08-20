"""Small HTTP-shaped adapter for the dependency-free query application service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.planner.parser import CreatorQueryParseError
from backend.privacy.service import PrivacyDenied
from backend.query.service import QueryApplicationService


@dataclass(frozen=True)
class HttpResponse:
    """Framework-independent status/body pair for an HTTP integration later."""

    status_code: int
    body: dict[str, Any]


class QueryHttpAdapter:
    """Adapt a JSON ``POST /query`` body without selecting a web framework."""

    def __init__(self, service: QueryApplicationService) -> None:
        self.service = service

    def post(self, body: object) -> HttpResponse:
        if not isinstance(body, dict):
            return _bad_request("request body must be a JSON object")
        unknown = set(body) - {"query", "debug"}
        if unknown:
            return _bad_request("request contains unsupported fields")
        query = body.get("query")
        if not isinstance(query, str) or not query.strip():
            return _bad_request("query must be a non-empty string")
        debug = body.get("debug", False)
        if not isinstance(debug, bool):
            return _bad_request("debug must be a boolean")
        try:
            response = self.service.execute(query, debug=debug)
        except CreatorQueryParseError as error:
            return _bad_request(str(error))
        except PrivacyDenied:
            return HttpResponse(403, {"error": {"code": "privacy_denied"}})
        except ValueError:
            return _bad_request("query could not be resolved")
        return HttpResponse(status_code=200, body=response)


def _bad_request(message: str) -> HttpResponse:
    return HttpResponse(
        status_code=400,
        body={"error": {"code": "invalid_query", "message": message}},
    )
