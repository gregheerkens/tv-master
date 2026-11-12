# ADR 0011: calendar destination choices

## Context

The user requested three destination options: a specific date/time, a specific
date and Today in a selected year. Today/year should support immersive daily TV.

## Decision

Both viewer destination forms offer those three choices. A date alone resolves
to local midnight. Today/year resolves on the server using the active broadcast
timezone's current month, day and wall-clock time, replacing only the year.
Preflight returns the resolved selection so Tune uses the moment actually checked.
The context key for Today/year uses its resolved calendar day, not entry seconds;
return visits that day resume the existing clock. Next day is a new destination.
Saved generated playlists keep the resolved selection rather than moving dates.

Legacy representative weekday/daypart templates remain supported by the API for
saved selections but are removed from the viewer dropdown. Existing context keys
for specific destinations are unchanged. No published timeline is reset or edited.

## Limits

A non-leap target year on February 29 and nonexistent local DST times produce an
explicit error. Historical viewing still needs sourced dated lineups/listings and
media. The calendar shortcut does not infer unknown broadcast schedules. Block
Party continues to compose representative programming from its library filters.
