# TV MASTER: viewing modes and companion workflow

Product requirements captured from the user's 2026-11-11 description. This is a
target experience, not a claim that all features below are implemented.

## 1. Time Machine: choose the television you want to visit

The viewer enters **Time Machine**, selects a historical date, time and channel,
and sees whether the archive can reconstruct that broadcast before tuning in.
Historical channels resolve through market, provider and dated lineup; a themed
channel can instead resolve through its own rules. A channel number alone is not
a stable historical identity.

Two reconstruction choices must be explicit:

- **Specific broadcast:** e.g. a selected Rochester provider/channel at 16:30 on
  a particular date. Combine publicly available historical evidence with the
  local catalog. Show what is established, available, missing or substituted.
- **Representative period block:** e.g. a weekday afternoon in 1995 or Saturday
  morning in 1995. Use period, weekday, daypart, station/network, seasonal and
  library constraints to assemble a plausible experience. This is not evidence
  that the generated sequence actually aired on a particular historical date.

The preflight should distinguish program-only availability from exact episodes,
and separately assess ads, bumpers, promos, local continuity, source quality and
seasonal compatibility. Missing history must not be confused with missing media.
Allow the user to locate missing material or choose explicitly labeled substitutes
under the same manager policies used elsewhere.

Public-source adapters should retrieve and cache evidence, normalize it into the
catalog and retain citations. Ordinary APIs, HTML/PDF/OCR imports and manually
curated packs can all participate. AI is an optional enrichment aid, not a playback
or catalog requirement. No single source is presumed to establish all historical
station affiliations, cable positions, episode airings and commercial campaigns.

Tuning opens a **separate reconstruction session** at the requested historical
instant. All channels in that session share its simulated clock. Changing the
Time Machine destination creates/selects a reconstruction context; it does not
reset the Channel Surfing station or mutate any published schedule. The guide
inside a selected context still exposes only the next 72 simulated hours.

## 2. Channel Surfing: join television already underway

This mode behaves like an unattended cable system. The channel schedule, show
order and start/end times are predetermined and cannot be edited, shuffled or
restarted by tuning, leaving, refreshing or changing channels.

**The timeline is in progress; media processing does not need to be.** A channel
does not require a background decoder, rendered stream or active viewer to keep
its place. Keep a time-addressed manifest and a persistent clock anchor; open and
decode the appropriate local file only when someone tunes in.

```text
simulated_now = historical_anchor + (real_now - real_anchor)
entry = manifest entry containing simulated_now
source_position = entry.source_in + (simulated_now - entry.broadcast_start)
```

For example, if a composed broadcast began at 16:30 and simulated time is 16:47,
tune into minute 17 of the broadcast timeline. That position may fall within an
episode act, commercial or bumper; resolve the actual segment and its source
offset rather than seeking blindly 17 minutes into the episode file.

The schedule may be generated ahead or materialized lazily, but viewer activity
must not choose a new order. Persist manifests or pin their seed, catalog/rule
versions and other inputs so that a library update cannot rewrite the current
day. All viewers sharing a channel timeline should join the same moment.

The rolling 72-hour guide remains fixed as published and extends at its far end.
Unwatched channels need metadata/clock bookkeeping, not continuous video work.

## 3. Companion: turn long recordings into reusable library material

Accept long off-air recordings, including locally obtained Internet Archive
captures of the kind used by Spelunkr. Require the recording context specified in
`INGESTION.md`: at least an approximate date, an explicit seasonal answer, and
holiday/year when seasonal.

The target workflow is:

1. Detect program, bumper and individual-commercial boundaries.
2. Identify/describe the segments and propose program/episode, station/network,
   dates, seasonal relevance and reusable metadata with evidence and confidence.
3. Review uncertain boundaries and identities; retain unknowns instead of
   presenting guesses as established broadcast history.
4. Preserve the archival recording. Canonical segments are virtual source spans;
   optionally produce physical clips for convenience.
5. Store approved segments and their lineage in the shared catalog. Apply the
   estimated ±2-year continuity reuse defaults, holiday rules and stronger dated
   evidence overrides already specified for ingestion.
6. Let the independent frontend/composer use those assets to build plausible
   period blocks. Known original blocks can retain their original order.

Users with already divided, well-described libraries bypass this companion
entirely. Neither restoration nor upscaling is required.

## Shared foundation and implementation boundary

Both viewing modes use the same catalog, source spans, historical evidence,
eligibility rules, composer, health reporting, retro guide and lazy media adapter.
Keep timeline/session identity explicit so a user-directed historical destination
cannot accidentally become a reset command for the live surfing station.

Current implementation:

| Capability | Status |
| --- | --- |
| Fixed pseudo-live clock, predetermined manifests, tune at source offset | Working for the single Channel Surfing station |
| Open local media only for viewing | Working; no per-channel background video renderer |
| Classic guide, manager, 1–3-day isolated assessments | Working |
| Dated listing import, catalog matching, known gaps and substitutions | Working through sourced JSON/local records |
| Theme-tag and date/daypart/season eligibility | Working foundation for representative blocks |
| Named Time Machine destination/session workflow | Planned; manager assessment is not yet Time Machine playback |
| Public-source historical scraping/enrichment adapters | Planned |
| Companion boundary candidates, reviewed import, optional physical cuts | Working baseline |
| Automatic program/ad/bumper identification and historical dating | Planned; current baseline requires review |

Next independently testable Time Machine slice: select a specific date/time/channel,
run preflight, create an isolated context from sourced fixture listings, tune at
the correct act/ad offset, and prove that the surfing station's anchors, published
order and guide remain unchanged. Follow with representative weekday/Saturday
templates and a source-specific evidence adapter.
