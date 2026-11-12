# Implementation status

Reviewed against the repository on 2026-11-12. This is an implementation inventory,
not a promise of exact historical coverage for an arbitrary library or location.

## Working

- Independent prepared-library ingestion and deterministic composition using
  SQLite, source hashes, virtual spans, ordered program acts, whole commercial
  spots, service/date/daypart/season rules and explicit gap slates.
- Persistent clocks, immutable published segments, current-offset tuning and a
  rolling 72-hour guide. Catalog changes never rewrite published programming.
- Time Machine preflight, specific/representative destinations, saved WHAT rules,
  separate persistent contexts and resume. Filtered surfing shares station time.
- PIP, bottom-third and TV-only modes on a 640×480 guide, remote-style keyboard
  navigation, numeric tuning, details and browser fullscreen.
- Four-mode viewer manager, saved region/provider/tier/channel layouts, live
  catalog/manifest meters, scratch assessments and adjustable health standards.
  Only the explicit Test UI uses simulated library values.
- Sourced listing import, daily wiki/Blog+ adapters, cached HTML, reviewed JSON
  sideloads, episode title/alias matching and next-day checks for midnight spill.
  Coverage reports distinguish unknown history from missing owned media; sourced
  episode gaps and ad-variety shortages produce acquisition search links.
- Server-only source attachment, checksum-identical repair, substitutions,
  research review and complete-block editor. These require CLI or `serve --admin`;
  ordinary viewer servers do not expose content tooling.
- Intact local and opt-in HTTPS blocks fixed to original broadcast/source brackets;
  optional approved local presentations preserve original references and timing.
  Remote availability is measured during playback, not assumed from a URL.
- Optional companion black/silence boundary detector, review/export, serial HTTP
  jobs and physical extraction. Raw sources remain unmodified.
- Corrected Branding v2 and Textless UI v1 assets, local VT323 font/license,
  responsive warm manager/server theme, blue guide and optional About artwork.
  Nested assets are included in packaged wheels.

## Validation record

The asset-integration revision passed 81 Python tests, six browser checks and a
wheel asset inventory check. Coverage includes import rollback, source preservation,
composition, concurrent schedule extension, clock/immutability behavior, context
isolation/resume, historical evidence, source repair, ingestion defaults, research
acceptance and UI/role boundaries. Earlier complete-block validation also exercised
real HTTPS range playback of generated footage at the expected source offset.

Browser tests use synthetic media and fixtures. These checks do not establish
physical-TV compatibility or validate real Internet Archive broadcast footage.
See `tests/` for the executable checks. Runtime galleries are local outputs; there
are no current screenshot fixtures in `docs/`.

## Remaining limitations

- No native TV APK, physical-TV remote verification or HLS/IPTV/transcoding adapter.
- Browser playback requires compatible codecs and may briefly transition between files.
- No automatic semantic identification of shows/ads/bumpers, historical dating,
  universal website/PDF/OCR scraper, or automatic historical cable-tier lookup.
- No full catalog/segmentation editor, restoration worker or campaign-frequency optimizer.
- Program break recipes still need approved/manual boundaries. Unknown episodes,
  rerun windows and channel histories are not fabricated.
- Search links are not verified products/tapes. Historical completeness depends
  on sourced listings and the user's library, not just playable airtime.
- The local server has no remote-account authentication. Admin tools bind to
  loopback; there is no supported public Internet deployment workflow.

See the [roadmap](DEVELOPMENT_ROADMAP.md) for the next independently testable work.
