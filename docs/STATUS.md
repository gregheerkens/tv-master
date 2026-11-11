# Implementation status

## Delivered in the initial repository

- `retro_tv/catalog.py`, `schema.sql`: transactional, hash/provenance-preserving
  source and virtual-span imports; reviewed metadata; logical services and dated
  user-defined lineups; append-only published broadcast/segment storage.
- `retro_tv/scheduler.py`: deterministic act/spot composition, date/service and
  local program-daypart filtering, explicit gap slates, persistent simulation
  anchor, no reset/reroll, serialized horizon extension, current-position tuning.
- `retro_tv/server.py`, `static/`: local guide/browser playback, byte-range media
  delivery, remote keyboard focus, fullscreen and periodic clock resynchronization.
- `retro_tv/companion.py`: separate optional FFmpeg detector and serial job
  service, persistent review documents, reviewed library export and optional cuts.
- `retro_tv/demo.py`, `examples/`: self-generated test-pattern demo and editable
  station/library manifests. No actual TV programs or historical lineup claims.
- `docs/adr/ADR-0001-standalone-block-station.md`: records the user's scope change
  and initial Python/SQLite/browser delivery decisions. Original handoff preserved.

## Validation performed

- 31 Python tests passed, including a real FFmpeg detection → review → export →
  catalog import → physical extraction round trip. The archival fixture remained
  byte-for-byte unchanged.
- Concurrent writers produced one contiguous, nonoverlapping schedule.
- Published broadcasts, segments, seed and simulation anchors rejected mutation;
  restart and backward clock movement did not rewind the station.
- A new library did not rewrite published programs or previously published gaps.
- Chromium/Playwright loaded two channels, played real generated video, and moved
  remote focus correctly after guide refresh; no browser script errors observed.
- Live HTTP checks passed for 72-hour bounds, current tuning, valid partial media
  responses and invalid-range rejection.
- Companion HTTP checks passed for queued analysis, persisted pending review and
  rejecting source paths outside the configured media root.
- Python compile checks and JavaScript syntax checks passed.

## Known gaps and next steps

Schema v3 adds source-ingestion context, ripped-folder/recorded-file intake,
mandatory recording date/seasonal/holiday fields for new recorded media, and
estimated ±2-year continuity reuse with movable-holiday and evidence overrides.
Existing sources remain `legacy_unknown` without changing published programming.
Tests include leap dates, seasonal context rejection, Thanksgiving/Easter and
New Year boundaries, annual campaigns, scheduler enforcement and ingest→companion
source reuse. These are CLI/JSON workflows; an ingest form remains future work.

The v2 recordkeeping update adds normalized content identities, dated station and
primary-network lookup, themed-channel tag matching, seasonal eligibility windows,
recording quality/alerts, content versus recording exclusions, and separate
scheduled/aired/viewed statistics. Existing SQLite stations migrate additively.
See `RECORDKEEPING.md`, `DATA_SOURCES.md` and ADR 0002. Metadata-only operations
require no media tools or AI. TV MASTER is the provisional display name.

The new tests cover legacy migration, period/network lookup, seasonal windows,
theme matching, inherited series bans, per-copy exclusions, unchanged published
slots, and idempotent explicit viewing records.

No automatic semantic identification/date research, catalog review GUI, full
historical-airing importer, acquisition coverage reports, campaign optimizer,
HLS/IPTV output, native TV APK or enhancement worker is implemented. Browser
playback requires supported codecs and may have a brief transition between files.
The fixed guide is an application/storage rule, not tamper-proof enforcement
against the owner of the server.

Next narrow milestone: reference-backed identification suggestions for reviewed
companion candidates, with explicit unknowns and date provenance. Keep the
prepared-library path and immutable-guide tests passing throughout.

The hosted repository is `gregheerkens/tv-master`. GitHub app access was
reconnected and the project was uploaded through that connection. The cloud
terminal's separate `GH_TOKEN` was still invalid at the time of upload; connector
access does not depend on that terminal credential.
