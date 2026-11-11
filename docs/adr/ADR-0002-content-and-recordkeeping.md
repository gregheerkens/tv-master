# ADR 0002: Separate content, recording, channel history and user records

Status: accepted following the user's agreement on 2026-11-11.

## Decision

Keep SQLite. Add normalized content identities and optional episode metadata,
separate asset/program identity mappings, multiple evidenced eligibility windows,
channel modes, dated station/primary-affiliation records, and recording-specific
quality/preferences. Keep provider cable positions separate from OTA station
numbers. Resolve history from imported facts; do not invent Rochester mappings.

Content-wide exclusions inherit through series/episode relationships. Recording
exclusions apply to one asset. Both constrain future composition only. Quality
warnings and favorites do not silently become bans or alter published slots.
Derive play counts from immutable scheduling history and distinguish explicit
view observations from merely scheduled/started broadcasts.

## Migration and consequences

Schema version 2 adds tables and backfills legacy identities transactionally;
archival sources and published playout rows remain untouched. Legacy library
JSON remains supported. Metadata-only CLI operations do not invoke media tools.
Source media availability remains independent from content/history records.

The existing legacy date windows remain upper bounds; normalized windows add
constraints. Historical data-provider integration, recording-substitution logic,
campaign weighting and a graphical catalog editor remain later work. These
choices refine the canonical data model without changing its settled principles.
