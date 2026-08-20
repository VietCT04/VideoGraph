# Synthetic creator-memory demo dataset

This directory contains a small, controlled metadata fixture for VideoGraph issues
#22 and #23. It has 20 synthetic video/LIVE records across two synthetic creators,
machine-readable Moments with exact timestamps, canonical entity IDs, controlled
relations, and a query set grouped into `graph`, `vector`, `hybrid`, and `reasoning`
cases.

No copyrighted media, audio, frames, transcripts from real people, or external URLs are
included. `synthetic_media_ref` is intentionally `null` for every content record. The
fixture is designed to exercise metadata and retrieval logic; it is not an audiovisual
benchmark until locally generated or separately licensed media is added.

## Coverage

- repeated products across videos and a LIVE recording: Dior Rouge 999, Rare Beauty
  Inspire, and Rare Beauty Humble
- explicit recommendations, comparisons, dislikes, uses, and `SWITCHED_TO`
- a longitudinal Foundation A → Foundation B change
- vague language such as `this one`
- silent and low-speech records with OCR/visual text
- graph-only, vector-only, hybrid, and reasoning-oriented queries
- creator scoping through Alice Beauty and Bob Builds records

## Files

- `manifest.json` — creators, 20 content records, entities, and ground-truth Moments
- `queries.json` — expected evidence and graph intent for benchmark queries

## Usage and license

The original synthetic metadata in this directory is released under CC0-1.0. This
notice does not grant rights to any future media added outside this fixture. Keep any
locally added recordings uncommitted unless their source, permission, and redistribution
terms are documented separately. The benchmark must not claim media-level results from
these metadata-only records.
