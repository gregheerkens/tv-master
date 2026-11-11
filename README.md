# TV MASTER

A local period-TV station built from your own prepared library. Programs, ads,
promos and bumpers become continuous, reproducible broadcasts. The player and
scheduler have **no dependency on the companion analyzer or an upscaler**.

This is a working first slice, not a finished historical-reconstruction product.
The current composer supports date windows, service matching, optional local
dayparts, ordered acts, whole commercial spots and explicit missing-material
slates. The original design and handoff are retained in `docs/`.

## Run a synthetic demonstration

Requirements: Python 3.11+; FFmpeg/ffprobe on PATH for importing actual media,
generating demonstration clips, or running the optional analyzer. The guide,
database and HTTP server use Python's standard library. No GPU or AI is required.

```sh
python -m retro_tv demo
python -m retro_tv serve
```

Open **http://127.0.0.1:8787**. The demo generates small colored test videos,
initializes a fictional two-channel lineup, and plays them at the correct point
on a simulated July 1995 clock. It contains no TV footage or verified historical
lineup claims. Short demo shows intentionally leave conspicuous filler slates.

Up/down selects a channel; Enter/OK tunes it. F toggles fullscreen, G returns to
the guide. A browser may require the resume button before allowing sound.

## Use a prepared library

Use a **new station database** for initial setup, rather than the demo database:

```sh
python -m retro_tv --db data/my-station.sqlite init examples/station.json
python -m retro_tv --db data/my-station.sqlite import-library my-library.json
python -m retro_tv --db data/my-station.sqlite serve
```

Edit your station configuration *before initialization*: historical start with
explicit timezone offset, market, provider, lineup validity and your own channel
numbers/service names. Example channels 1 and 2 are personal assignments, not
claims about Rochester Time Warner Cable. Import all ready-to-use material before
first serving or running `guide`, as either publishes the initial horizon.

`examples/library.json` shows two manually separated acts, a commercial and a
bumper. Replace its paths, identities, periods and provenance with your media.
Whole files need no in/out points; spans into longer captures can use integer
`in_ms`/`out_ms`. Import reads and hashes source files but never modifies them.
Source and catalog IDs are append-only: duplicate IDs reject the entire import.

Use browser-compatible **H.264 video / AAC audio in MP4**, preferably with
faststart. Arbitrary containers/codecs do not become browser-compatible merely
because they are cataloged. An IPTV/transcoding adapter is a later integration.

## The fixed three-day guide

- The server owns the clock. Historical time advances one second per real second,
  even while nobody watches or the server is stopped.
- The server appends programming to maintain a visible **72-hour horizon**. It
  freezes the final whole block, even if that block ends beyond the horizon;
  the public guide clips it at the horizon and never exposes a fourth day.
- Published broadcasts and segments cannot be updated or deleted through the app.
  SQLite triggers also reject ordinary SQL updates/deletes. Station anchors,
  seed and timezone cannot be edited after initialization.
- There are no reroll, reset, seek-to-date, future-tune or schedule-edit endpoints.
  Importing media affects only blocks that have not yet been composed.
- A backward host-clock adjustment cannot rewind the station. A large forward
  jump advances it; this is a local system-clock model, not an external trusted
  time service.
- Tuning uses the current source offset; changing channels never restarts a show.
  Playback resynchronizes periodically and at each segment boundary.
- Original files must remain available and unchanged at their registered paths.
  Missing content produces an error/slate; the schedule is not silently replaced.

These are application guarantees, not DRM: a computer owner can delete or restore
the database, change files, modify the program or create another station. Back up
the database and archival media. The original historical design's free time-machine
exploration is deliberately narrowed for this station's live viewing mode; see ADR 0001.

## Optional companion

```sh
python -m retro_tv.companion analyze /media/tape.mp4 review.json
# Review boundaries and supply identities, dates, service IDs and evidence.
python -m retro_tv.companion export review.json approved-library.json
python -m retro_tv --db data/my-station.sqlite import-library approved-library.json
```

It can also run independently as a serial analysis-job HTTP service:

```sh
python -m retro_tv.companion serve --media-root /media --port 8790
curl -X POST http://127.0.0.1:8790/jobs \
  -H 'Content-Type: application/json' -d '{"path":"tape.mp4"}'
curl http://127.0.0.1:8790/jobs/JOB_ID
```

The baseline detects black/silence transitions and outputs complete virtual spans.
Physical cuts are optional: `python -m retro_tv.companion extract review.json clips/`
creates H.264/AAC derivatives without overwriting originals.

**Automatic recognition of arbitrary shows, ads, bumpers, air dates or rerun
windows is not implemented.** Those fields start unknown and require review;
transition confidence is never represented as identity confidence. This distinction
prevents a detector from inventing historical facts. The companion contract and
next recognition milestone are documented in `docs/COMPANION.md`.

## Verification

```sh
python -m unittest discover -s tests -v
```

Tests cover source spans, transaction rollback, standalone composition, date and
daypart eligibility, deterministic scheduling, immutability, new imports,
restart/clock rollback and analyzer review gating. No copyrighted files needed.
`tests/browser-smoke.cjs` is an optional Playwright smoke test against a running
demo; it uses externally installed Playwright and Chromium.

## Current boundaries

The first delivery adapter is a browser player, not an HLS/IPTV server or TV APK.
The UI is intentionally small. There is no catalog editing GUI yet. The composer
uses simple deterministic rotation with immediate-repeat avoidance, not a full
campaign-frequency optimizer or historical listings importer. Breaks must be
provided manually as ordered program parts. It does not fabricate missing episode
identity, guaranteed rerun brackets or local station history.

The next independently testable milestone is a reference-backed identification
adapter for the companion: known labeled examples, calibrated match confidence,
reviewable metadata suggestions, and round-trip import into the existing catalog.
Historical schedule normalization and coverage reports remain in the broader
roadmap. See `docs/STATUS.md` for validation and implementation inventory.

## Catalog records and personal decisions

The additive v2 catalog separates content identities from recording spans,
supports custom/themed/historical channels, and stores dated station/affiliation
facts independently of cable positions. Seasonal eligibility windows, quality
alerts, content bans, recording exclusions and scheduled/aired/viewed statistics
are documented in [RECORDKEEPING](docs/RECORDKEEPING.md), with an optional
`examples/records.json` import. Existing databases migrate without resetting the
clock or changing published slots. Historical lookup uses imported evidence;
automatic historical-data retrieval is not yet implemented.
