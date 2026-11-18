# ADR 0013: research packet interoperability and media fallbacks

The user supplied a near-complete Rochester research subset and requested
compatible interchange, multiple dated airings per media identity and related
backup references across the suite.

Import ZIP/JSON/reference SQLite as data, preserve the full reference document,
and normalize dated and recurring schedules through the supplied resolver's
precedence. Materialize a requested date range with idempotent packet ownership.
Research updates are transactional and cannot rewrite published evidence. Retain
unknown coverage, citations, evidence labels, recording leads and licensing
metadata. Keep provider channel positions separate from station/service identity.

Use existing content/asset/program/airing relationships for multiple recordings
and reruns. Add direct curator-ranked same-kind content fallbacks. Available
same-identity program copies are preferred. Distinct replacements are explicit
substitutions and must fit the original slot. Known continuity requirements may
use approved backups while reporting the original requirement separately.
Prepared media, companion exports and research packets share catalog IDs and
provenance; research records do not create owned-media records.
