"""Focused tests for structured multimodal fusion."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from contracts.validation import ContractValidationError
from pipeline.frames import RepresentativeFrame
from pipeline.fusion import (
    FixtureFusionProvider,
    MultimodalBundle,
    build_extraction_payload,
    validate_fusion_output,
)
from pipeline.ocr import OCRFrameResult, OCRItem
from pipeline.segmentation import TemporalChunk


class FusionTests(unittest.TestCase):
    def test_fixture_outputs_cover_content_types_and_shared_contract(self) -> None:
        provider = FixtureFusionProvider()
        outputs = []
        for fixture_key, start_ms, end_ms in (
            ("beauty", 5000, 11000),
            ("tech", 1000, 8000),
            ("travel", 2000, 9000),
        ):
            bundle = self._bundle(fixture_key, start_ms, end_ms)
            output = provider.fuse(bundle)
            outputs.append(output)
            self.assertTrue(output.semantic_text)
            self.assertTrue(all(relation.evidence_refs for relation in output.relations))

        extraction = build_extraction_payload("content-1", "creator-1", outputs)
        self.assertEqual(len(extraction["moments"]), 3)

    def test_context_assembles_transcript_ocr_and_timestamped_frames(self) -> None:
        context = self._bundle("beauty", 5000, 11000).context()

        self.assertEqual(context["chunk"]["start_ms"], 5000)
        self.assertEqual(context["frames"][0]["timestamp_ms"], 8000)
        self.assertEqual(context["ocr"][0]["items"][0]["bbox"], [10, 20, 30, 40])

    def test_unknown_predicates_and_missing_relation_evidence_fail_closed(self) -> None:
        provider = FixtureFusionProvider()
        payload = provider.fuse(self._bundle("beauty", 5000, 11000)).as_dict()

        unknown = copy.deepcopy(payload)
        unknown["relations"][0]["predicate"] = "INVENTED"
        with self.assertRaises(ContractValidationError):
            validate_fusion_output(unknown)

        missing_evidence = copy.deepcopy(payload)
        missing_evidence["relations"][0]["evidence_refs"] = []
        with self.assertRaises(ContractValidationError):
            validate_fusion_output(missing_evidence)

    @staticmethod
    def _bundle(fixture_key: str, start_ms: int, end_ms: int) -> MultimodalBundle:
        return MultimodalBundle(
            chunk=TemporalChunk("chunk_001", start_ms, end_ms, (8000,), True),
            transcript="Fixture transcript",
            asr_segment_ids=("asr_1",),
            frames=(RepresentativeFrame("frame_8", 8000),),
            ocr_results=(
                OCRFrameResult(
                    "frame_8",
                    8000,
                    (OCRItem("ocr_1", "RARE BEAUTY", 0.96, (10, 20, 30, 40)),),
                    "fixture",
                ),
            ),
            fixture_key=fixture_key,
        )


if __name__ == "__main__":
    unittest.main()
