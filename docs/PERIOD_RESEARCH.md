# Research a period before measuring its gaps

Open `/research` on an explicit loopback `serve --admin` console; research is server-only. No API key or AI provider is needed.
The database keeps collected source pages separate from accepted historical airings.
An HTTP success, a search result or a saved page alone never establishes coverage.

## Working path

1. Choose a configured service, date range (exclusive end, maximum 31 days), source
   feed timezone and daily source URL/template. A service is independent of any
   local cable number. The default template targets Nickstory-style daily pages.
2. Collect individual dates or run the pending batch. The browser requests dates
   serially, with a one-second interval. Stop leaves collected work intact. A
   failure stops bulk collection and can be retried; there is no retry loop.
3. Alternatively supply saved HTML for a date or sideload a research JSON bundle
   collected with another browser/tool. Cached pages remain usable offline.
4. Review source times, warnings, episode annotations and catalog matches. Checked
   slots are accepted in one transaction. Conflicts preserve existing evidence and
   roll back the whole page; they never silently replace a listing.
5. Assess the same service/date in the manager. Accepted program-level listings
   count as researched slots; episode-exact coverage is a separate measure.

Reopening an accepted page shows which rows were actually accepted. Reaccepting
it is idempotent. To accept a different subset later, export and sideload another
research batch; conflicting existing evidence remains protected.

## Supported adapters and limits

- `mediawiki_daily`: an HTML table with Time and Show/Program headers and optional
  Episode column, including rowspans. A multi-row show/episode span becomes one
  longer airing. Distinct episode cells remain separate slots.
- `kidsblock_post`: timed lines inside The Kids Block Blog+ daily post's
  `entry-content`. An exact daily URL can be used instead of a template.
- `sideload`: normalized JSON collected elsewhere. It needs source URL, retrieval
  date/method, explicit-offset timestamps and bounded program slots.

Templates support `{wiki_date}` (e.g. July_18%2C_1995), `{date}` (ISO), `{year}`,
`{month}` (two digits), and `{day}` (unpadded). Parsing requires a heading identifying
that date. Only HTML is fetched, with a 15-second timeout and 1.5 MB page limit.
Scripts are not executed. Public HTTPS URLs are required; private/local URL targets
and redirects are rejected. Source failures or layout changes produce research
errors, not guessed programming. There is no universal OCR/PDF or arbitrary-site
scraper, full-site crawl, search-engine discovery or historical station lookup yet.

The parser uses the next explicit listing start as a slot's end. Blank listings
stay blank. Bad clocks break continuity. Late-night final slots poll the next day:
a matching midnight continuation uses its next boundary; a different named program
implies 23:59 inclusive (exclusive midnight in storage). Unavailable or blank first
slots stay pending. Supply `next_html`/`next_day_url` or `retry_boundary` to resume a
cached pending lookup. Other unbounded final slots are omitted rather than guessed.
Evening-to-midnight rollovers are handled. Ambiguous/nonexistent DST times require
sideloaded timestamps with explicit offsets. Durations longer than four hours
require a separately reviewed listing import rather than automatic inference.

## Evidence and matching

Scraped slots retain `schedule_exact` as their source-confidence state. Named
episodes now become usable catalog identities, even without season numbers. This is a claim attributed to
that source, not a verified as-aired log. Human review is required before acceptance.
The UI suggests a catalog identity only for an unambiguous matching title, with
matching episode text when present; it never uses fuzzy matching to claim an episode.
Unmatched accepted titles get program identities without invented season/episode
numbers. An `exact` row requires a catalog episode/movie and explicit confirmation.
Inferred and seasonal expectations do not count as established research coverage.

Snapshots retain the URL, retrieval time, content hash, warnings, original normalized
rows, selected identities and accepted airing references. For fetched HTML the hash
is of the stored HTML text; for sideloads it is of the normalized JSON source snapshot,
not a claimed checksum of the remote page. Source annotations and end-boundary basis
are preserved in airing provenance. The app keeps source truth independent of media
ownership and never changes published guide rows while researching or accepting.

## Real sideload example

`examples/research/nickelodeon-1995-07-04.json` contains **44 bounded program slots**
from [The Kids Block Blog+ daily listing](https://kidsblockblog.wordpress.com/2021/01/16/nickelodeon-schedule-for-tuesday-july-4-1995/),
retrieved through web browsing on November 11, 2026 and manually normalized to JSON.
This is real secondary-source listing data, separate from synthetic test fixtures.
It establishes no Rochester station/cable position, commercials or bumpers.

The source leaves 05:30–07:00 blank. Its 23:30 entry is now resolved against the July 5 listing: a different midnight
program implies 23:59 inclusive. Thus the bundle provides **22.5 hours / 93.8%** program-slot coverage
for that day, with **0% automatically established exact-episode coverage**. These
are completeness measures of accepted source claims, not independent verification.

To add the logical service if it is absent:

```sh
python -m retro_tv --db data/station.sqlite import-records examples/research/nickelodeon-service.json
python -m retro_tv --db data/station.sqlite research sideload examples/research/nickelodeon-1995-07-04.json
```

Then open `/research`, inspect the source and accept selected rows. If the service
already has a different configured ID, change the bundle's `service_id` to that ID;
keep the original source URL and feed identity. Do not map it to an unrelated theme
channel or invent a local historical lineup.

CLI actions are `research create|fetch|sideload|accept REQUEST.json`, `research list`,
and `research export BATCH_ID`. Request bodies use the same fields as these routes:

| Route | Purpose |
| --- | --- |
| `GET /api/research` | Collected batches, source dates and catalog matching choices |
| `POST /api/research/create` | `service_id`, `start_date`, `until_date`, `timezone`, `adapter`, `url_template` |
| `POST /api/research/fetch` | `page_id`, optionally saved `html`; otherwise fetch its URL |
| `POST /api/research/sideload` | Version 1 research JSON bundle |
| `POST /api/research/accept` | `page_id`, `selections` with `index`, optional `content_id`, `evidence_state`, `episode_confirmed` |
| `GET /api/research/export?batch=…` | Portable staged research JSON, ready for review elsewhere |

Research always belongs to the root catalog, including when opened from a Time
Machine manager. Existing context catalog synchronization carries new accepted
identities/listings forward without resetting any published viewing timeline.

## Local runtime screenshot library

`node scripts/capture-runtime.cjs` captures actual app screens against a prepared
synthetic demo, without resetting its database. Set `RETRO_TV_URL` and optionally
`TV_MASTER_SCREENSHOTS` (default `data/runtime-screenshots`, ignored by Git).
It creates numbered PNGs, an HTML gallery and a JSON manifest. Set
`TV_MASTER_ADMIN_URL` to capture the separate server block editor, and
`TV_MASTER_CAPTURE_TUNE=1` to tune the prepared demo block. No images are uploaded.
Generated demo media makes playback verifiable without pretending TV footage is
included in the application.

Episode titles are matched with punctuation/segment/number normalization and
optional `content_aliases` in catalog records. `research enrich REQUEST.json` merges
supplemental episode references by timestamp, or a premiere date when exactly one
slot matches the show that day. Ambiguous repeated slots stay unresolved. The
included episode supplement cites Nickstory’s Alvin and Richard Scarry episode
indexes; those two titles are also present in the updated main sideload bundle.
Source details remain hover/focus notes in viewer screens. See ADR 0007.
