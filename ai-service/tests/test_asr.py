"""Focused tests for the normalized timestamped ASR boundary."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from pipeline.asr import ASRConfig, ASRSegment, AudioInput, FixtureASRProvider


class ASRTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = FixtureASRProvider(
            {
                "speech": (
                    ASRSegment("seg_1", 1200, 4800, "This is a fixture transcript.", 0.93),
                    ASRSegment("seg_2", 5000, 7200, "It has timestamps.", 0.88),
                ),
                "silent": (),
                "music": (
                    ASRSegment(
                        "seg_music",
                        0,
                        3000,
                        "unusable",
                        0.1,
                        no_speech_probability=0.95,
                    ),
                ),
            },
            config=ASRConfig(model_size="fixture-small", no_speech_threshold=0.5),
        )

    def test_timestamped_output_is_ordered_and_consumable_by_segmenter(self) -> None:
        result = self.provider.transcribe(
            AudioInput("speech.wav", 10000, fixture_key="speech")
        )

        self.assertFalse(result.no_speech)
        self.assertEqual([segment.id for segment in result.segments], ["seg_1", "seg_2"])
        self.assertEqual(
            [(span.start_ms, span.end_ms) for span in result.to_speech_spans()],
            [(1200, 4800), (5000, 7200)],
        )
        self.assertGreater(result.speech_ratio, 0)

    def test_silent_and_high_no_speech_inputs_do_not_fabricate_text(self) -> None:
        silent = self.provider.transcribe(
            AudioInput("silent.wav", 10000, fixture_key="silent")
        )
        music = self.provider.transcribe(
            AudioInput("music.wav", 10000, fixture_key="music")
        )

        self.assertTrue(silent.no_speech)
        self.assertEqual(silent.segments, ())
        self.assertTrue(music.no_speech)
        self.assertEqual(music.segments, ())
        self.assertEqual(music.speech_ratio, 0.0)

    def test_batching_and_language_metadata_are_stable(self) -> None:
        results = self.provider.transcribe_many(
            (
                AudioInput("speech.wav", 10000, language_hint="en", fixture_key="speech"),
                AudioInput("silent.wav", 10000, language_hint="ja", fixture_key="silent"),
            )
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].language, "en")
        self.assertEqual(results[1].language, "ja")
        self.assertEqual(results[0].model, "fixture-small")


if __name__ == "__main__":
    unittest.main()
