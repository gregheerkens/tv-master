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

- 59 Python tests passed, including a real FFmpeg detection → review → export →
  catalog import → physical extraction round trip. The archival fixture remained
  byte-for-byte unchanged.
- Concurrent writers produced one contiguous, nonoverlapping schedule.
- Published broadcasts, segments, seed and simulation anchors rejected mutation;
  restart and backward clock movement did not rewind the station.
- A new library did not rewrite published programs or previously published gaps.
- Chromium/Playwright verified the classic full-PIP and bottom-third guide modes,
  continuous generated-video playback, remote-style D-pad/future-info navigation,
  numeric tuning, three-day manager analysis and narrow-screen layouts. No browser
  script errors were observed. This is not physical TV-device verification.
- Live HTTP checks passed for 72-hour bounds, current tuning, valid partial media
  responses and invalid-range rejection.
- Companion HTTP checks passed for queued analysis, persisted pending review and
  rejecting source paths outside the configured media root.
- Python compile checks and JavaScript syntax checks passed.

## Known gaps and next steps

**Time Machine now works**: saved WHAT choices, specific or representative period
destinations, preflight, scoped guide/player, persistent clocks and resume. Filtered
surfing shares the station clock; default surfing uses the original station.
Different entry minutes do not reroll that day's schedule. Catalog additions and
repairs can propagate without rewriting published timelines or copying videos.
See `USING_TIME_MACHINE.md`, `PRODUCT_MODES.md` and ADR 0006.

Manager standards now distinguish operation, historical recreation and theme
capacity. Lineup counts/health are mode-based. Exact imported episode gaps group
by season/range and offer DVD searches; period ad variety shortages offer video
searches. Unresearched history stays unknown, and owned/offline/excluded recordings
are distinguished from acquisition needs. Public-source period scraping is still
not implemented and is required before missing-inventory claims for new periods.

Tests cover context isolation/resume, shared media, same-day order stability,
concurrent identical launches, DST/lineup validation, metadata synchronization,
evidence gating, grouped episode recommendations and editable health standards.
Browser tests cover Time Machine save/preflight/playback/resume and scoped manager
links, in addition to the classic guide. Physical TV testing remains pending.

The guide/manager update adds a fixed 640×480 / 4:3 TV surface with flat early-
firmware styling (revised following the user's visual feedback), contextual colors,
full-PIP / bottom-third / TV-only modes and remote-event navigation. The manager
reports footage health, isolated theme/channel/history forecasts, unique inventory,
repeat pressure and historical evidence coverage. Sourced listing/requirement
imports constrain composition; located-file linking, explicit substitutions and
checksum-identical repair are available through the manager.

Tests verify forecast isolation, historical episode retention, known-ad gaps,
source repair without rewriting published segments, substitution labeling and
real-media attachment. See `GUIDE_AND_MANAGER.md` and ADR 0004. The demo now has
six explicitly fictional channels. Screenshots are under `docs/screenshots/`.

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

No automatic semantic identification/date research, full catalog/segmentation
editor, source-specific historical website scraper, verified marketplace search,
campaign optimizer, HLS/IPTV output, native TV APK or enhancement
worker is implemented. Browser
playback requires supported codecs and may have a brief transition between files.
The fixed guide is an application/storage rule, not tamper-proof enforcement
against the owner of the server.

Next narrow milestones: validate one sourced historical block against owned media
and test key delivery on a physical TV/browser or wrapper; then add source-specific
history adapters and reference-backed companion identification. Keep the prepared-
library path and immutable-guide tests passing throughout.

The hosted repository is `gregheerkens/tv-master`. GitHub app access was
reconnected and the project was uploaded through that connection. The cloud
terminal's separate `GH_TOKEN` was still invalid at the time of upload; connector
access does not depend on that terminal credential.
