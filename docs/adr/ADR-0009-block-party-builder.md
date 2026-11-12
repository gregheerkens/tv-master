# ADR 0009: library-derived Block Party builder

## Context

The user requested an inclusive multi-select tag cloud, optional commercials and
bumpers, and fixed 15/30/60/90-minute custom blocks. This extends WHAT selection
with a small set of block formats; it does not introduce timeline editing.

## Decision

Block Party offers themes, years, months and networks derived from cataloged
program identities/ancestors, metadata, approved availability and network facts.
Selections are OR within a group and AND across groups; blank groups do not filter.
Ordinary eligibility, channel, daypart and source-preservation rules still apply.
These controls are separate from the historical Time Machine form.

Builder rules live in the existing saved recipe/context JSON. Only representative
contexts accept them. Block duration is restricted to 15/30/60/90 minutes and is
pinned when the context is created. Groups align to the context origin, not tune
time. They can contain several whole programs, with ordinary guide rows for each.
With continuity enabled, program slots round up to 15-minute units; without it,
acts run together at their full original duration. A program cannot cross the
custom block boundary. Remaining time without fitting material is a visible gap.
Commercials and bumper/station continuity are independently selectable.

Complete archival recordings are not chopped or repurposed by the builder. Custom
blocks compose prepared program recipes; original anchored recordings continue to
work in ordinary historical/surfing contexts. Published main-station rows and
existing contexts are never changed by choosing a new builder selection.

## Consequences

No database migration, analyzer or AI provider is needed. Existing recipes without
builder keys retain their previous behavior and context keys. New builder choices
save and resume like other selections, with the same no-reset/no-reroll guarantees.
Unknown metadata does not match a selected facet; blank filters still allow it.
