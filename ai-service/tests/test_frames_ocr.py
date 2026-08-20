"""Focused tests for representative frame and OCR evidence boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from pipeline.frames import (
    DeterministicFrameSampler,
    FrameCandidate,
    candidate_timestamps,
)
from pipeline.ocr import FixtureOCRProvider, OCRItem
from pipeline.segmentation import TemporalChunk


class FramesAndOCRTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunk = TemporalChunk("chunk_001", 5000, 11000, (5500, 8000, 10500), True)

    def test_sampler_keeps_anchors_and_deduplicates_near_identical_frames(self) -> None:
        candidates = (
            FrameCandidate("frame_start", 5500, (1, 1, 1, 1)),
            FrameCandidate("frame_duplicate", 6000, (1, 1, 1, 2)),
            FrameCandidate("frame_mid", 8000, (8, 8, 8, 8), important=True),
            FrameCandidate("frame_scene", 9000, (9, 9, 9, 9), important=True),
            FrameCandidate("frame_end", 10500, (5, 5, 5, 5)),
        )
        selected = DeterministicFrameSampler(max_frames=4, similarity_threshold=0.75).sample(
            self.chunk,
            candidates,
        )

        self.assertEqual(
            [frame.frame_id for frame in selected],
            ["frame_start", "frame_mid", "frame_scene", "frame_end"],
        )
        self.assertEqual([frame.timestamp_ms for frame in selected], [5500, 8000, 9000, 10500])

    def test_candidate_timestamps_include_scene_changes(self) -> None:
        self.assertEqual(
            candidate_timestamps(self.chunk, (5200, 8000, 12000)),
            (5200, 5500, 8000, 10500),
        )

    def test_ocr_preserves_timestamp_boxes_and_empty_results(self) -> None:
        provider = FixtureOCRProvider(
            {
                "frame_mid": (
                    OCRItem("ocr_1", "RARE BEAUTY", 0.96, (112, 220, 390, 305)),
                ),
            }
        )
        frames = provider.recognize_many(
            (
                self._frame("frame_mid", 8000),
                self._frame("frame_end", 10500),
            )
        )

        self.assertEqual(frames[0].timestamp_ms, 8000)
        self.assertEqual(frames[0].items[0].bbox, (112, 220, 390, 305))
        self.assertEqual(frames[1].timestamp_ms, 10500)
        self.assertEqual(frames[1].items, ())

    @staticmethod
    def _frame(frame_id: str, timestamp_ms: int):
        from pipeline.frames import RepresentativeFrame

        return RepresentativeFrame(frame_id, timestamp_ms)


if __name__ == "__main__":
    unittest.main()
