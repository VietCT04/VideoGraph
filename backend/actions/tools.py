"""Typed, permissioned actions over canonical fused retrieval results."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from backend.search.fusion import FusedResult, FusionEvidence

from .catalog import FixtureProductCatalog, ProductCatalog, ProductRecord


class ActionPrivacyPolicy(Protocol):
    def can_surface_evidence(self, creator_id: str, content_ids: list[str]) -> bool:
        ...


@dataclass(frozen=True)
class ActionResult:
    tool_name: str
    status: str
    payload: dict[str, object] | None = None
    evidence: tuple[FusionEvidence, ...] = ()
    error_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "tool": self.tool_name,
            "status": self.status,
            "payload": self.payload,
            "error_code": self.error_code,
            "evidence": [
                {
                    "moment_id": item.moment_id,
                    "content_id": item.content_id,
                    "start_ms": item.start_ms,
                    "end_ms": item.end_ms,
                }
                for item in self.evidence
            ],
        }


class ActionToolService:
    """Execute actions only from a privacy-authorized canonical result."""

    def __init__(self, privacy_policy: ActionPrivacyPolicy, catalog: ProductCatalog | None = None) -> None:
        self.privacy_policy = privacy_policy
        self.catalog = catalog or FixtureProductCatalog()

    def execute(
        self,
        action: str,
        creator_id: str,
        result: FusedResult,
        constraints: Mapping[str, object] | None = None,
    ) -> ActionResult:
        options = constraints or {}
        if action == "jump_to_timestamp":
            return self.jump_to_timestamp(creator_id, result, options)
        if action == "find_product":
            return self.find_product(creator_id, result)
        if action == "find_similar_products":
            return self.find_similar_products(creator_id, result, options)
        return ActionResult("unknown", "failed", error_code="unsupported_action")

    def jump_to_timestamp(
        self,
        creator_id: str,
        result: FusedResult,
        constraints: Mapping[str, object] | None = None,
    ) -> ActionResult:
        authorized = self._authorize("jump_to_timestamp", creator_id, result)
        if authorized is not None:
            return authorized
        if not result.evidence:
            return ActionResult("jump_to_timestamp", "failed", error_code="evidence_missing")
        index = (constraints or {}).get("evidence_index", 0)
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(result.evidence):
            return ActionResult("jump_to_timestamp", "failed", error_code="invalid_evidence_index")
        evidence = result.evidence[index]
        return ActionResult(
            "jump_to_timestamp",
            "success",
            payload={
                "content_id": evidence.content_id,
                "moment_id": evidence.moment_id,
                "start_ms": evidence.start_ms,
                "end_ms": evidence.end_ms,
            },
            evidence=(evidence,),
        )

    def find_product(self, creator_id: str, result: FusedResult) -> ActionResult:
        authorized = self._authorize("find_product", creator_id, result)
        if authorized is not None:
            return authorized
        if result.entity_type != "Product" or result.entity_id is None:
            return ActionResult("find_product", "failed", evidence=result.evidence, error_code="product_entity_required")
        product = self.catalog.lookup(result.entity_id)
        if product is None:
            return ActionResult("find_product", "failed", evidence=result.evidence, error_code="product_not_found")
        return ActionResult("find_product", "success", payload=_product_payload(product), evidence=result.evidence)

    def find_similar_products(
        self,
        creator_id: str,
        result: FusedResult,
        constraints: Mapping[str, object] | None = None,
    ) -> ActionResult:
        authorized = self._authorize("find_similar_products", creator_id, result)
        if authorized is not None:
            return authorized
        if result.entity_type != "Product" or result.entity_id is None:
            return ActionResult("find_similar_products", "failed", evidence=result.evidence, error_code="product_entity_required")
        products = tuple(self.catalog.similar(result.entity_id, constraints or {}))
        return ActionResult(
            "find_similar_products",
            "success",
            payload={"products": [_product_payload(product) for product in products]},
            evidence=result.evidence,
        )

    def _authorize(self, tool_name: str, creator_id: str, result: FusedResult) -> ActionResult | None:
        content_ids = [evidence.content_id for evidence in result.evidence]
        if not content_ids or not self.privacy_policy.can_surface_evidence(creator_id, content_ids):
            return ActionResult(tool_name, "denied", error_code="privacy_denied")
        return None


def _product_payload(product: ProductRecord) -> dict[str, object]:
    return {
        "canonical_product_id": product.canonical_product_id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "price": product.price,
        "url": product.url,
        "tags": list(product.tags),
    }
