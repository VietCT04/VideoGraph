"""Focused tests for deterministic temporal segmentation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from pipeline.metadata import FixtureMetadataInspector, VideoMetadata
from pipeline.segmentation import SceneBoundary, SpeechSpan, TemporalSegmenter


class TemporalSegmentationTests(unittest.TestCase):
    def test_fixture_metadata_is_dependency_free(self) -> None:
        inspector = FixtureMetadataInspector(
            {"silent.mp4": VideoMetadata(duration_ms=60000, has_audio=False)}
        )
        metadata = inspector.inspect("silent.mp4")
        self.assertEqual(metadata.duration_ms, 60000)
        self.assertFalse(metadata.has_audio)

    def test_silent_minute_uses_deterministic_visual_fallback(self) -> None:
        segmenter = TemporalSegmenter()
        first = segmenter.segment(60000)
        second = segmenter.segment(60000)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        self.assertEqual(first[0].start_ms, 0)
        self.assertEqual(first[-1].end_ms, 60000)
        self.assertTrue(all(not chunk.has_speech for chunk in first))
        self.assertTrue(all(0 < chunk.duration_ms <= 6000 for chunk in first))
        self.assertTrue(all(len(chunk.frame_timestamps_ms) == 3 for chunk in first))

    def test_tiny_speech_fragments_are_merged(self) -> None:
        spans = (
            SpeechSpan(0, 1000, "short one"),
            SpeechSpan(1000, 1800, "short two"),
            SpeechSpan(1800, 5000, "main thought"),
        )
        chunks = TemporalSegmenter().segment(5000, speech_spans=spans)

        self.assertEqual(len(chunks), 1)
        self.assertEqual((chunks[0].start_ms, chunks[0].end_ms), (0, 5000))
        self.assertTrue(chunks[0].has_speech)

    def test_strong_scene_boundary_is_preserved(self) -> None:
        chunks = TemporalSegmenter().segment(
            12000,
            scene_boundaries=(SceneBoundary(2000, strong=True), SceneBoundary(7000, strong=True)),
        )

        self.assertEqual(
            [(chunk.start_ms, chunk.end_ms) for chunk in chunks],
            [(0, 2000), (2000, 7000), (7000, 12000)],
        )

    def test_long_speech_video_is_bounded_and_ordered(self) -> None:
        spans = tuple(SpeechSpan(start, start + 4500) for start in range(0, 60000, 5000))
        chunks = TemporalSegmenter().segment(60000, speech_spans=spans)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].start_ms, 0)
        self.assertEqual(chunks[-1].end_ms, 60000)
        self.assertTrue(all(chunk.start_ms < chunk.end_ms <= 60000 for chunk in chunks))
        self.assertTrue(
            all(
                left.end_ms == right.start_ms
                for left, right in zip(chunks, chunks[1:])
            )
        )
        self.assertTrue(all(chunk.duration_ms <= 15000 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
