# ADR 0010: editable Block Party playlists

## Context

The user explicitly requested Generate Block, recent blocks, regeneration and
editable JSON playlists. This relaxes the no-reroll rule for saved drafts only.
Published broadcasts and already-tuned contexts remain fixed.

## Decision

Store version-1 JSON documents in an additive `party_playlist` table, separate
from append-only broadcast/segment tables. Documents contain a name, a fixed
15/30/60/90-minute format, generation settings and ordered items referencing
catalog asset IDs or explicit gap milliseconds. They never carry filesystem paths.
Generation uses a fresh composition seed in a disposable copy of the library;
regeneration saves a new draft and retains its parent. Editing uses revision
checks so a stale editor cannot overwrite a newer save. Deletion removes only
the draft. No archival media is modified or imported through this viewer tool.

Tuning snapshots the saved document into a persistent representative context,
including its full ordered playlist. Published rows and future horizon extensions
read this snapshot, never the editable draft. Editing/deleting a draft cannot
alter an existing tuned context. A changed playlist can be tuned into a separate
context. Rejoining the same snapshot resumes its clock. Normal date/channel,
recording exclusion and source availability checks still apply; ineligible or
unfilled spans become explicit slates rather than silently changing order.

## Consequences

Drafts can be regenerated, edited, copied, downloaded and imported as JSON without
adding broadcast resets or source-management tools to viewer surfaces. A block
may be underfilled; its remaining time is a slate. Overfilled documents and
unknown asset IDs are rejected. JSON is stored locally in SQLite and is portable
between libraries only when referenced asset IDs/settings exist there.
