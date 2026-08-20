"""Focused tests for the simulated incremental LIVE memory store."""

from __future__ import annotations

import unittest

from .live_memory import LiveMemoryStore, LiveMomentState


class LiveMemoryStoreTests(unittest.TestCase):
    def test_append_creates_temporary_moment_with_both_timestamp_domains(self) -> None:
        store = LiveMemoryStore()
        moment = store.append_or_update(
            content_id="live-001",
            chunk_id="chunk-001",
            stream_start_ms=0,
            stream_end_ms=5000,
            wall_clock_start="2026-08-20T10:00:00Z",
            wall_clock_end="2026-08-20T10:00:05Z",
            extraction={"semantic_text": "opening"},
        )

        self.assertEqual(moment.temporary_id, "live:live-001:chunk-001")
        self.assertEqual(moment.state, LiveMomentState.TEMPORARY)
        self.assertEqual(moment.stream_end_ms, 5000)
        self.assertEqual(moment.wall_clock_end, "2026-08-20T10:00:05Z")

    def test_repeated_chunk_updates_without_creating_a_duplicate(self) -> None:
        store = LiveMemoryStore()
        store.append_or_update(
            content_id="live-001",
            chunk_id="chunk-001",
            stream_start_ms=0,
            stream_end_ms=5000,
            wall_clock_start="2026-08-20T10:00:00Z",
            wall_clock_end="2026-08-20T10:00:05Z",
            extraction={"semantic_text": "partial"},
        )
        updated = store.append_or_update(
            content_id="live-001",
            chunk_id="chunk-001",
            stream_start_ms=0,
            stream_end_ms=7000,
            wall_clock_start="2026-08-20T10:00:00Z",
            wall_clock_end="2026-08-20T10:00:07Z",
            extraction={"semantic_text": "complete"},
        )

        self.assertEqual(len(store.list_for_content("live-001")), 1)
        self.assertEqual(updated.stream_end_ms, 7000)
        self.assertEqual(updated.extraction["semantic_text"], "complete")

    def test_moments_are_ordered_by_stream_time(self) -> None:
        store = LiveMemoryStore()
        for chunk_id, start in (("late", 5000), ("early", 0)):
            store.append_or_update(
                content_id="live-001",
                chunk_id=chunk_id,
                stream_start_ms=start,
                stream_end_ms=start + 1000,
                wall_clock_start=f"2026-08-20T10:00:0{start // 1000}Z",
                wall_clock_end=f"2026-08-20T10:00:0{start // 1000}Z",
                extraction={},
            )

        self.assertEqual(
            [moment.stream_start_ms for moment in store.list_for_content("live-001")],
            [0, 5000],
        )

    def test_finalize_assigns_persistent_ids_and_removes_temporary_records(self) -> None:
        store = LiveMemoryStore()
        store.append_or_update(
            content_id="live-001",
            chunk_id="chunk-001",
            stream_start_ms=0,
            stream_end_ms=5000,
            wall_clock_start="2026-08-20T10:00:00Z",
            wall_clock_end="2026-08-20T10:00:05Z",
            extraction={"semantic_text": "opening"},
        )

        finalized = store.finalize("live-001", "content-001")

        self.assertEqual(len(finalized), 1)
        self.assertEqual(finalized[0].state, LiveMomentState.FINALIZED)
        self.assertEqual(finalized[0].persistent_moment_id, "moment:content-001:0:5000")
        self.assertEqual(store.list_for_content("live-001"), [])
        self.assertEqual(store.list_for_content("content-001"), finalized)

    def test_invalid_intervals_fail_closed(self) -> None:
        store = LiveMemoryStore()
        with self.assertRaises(ValueError):
            store.append_or_update(
                content_id="live-001",
                chunk_id="chunk-001",
                stream_start_ms=5000,
                stream_end_ms=5000,
                wall_clock_start="2026-08-20T10:00:00Z",
                wall_clock_end="2026-08-20T10:00:00Z",
                extraction={},
            )


if __name__ == "__main__":
    unittest.main()
