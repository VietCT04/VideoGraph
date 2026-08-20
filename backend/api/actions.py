"""Framework-neutral adapter for permissioned retrieval actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.api.query import HttpResponse
from backend.actions.tools import ActionToolService
from backend.search.fusion import FusedResult


class ActionHttpAdapter:
    """Resolve an internal result ID, then execute a typed action over it."""

    def __init__(self, service: ActionToolService, result_resolver: Callable[[str], FusedResult | None]) -> None:
        self.service = service
        self.result_resolver = result_resolver

    def post(self, body: object) -> HttpResponse:
        if not isinstance(body, dict):
            return _bad_request()
        if not isinstance(body.get("action"), str) or not isinstance(body.get("creator_id"), str) or not isinstance(body.get("result_id"), str):
            return _bad_request()
        if set(body) - {"action", "creator_id", "result_id", "constraints"}:
            return _bad_request()
        constraints = body.get("constraints", {})
        if not isinstance(constraints, dict):
            return _bad_request()
        result = self.result_resolver(body["result_id"])
        if result is None:
            return HttpResponse(404, {"error": {"code": "retrieval_result_not_found"}})
        action_result = self.service.execute(body["action"], body["creator_id"], result, constraints)
        status_code = 403 if action_result.status == "denied" else 200
        return HttpResponse(status_code, action_result.to_dict())


def _bad_request() -> HttpResponse:
    return HttpResponse(400, {"error": {"code": "invalid_action_request"}})
