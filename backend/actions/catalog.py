"""Typed product catalog boundary with deterministic local fixtures."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from backend.graph.ingestion import canonical_entity_id


@dataclass(frozen=True)
class ProductRecord:
    canonical_product_id: str
    name: str
    brand: str
    category: str
    price: str | None = None
    url: str | None = None
    tags: tuple[str, ...] = ()


class ProductCatalog:
    def lookup(self, canonical_product_id: str) -> ProductRecord | None:
        raise NotImplementedError

    def similar(self, canonical_product_id: str, constraints: Mapping[str, object]) -> Iterable[ProductRecord]:
        raise NotImplementedError


class FixtureProductCatalog(ProductCatalog):
    """Small catalog keyed only by backend-owned canonical Product IDs."""

    def __init__(self, products: Iterable[ProductRecord] | None = None) -> None:
        default_products = _default_products() if products is None else products
        self.products = {product.canonical_product_id: product for product in default_products}

    def lookup(self, canonical_product_id: str) -> ProductRecord | None:
        return self.products.get(canonical_product_id)

    def similar(self, canonical_product_id: str, constraints: Mapping[str, object]) -> Iterable[ProductRecord]:
        source = self.lookup(canonical_product_id)
        if source is None:
            return ()
        category = constraints.get("category", source.category)
        brand = constraints.get("brand")
        return tuple(
            product
            for product in self.products.values()
            if product.canonical_product_id != canonical_product_id
            and product.category == category
            and (brand is None or product.brand == brand)
        )


def _default_products() -> tuple[ProductRecord, ...]:
    source_id = canonical_entity_id("creator-42", "Product", "rare beauty humble lipstick")
    similar_id = canonical_entity_id("creator-42", "Product", "rare beauty inspire lipstick")
    return (
        ProductRecord(
            canonical_product_id=source_id,
            name="Rare Beauty Humble lipstick",
            brand="Rare Beauty",
            category="lipstick",
            price="$20",
            url="https://example.test/products/rare-beauty-humble",
            tags=("everyday", "neutral"),
        ),
        ProductRecord(
            canonical_product_id=similar_id,
            name="Rare Beauty Inspire lipstick",
            brand="Rare Beauty",
            category="lipstick",
            price="$20",
            url="https://example.test/products/rare-beauty-inspire",
            tags=("bold", "long-wear"),
        ),
    )
