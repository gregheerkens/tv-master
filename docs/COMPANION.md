# Optional analysis companion

The station accepts one versioned library contract. Hand-prepared libraries and
reviewed companion results use that same contract. The companion never writes
published programming, runs the scheduler, or requires restoration.

## Implemented baseline

1. Accept an existing local recording under a configured media root. Downloads
   and Internet Archive scraping are not part of this initial worker.
2. Probe duration and hash the untouched source.
3. Scan black transitions and silence with FFmpeg. Propose boundaries at black
   interval midpoints, retaining coverage from source start to end.
4. Persist a review document containing virtual spans, evidence and confidence.
   This confidence concerns boundary detection only.
5. Leave semantic type, identity, summary, original air date, rerun window and
   network/station unknown. A reviewer may merge/split candidates and annotate
   them. A reviewed candidate requires identity evidence before export.
6. Export approved entries to the station's standard library JSON. Supply program
   recipes with ordered act IDs in a top-level `programs` list as necessary.
7. Optionally extract reviewed spans as non-overwriting presentation derivatives.

## Review fields

- `title`, `kind`, `summary`: what the segment is. Supported kinds are program,
  commercial, bumper, promo, station_id and psa.
- `original_air_date`: evidence-backed first airing if known; null is legitimate.
- `valid_from`, `valid_until`: approved eligibility/rerun window; end exclusive.
  These are not automatically proof the content actually aired during that span.
- `services`: station catalog service IDs; empty means usable on any service.
  Do not store a cable channel number as a network's identity.
- `network_or_station`, `identification_evidence`: attribution and its basis.
- `review_status`: pending, rejected or approved. Only approved entries export.

An approved title must not be a guessed exact episode represented as fact. A
reviewer can use a general description with explicit uncertainty. Source records
and span metadata retain evidence for later correction and better matching.

## Recognition adapter milestone (not implemented)

An identification adapter should enrich these documents using labeled reference
clips, audio/video fingerprints, optional OCR/transcription and candidate search.
It must report identity confidence independently of boundary confidence, retain
reference citations and permit unknowns. Date proposals need a cited first-airing
fact and a separately justified rerun bracket; visual appearance alone cannot
establish broadcast history. User-approved service mappings resolve local cable
positions through dated lineup entries.

Acceptance: with a small synthetic/labeled reference set, recover known matches,
leave out-of-corpus clips unknown, preserve uncertain date evidence, and export
only approved matches into the unchanged standalone player. Evaluate on real VHS
noise, hard cuts with no black, fades, show-internal black frames, logos and ads
with similar openings before claiming reliable automatic segmentation.

## Service boundary

`POST /jobs` accepts `path` under `--media-root` plus mandatory recorded-media
`ingest` context (recording date, seasonal answer, and holiday/year if seasonal).
See `INGESTION.md` for examples and inherited continuity reuse defaults.
`GET /jobs/<id>` returns queued/running/awaiting_review/failed/interrupted state.
One worker serializes heavy analysis; results persist in `--jobs`. Work interrupted
by restart must be resubmitted. Save the GET response as JSON and use `export`;
the CLI accepts both wrapped service responses and plain review documents.

Bind to localhost by default. Both services are trusted-home prototypes, without
Internet authentication/TLS, and must not be exposed directly to the Internet.
