"""Server-side creator opt-in, review, visibility, and deletion controls."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from backend.graph.model import VISIBILITIES
from backend.graph.repository import GraphRepository
from backend.search.vector_repository import VectorRepository


class ReviewStatus(str, Enum):
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"


@dataclass
class CreatorMemorySettings:
    creator_id: str
    ai_memory_enabled: bool = False


@dataclass
class ContentMemoryState:
    creator_id: str
    content_id: str
    included_in_memory: bool = True
    visibility: str = "public"
    review_status: ReviewStatus = ReviewStatus.ACCEPTED
    correction_note: str | None = None
    deleted: bool = False


class PrivacyDenied(PermissionError):
    """Raised when creator memory or content is not available to a caller."""


class CreatorPermission(Protocol):
    def can_manage(self, requester_id: str, creator_id: str) -> bool:
        ...


class SameCreatorPermission:
    """Fixture authorization adapter; production auth can replace this boundary."""

    def can_manage(self, requester_id: str, creator_id: str) -> bool:
        return requester_id == creator_id


class InMemoryPrivacyRepository:
    """Fixture-backed application-state store for creator/content policy."""

    def __init__(self) -> None:
        self.creators: dict[str, CreatorMemorySettings] = {}
        self.contents: dict[str, ContentMemoryState] = {}

    def creator(self, creator_id: str) -> CreatorMemorySettings | None:
        return self.creators.get(creator_id)

    def content(self, content_id: str) -> ContentMemoryState | None:
        return self.contents.get(content_id)

    def save_creator(self, settings: CreatorMemorySettings) -> CreatorMemorySettings:
        self.creators[settings.creator_id] = settings
        return settings

    def save_content(self, state: ContentMemoryState) -> ContentMemoryState:
        self.contents[state.content_id] = state
        return state

    def for_creator(self, creator_id: str) -> list[ContentMemoryState]:
        return sorted(
            (state for state in self.contents.values() if state.creator_id == creator_id),
            key=lambda state: state.content_id,
        )


class PrivacyControlService:
    """Keep application policy and graph/vector visibility synchronized."""

    def __init__(
        self,
        repository: InMemoryPrivacyRepository,
        graph_repository: GraphRepository,
        vector_repository: VectorRepository,
        permission: CreatorPermission | None = None,
    ) -> None:
        self.repository = repository
        self.graph_repository = graph_repository
        self.vector_repository = vector_repository
        self.permission = permission or SameCreatorPermission()

    def set_memory(self, creator_id: str, enabled: bool, requester_id: str) -> CreatorMemorySettings:
        self._authorize_manager(requester_id, creator_id)
        settings = self.repository.creator(creator_id) or CreatorMemorySettings(creator_id)
        settings.ai_memory_enabled = enabled
        self.repository.save_creator(settings)
        if not enabled:
            for state in self.repository.for_creator(creator_id):
                self._suppress(state, visibility="excluded", included=False)
        return settings

    def select_content(self, creator_id: str, content_id: str, requester_id: str) -> ContentMemoryState:
        self._authorize_manager(requester_id, creator_id)
        self._require_enabled(creator_id)
        current = self.repository.content(content_id)
        if current is not None and current.creator_id != creator_id:
            raise PrivacyDenied("content does not belong to creator")
        if current is not None and (current.deleted or current.review_status == ReviewStatus.REJECTED):
            raise PrivacyDenied("content cannot be restored automatically")
        state = current or ContentMemoryState(creator_id=creator_id, content_id=content_id)
        state.included_in_memory = True
        state.visibility = "public"
        state.deleted = False
        self.repository.save_content(state)
        self._sync_visibility(content_id, "public")
        return state

    def hide_content(self, creator_id: str, content_id: str, requester_id: str) -> ContentMemoryState:
        return self._set_content_visibility(creator_id, content_id, requester_id, "hidden", True)

    def exclude_content(self, creator_id: str, content_id: str, requester_id: str) -> ContentMemoryState:
        return self._set_content_visibility(creator_id, content_id, requester_id, "excluded", False)

    def correct_content(
        self,
        creator_id: str,
        content_id: str,
        requester_id: str,
        correction_note: str,
    ) -> ContentMemoryState:
        self._authorize_manager(requester_id, creator_id)
        if not isinstance(correction_note, str) or not correction_note.strip():
            raise ValueError("correction_note must be a non-empty string")
        state = self._content_for_creator(creator_id, content_id)
        if state.deleted:
            raise PrivacyDenied("deleted content cannot be corrected")
        state.review_status = ReviewStatus.CORRECTED
        state.correction_note = correction_note.strip()
        return self.repository.save_content(state)

    def reject_content(self, creator_id: str, content_id: str, requester_id: str) -> ContentMemoryState:
        self._authorize_manager(requester_id, creator_id)
        state = self._content_for_creator(creator_id, content_id)
        state.review_status = ReviewStatus.REJECTED
        self.repository.save_content(state)
        return self._suppress(state, visibility="excluded", included=False)

    def delete_content(self, creator_id: str, content_id: str, requester_id: str) -> ContentMemoryState:
        self._authorize_manager(requester_id, creator_id)
        state = self._content_for_creator(creator_id, content_id)
        self.graph_repository.delete_content(content_id)
        self.vector_repository.delete_by_content(content_id)
        state.deleted = True
        state.included_in_memory = False
        state.visibility = "excluded"
        return self.repository.save_content(state)

    def authorize_creator(self, creator_id: str) -> None:
        self._require_enabled(creator_id)
        visible = any(self.content_allowed(creator_id, state.content_id) for state in self.repository.for_creator(creator_id))
        if not visible:
            raise PrivacyDenied("creator has no searchable content")

    def content_allowed(self, creator_id: str, content_id: str) -> bool:
        settings = self.repository.creator(creator_id)
        state = self.repository.content(content_id)
        return bool(
            settings is not None
            and settings.ai_memory_enabled
            and state is not None
            and state.creator_id == creator_id
            and state.included_in_memory
            and state.visibility == "public"
            and state.review_status != ReviewStatus.REJECTED
            and not state.deleted
        )

    def can_surface_evidence(self, creator_id: str, content_ids: Iterable[str]) -> bool:
        return all(self.content_allowed(creator_id, content_id) for content_id in content_ids)

    def status(self, creator_id: str) -> dict[str, object]:
        settings = self.repository.creator(creator_id) or CreatorMemorySettings(creator_id)
        return {
            "creator_id": creator_id,
            "ai_memory_enabled": settings.ai_memory_enabled,
            "content": [
                {
                    "content_id": state.content_id,
                    "included_in_memory": state.included_in_memory,
                    "visibility": state.visibility,
                    "review_status": state.review_status.value,
                    "correction_note": state.correction_note,
                    "deleted": state.deleted,
                }
                for state in self.repository.for_creator(creator_id)
            ],
        }

    def _set_content_visibility(
        self,
        creator_id: str,
        content_id: str,
        requester_id: str,
        visibility: str,
        included: bool,
    ) -> ContentMemoryState:
        self._authorize_manager(requester_id, creator_id)
        state = self._content_for_creator(creator_id, content_id)
        if state.deleted:
            raise PrivacyDenied("deleted content cannot change visibility")
        return self._suppress(state, visibility=visibility, included=included)

    def _suppress(self, state: ContentMemoryState, visibility: str, included: bool) -> ContentMemoryState:
        if visibility not in VISIBILITIES:
            raise ValueError(f"unknown visibility {visibility!r}")
        state.visibility = visibility
        state.included_in_memory = included
        self.repository.save_content(state)
        self._sync_visibility(state.content_id, visibility)
        return state

    def _sync_visibility(self, content_id: str, visibility: str) -> None:
        self.graph_repository.set_visibility(content_id, visibility)
        self.vector_repository.set_visibility(content_id, visibility)

    def _content_for_creator(self, creator_id: str, content_id: str) -> ContentMemoryState:
        state = self.repository.content(content_id)
        if state is None or state.creator_id != creator_id:
            raise PrivacyDenied("content does not belong to creator")
        return state

    def _authorize_manager(self, requester_id: str, creator_id: str) -> None:
        if not self.permission.can_manage(requester_id, creator_id):
            raise PrivacyDenied("creator management is not authorized")

    def _require_enabled(self, creator_id: str) -> None:
        settings = self.repository.creator(creator_id)
        if settings is None or not settings.ai_memory_enabled:
            raise PrivacyDenied("creator memory is not enabled")
