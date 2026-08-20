"""Framework-neutral creator privacy-control adapter."""

from __future__ import annotations

from typing import Any

from backend.api.query import HttpResponse
from backend.privacy.service import PrivacyControlService, PrivacyDenied


class PrivacyHttpAdapter:
    """Map creator-management requests to server-side policy operations."""

    def __init__(self, service: PrivacyControlService) -> None:
        self.service = service

    def set_memory(self, body: object) -> HttpResponse:
        if not isinstance(body, dict) or not isinstance(body.get("creator_id"), str) or not isinstance(body.get("requester_id"), str) or not isinstance(body.get("enabled"), bool):
            return _bad_request()
        try:
            settings = self.service.set_memory(body["creator_id"], body["enabled"], body["requester_id"])
        except PrivacyDenied:
            return _forbidden()
        return HttpResponse(200, {"creator_id": settings.creator_id, "ai_memory_enabled": settings.ai_memory_enabled})

    def content_action(self, body: object) -> HttpResponse:
        if not isinstance(body, dict):
            return _bad_request()
        required = {"creator_id", "content_id", "requester_id", "action"}
        if not required.issubset(body) or not all(isinstance(body.get(key), str) for key in required):
            return _bad_request()
        action = body["action"]
        try:
            if action == "select":
                state = self.service.select_content(body["creator_id"], body["content_id"], body["requester_id"])
            elif action == "hide":
                state = self.service.hide_content(body["creator_id"], body["content_id"], body["requester_id"])
            elif action == "exclude":
                state = self.service.exclude_content(body["creator_id"], body["content_id"], body["requester_id"])
            elif action == "reject":
                state = self.service.reject_content(body["creator_id"], body["content_id"], body["requester_id"])
            elif action == "delete":
                state = self.service.delete_content(body["creator_id"], body["content_id"], body["requester_id"])
            elif action == "correct":
                state = self.service.correct_content(body["creator_id"], body["content_id"], body["requester_id"], body.get("correction_note", ""))
            else:
                return _bad_request()
        except PrivacyDenied:
            return _forbidden()
        except ValueError:
            return _bad_request()
        return HttpResponse(200, _serialize_state(state))

    def get_status(self, creator_id: str) -> HttpResponse:
        return HttpResponse(200, self.service.status(creator_id))


def _serialize_state(state: Any) -> dict[str, object]:
    return {
        "creator_id": state.creator_id,
        "content_id": state.content_id,
        "included_in_memory": state.included_in_memory,
        "visibility": state.visibility,
        "review_status": state.review_status.value,
        "correction_note": state.correction_note,
        "deleted": state.deleted,
    }


def _bad_request() -> HttpResponse:
    return HttpResponse(400, {"error": {"code": "invalid_privacy_request"}})


def _forbidden() -> HttpResponse:
    return HttpResponse(403, {"error": {"code": "privacy_denied"}})
