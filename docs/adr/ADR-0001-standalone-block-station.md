# ADR 0001: Standalone block station and an immutable rolling guide

Status: accepted on the user's explicit 2026-11-11 direction.

## Context and authority

The supplied v0.2 canon prioritizes a reconstruction suite and a complete
summer-1995 Nickelodeon vertical slice. The user now explicitly prioritizes a
discrete player/scheduler usable with a well-divided library, with analysis and
upscaling optional. They also require a fixed rolling three-day guide.

## Decision

Build prepared-library ingest, deterministic composition and local browser
playback first. Ordered acts and full commercial/bumper files substitute for
automated segmentation. Keep the catalog contract independent of the companion.
Do not import analyzer modules or require a GPU for station operation.

Keep virtual spans canonical. Optional companion physical extraction creates
derivatives only. Keep market, provider, logical service, lineup and channel
positions separate. Treat assigned example channel numbers as synthetic.

Use a server-owned simulated historical clock anchored once at setup. Append
whole blocks to SQLite, expose only the next 72 hours, and reject updates/deletes
to published programming. No viewer time travel, schedule reroll or reset.

This changes the implementation order in Sections 12/13 and defers the first
realistic Nickelodeon corpus; it narrows exploratory date navigation described
in the handoff. It preserves Section 14's source, provenance, manifest and
continuous-clock semantics. No canon document is silently rewritten.

## Consequences

Simple libraries can drive channels immediately, with no inference pipeline.
Missing material is explicit. Once published, even an off-air slot stays fixed.
The initial composer is not a historical-airing oracle: generated broadcasts
are labeled composed/missing, not exact historical facts.

Clock settings/lineup are setup-only in this slice. Program eligibility uses
user-reviewed historical date windows and optional local dayparts. File paths,
hashes, offsets and titles are snapshotted into published segments. App-level
immutability cannot prevent a machine owner replacing files or databases.

## Technology

Python 3.11+ and SQLite allow a zero-package runtime and deterministic tests.
FFmpeg/ffprobe are external tools for media import/detection and optional cuts.
The browser delivery adapter requires compatible files; HLS/IPTV integration
and native TV packaging remain separate decisions. No upscaler is selected.
