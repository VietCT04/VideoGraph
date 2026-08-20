"""Targeted contract tests runnable with only the Python standard library."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from .validation import ContractValidationError, load_schema, validate_extraction, validate_retrieval_plan


class ContractValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.examples_dir = Path(__file__).parent / "examples"

    def test_schemas_are_versioned_json_objects(self) -> None:
        for name in ("multimodal-extraction.schema.json", "retrieval-plan.schema.json"):
            with self.subTest(schema=name):
                schema = load_schema(name)
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["type"], "object")

    def test_examples_validate(self) -> None:
        for path in sorted(self.examples_dir.glob("*.json")):
            with self.subTest(example=path.name):
                with path.open(encoding="utf-8") as example_file:
                    validate_extraction(json.load(example_file))

    def test_unknown_graph_values_are_rejected(self) -> None:
        with (self.examples_dir / "beauty.json").open(encoding="utf-8") as example_file:
            extraction = json.load(example_file)
        extraction["moments"][0]["relations"][0]["predicate"] = "INVENTED"
        with self.assertRaises(ContractValidationError):
            validate_extraction(extraction)

        plan = {
            "schema_version": "1.0",
            "creator_id": "creator-42",
            "intent": "find_recommendation",
            "graph": {"relations": ["INVENTED"], "entity_types": ["Product"], "filters": {}},
            "semantic_query": "red lipstick",
            "result_type": "Entity",
            "top_k": 10,
        }
        with self.assertRaises(ContractValidationError):
            validate_retrieval_plan(plan)

    def test_unknown_properties_and_raw_cypher_are_rejected(self) -> None:
        with (self.examples_dir / "beauty.json").open(encoding="utf-8") as example_file:
            extraction = json.load(example_file)
        extraction["moments"][0]["raw_cypher"] = "MATCH (n) RETURN n"
        with self.assertRaises(ContractValidationError):
            validate_extraction(extraction)

        plan = {
            "schema_version": "1.0",
            "creator_id": "creator-42",
            "intent": "find_recommendation",
            "graph": {"relations": [], "entity_types": []},
            "semantic_query": "red lipstick",
            "result_type": "Entity",
            "top_k": 10,
            "cypher": "MATCH (n) RETURN n",
        }
        with self.assertRaises(ContractValidationError):
            validate_retrieval_plan(plan)

    def test_embedding_dimension_is_checked(self) -> None:
        with (self.examples_dir / "beauty.json").open(encoding="utf-8") as example_file:
            extraction = copy.deepcopy(json.load(example_file))
        extraction["moments"][0]["embedding"] = {"model": "fixture", "dimension": 2, "vector": [0.1]}
        with self.assertRaises(ContractValidationError):
            validate_extraction(extraction)


if __name__ == "__main__":
    unittest.main()
