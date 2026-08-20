"""AI Service client protocol and a deterministic local implementation."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AIJobStatus:
    """Small normalized status returned by an AI Service adapter."""

    state: str
    progress: int
    error_code: str | None = None


class AIServiceClient(Protocol):
    """Asynchronous AI Service boundary owned by the main backend."""

    def submit_content(self, creator_id: str, content_id: str, pipeline_version: str) -> str:
        ...

    def get_status(self, ai_job_id: str) -> AIJobStatus:
        ...

    def get_result(self, ai_job_id: str) -> Mapping[str, Any]:
        ...


class FixtureAIServiceClient:
    """Immediate fixture adapter that follows the async client contract."""

    def __init__(self, fixtures: Mapping[str, Mapping[str, Any]]) -> None:
        self.fixtures = dict(fixtures)
        self._jobs: dict[str, str] = {}

    def submit_content(self, creator_id: str, content_id: str, pipeline_version: str) -> str:
        del creator_id
        if content_id not in self.fixtures:
            raise KeyError(content_id)
        digest = hashlib.sha256(f"{content_id}|{pipeline_version}".encode()).hexdigest()[:16]
        ai_job_id = f"ai_{_slug(content_id)}_{digest}"
        self._jobs[ai_job_id] = content_id
        return ai_job_id

    def get_status(self, ai_job_id: str) -> AIJobStatus:
        if ai_job_id not in self._jobs:
            return AIJobStatus("failed", 0, "ai_job_not_found")
        return AIJobStatus("completed", 100)

    def get_result(self, ai_job_id: str) -> Mapping[str, Any]:
        content_id = self._jobs[ai_job_id]
        return copy.deepcopy(self.fixtures[content_id])


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "content"
