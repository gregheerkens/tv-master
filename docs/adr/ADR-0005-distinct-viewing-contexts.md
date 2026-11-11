# ADR 0005: Distinct Time Machine and Channel Surfing contexts

Status: accepted product direction from the user's 2026-11-11 clarification.

## Context

The user wants both a date/time/channel-selectable historical Time Machine and
uneditable channel surfing that joins predetermined programming midway through.
The initial station implementation has one immutable clock; the manager can
analyze other dates but cannot yet play a separate reconstruction session.

## Decision

Name the modes explicitly. Keep the current no-reset/no-reroll invariant for
Channel Surfing. Introduce separate reconstruction contexts for future Time
Machine playback; choosing a destination must never change that live station.
Within any selected context, channel surfing shares a common simulated clock
and published guide entries remain fixed with a 72-hour visible horizon.

Offer exact-date evidence-based reconstruction and explicitly representative
period/daypart reconstruction as distinct choices. Reuse the shared catalog,
history, composer, health/manager and guide. Keep companion analysis optional.

The timeline advances without running a decoder or streaming unwatched channels.
On tune, resolve the manifest segment and source offset from the context's clock.
Lazy generation must preserve predetermined order through pinned inputs or stored
manifests; a viewer's arrival must not reroll programming.

## Consequences

This deliberately narrows ADR 0001's single-context limitation without introducing
a reset to the existing station. It restores the broader time-machine intent of
the original handoff while preserving its continuous-clock and manifest semantics.
It records the user's requested scope; session APIs, UI and source adapters are
future implementation work, not features claimed by this documentation change.
