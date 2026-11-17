# ADR 0012: viewer quality-of-life controls

## Context

The user authorized all seven proposed improvements: live match counts, edit and
delete undo, unsaved draft recovery, segment search/type filters, recent-block
search/pins, clear draft/on-air status, and recall/last-channel restoration.

## Decision

Match counts reuse catalog eligibility, content identity, source availability and
current selection rules without composing or changing the station. Preflight
remains responsible for full block health. Pins use an additive server table.
Viewing context requests record draft ID/revision for copy links; their ordered
playlist snapshots stay immutable. Legacy copies can be linked by matching their
stored document. Local UI preferences never determine broadcast order or clocks.

The editor stores bounded undo history in memory and recovery copies in optional
browser storage, scoped by station identity. Recovery is explicit and retains the
server revision for optimistic saves. Undo deletion recreates a new draft; it
cannot change a published copy. Search/filtering acts on metadata, not source
files. Recall stores only service IDs and rejoins live source offsets. Channel
memory is scoped by station, layout and viewing context, validates lineup
membership, and yields to explicit channel links. Storage failures degrade to
ordinary viewing without preference persistence.
