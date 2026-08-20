"""Focused tests for deterministic semantic embeddings."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from pipeline.embeddings import HashingEmbeddingProvider, cosine_similarity, embed_extraction


class EmbeddingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = HashingEmbeddingProvider(dimension=32, batch_size=2)

    def test_related_fused_text_is_closer_than_unrelated_text(self) -> None:
        batch = self.provider.embed(
            (
                "Creator recommends a red lipstick for darker skin.",
                "She suggests this red lipstick for deeper skin tones.",
                "Creator explains how to install Docker.",
            )
        )

        related = cosine_similarity(batch.vectors[0], batch.vectors[1])
        unrelated = cosine_similarity(batch.vectors[0], batch.vectors[2])
        self.assertGreater(related, unrelated)

    def test_hashing_is_deterministic_and_metadata_is_explicit(self) -> None:
        texts = ("Creator uses a product.", "Creator visits Kyoto.")
        first = self.provider.embed(texts)
        second = self.provider.embed(texts)

        self.assertEqual(first, second)
        self.assertEqual(first.metadata.model, "hashing-fixture")
        self.assertEqual(first.metadata.version, "1")
        self.assertEqual(first.metadata.dimension, 32)
        self.assertTrue(all(len(vector) == 32 for vector in first.vectors))

    def test_extraction_integration_embeds_semantic_text_and_revalidates(self) -> None:
        example_path = Path(__file__).parents[2] / "contracts/examples/beauty.json"
        with example_path.open(encoding="utf-8") as example_file:
            extraction = json.load(example_file)
        original = copy.deepcopy(extraction)

        embedded = embed_extraction(extraction, self.provider)

        self.assertIsNone(original["moments"][0].get("embedding"))
        embedding = embedded["moments"][0]["embedding"]
        self.assertEqual(embedding["model"], "hashing-fixture")
        self.assertEqual(embedding["dimension"], 32)
        self.assertEqual(len(embedding["vector"]), 32)
        self.assertEqual(embedded["pipeline"]["embedding_model"], "hashing-fixture")


if __name__ == "__main__":
    unittest.main()
