# Source ingestion and reuse defaults

Two entry paths are supported, independently of analysis or enhancement:

```sh
python -m retro_tv ingest-rips /media/rips
python -m retro_tv ingest-recording /media/tapes/christmas.mp4 \
  --recorded-date 1995-12 --seasonal --holiday christmas --holiday-year 1995
python -m retro_tv ingest-recording /media/tapes/ordinary.mp4 \
  --recorded-date 1995 --not-seasonal
```

Ripped-media intake requires a folder, recursively finds supported video files,
hashes/probes them, and registers untouched sources. Recorded-media intake requires
one file, at least an approximate recording date, and an explicit seasonal answer.
Date input accepts YYYY, YYYY-MM or YYYY-MM-DD; both its precision and bounded
interval are retained. Seasonal input additionally requires a supported American
holiday and holiday year. No date is guessed from file modification time.

Source registration does not guess show identity, create approved playable
segments or change the guide. Follow it with reviewed library metadata or companion
analysis. Identical source IDs with matching path/hash/duration/context can be
referenced again by companion imports; conflicting redefinitions fail.

Each newly imported source requires `ingest` context in library JSON as well:

```json
{"kind":"recorded","recorded_date":"1995-12","seasonal":true,
 "holiday":"christmas","holiday_year":1995}
```

Use `{"kind":"ripped"}` for ripped material; `generated` is reserved for synthetic
fixtures/demo sources. Existing sources migrate as `legacy_unknown`; missing dates
are not invented or retroactively required to preserve already working stations.

## Recording-derived continuity reuse

Approved commercials, bumpers, promos, station IDs and PSAs inherit the recording
context. Nonseasonal material defaults to the recording's calendar year ±2 years,
inclusive: a recording dated 1995 suggests 1993-01-01 through 1998-01-01 exclusive.
This is an explicitly estimated reuse policy, not a first-airing fact.

Seasonal material defaults to the named holiday year ±2, around that holiday in
each target year. The provisional season is 30 days before through the holiday
itself. A 1995 Christmas bumper can appear around Christmas 1993–1997, not in July.
Thanksgiving and Easter are recalculated annually. A December 1995 recording
marked New Year's Day 1996 uses 1996 as the holiday-year center, not 1995.

Per-segment `metadata.reuse_constraints` overrides can specify:

- `year_specific`: a year, requiring `evidence` (e.g. a dated sweepstakes).
- `valid_from` plus exclusive `valid_until`, requiring evidence: replace the
  estimated bracket when documented campaigns were shorter or longer lived.
- `seasonal: false`: identify an evergreen spot inside a seasonal recording.
- `holiday`, `days_before`, `days_after`: reviewed seasonal adjustments; lead/lag
  offsets accept 0–90 days.

For example:

```json
{"reuse_constraints":{"year_specific":1995,
 "evidence":"Visible 1995 sweepstakes entry deadline"}}
```

The current recognizer does not automatically read dates from a commercial.
Reviewed users or a future recognition adapter supply these evidence fields;
the scheduler enforces them. Program episodes never receive the ±2-year rule.
Legacy asset/program validity and normalized eligibility rules still constrain
playout; any narrower applicable rule wins. Published blocks remain unchanged.

## Companion context

The analyzer CLI takes the same mandatory recording arguments:

```sh
python -m retro_tv.companion analyze /media/tape.mp4 review.json \
  --recorded-date 1995-12 --seasonal --holiday christmas --holiday-year 1995
```

The job service accepts an `ingest` object alongside `path` and rejects incomplete
recording context before queueing work. Reviewed continuity can use inferred
date defaults at export; identity and approval are still required. Episodes need
their own explicit eligibility dates. Original premiere dates remain unknown
unless separately established.

Next testable step: a graphical ingest form exposing these requirements, inherited
reuse estimates and per-segment corrections before approval.
