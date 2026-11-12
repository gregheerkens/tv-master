# Choose the television; join the broadcast

Open **Time Machine** from the TV guide (or press T). Everything uses the same
catalog, composer, player and source video files. New viewing selections store
schedule/catalog metadata, not duplicate videos or rendered channel streams.

## WHAT is easy to change

Choose a channel context, include/exclude themes, select shows or collections,
and optionally narrow the commercial/bumper collection. Save that selection with
a name and reuse it at another destination. These controls choose the eligible
material; they do not set an episode order, remove break time or expose a seed.

- **Plausible period television:** choose a specific date/time, or a Saturday
  morning, weekday afternoon or late-night template by year/month. Templates use
  the first matching weekday in that month. The resolved date is shown at preflight.
- **Sourced historical broadcast:** choose a specific date/time. The configured
  dated lineup and imported airings constrain the result. Unknown history remains
  unknown. Use the research desk to collect/review supported daily pages or sideload researched JSON.
- **Channel Surfing:** use the existing station clock. No date/time controls.
  An unfiltered choice returns to the original station; a filtered selection gets
  a persistent variant on the same clock.

Representative mode uses a clearly personal lineup and never labels its generated
sequence as an actual historical broadcast. Historical evidence stays in the
catalog so the manager can assess the same period under a historical standard.

## WHEN and HOW stay fixed

Check the selection, then tune in. The preview reports footage coverage, the
current program/segment, its source offset and any gaps. A 16:47 destination
joins a timeline composed from midnight; it does not start a show at 16:47.

The same selection/destination resumes its existing clock. Refreshing or returning
does not restart it. Adjacent entry times on the same day do not change the
composition seed or provide a hidden shuffle. The visible guide is always bounded
to the next 72 simulated hours. Future media cannot be played through the media
endpoint; tune requests derive their position from the server clock.

Switch channels, open the guide or visit the manager. Pause/skip/restart controls
are not offered. After a hidden tab becomes visible, playback rejoins the current
moment. A browser sound-permission prompt also rejoins live rather than beginning
at the first frame.

New catalog entries, verified source repairs and preference corrections can be
shared with saved selections. Previously published rows stay fixed. If a context
has been unwatched, elapsed airtime is first materialized with its prior catalog,
before new entries are adopted. No background per-channel decoder is required.

Viewing contexts live under `contexts/` beside the station database. Back up that
directory with the main database. A missing context database is reported as
unavailable, never silently regenerated/reset. Local server paths still point to
the same archived media. Source attachment/repair corrections are server-only; use the CLI or the
loopback admin console. Viewer assessments retain their selected context.

## The TV Master is the curator

The manager offers broadcast-operation, historical-recreation and theme-block
views of the same lineup. Define thresholds for playable footage, unique program
hours, repetition, period ad variety and the desired healthy-channel count.
Historical standards also specify listing/exact-episode coverage and whether
explicit substitutions are acceptable. Criteria change the assessment, not TV
timing or published programming.

Historical coverage is **unresearched**, **partial**, or **covered**. Unresearched
time is not a missing-program list. Named missing episodes require a sourced episode identity; imported titles now
create/match identities automatically. A program-only listing cannot identify an episode.
Inferred/seasonal expectations retain their uncertainty.

Acquisition recommendations:

- Group known missing episodes by series/season and contiguous episode ranges.
  Search eBay for relevant DVD seasons/collections. Do not imply an entire season
  is missing merely because only a few researched episodes are absent.
- For already cataloged recordings, inspect offline files, exclusions, eligibility
  and slot fit before recommending another purchase.
- Report commercial shortages against the user's variety target, with YouTube
  and Internet Archive searches for the selected era. This is a capacity/variety
  finding, not proof that particular unresearched commercials are missing.
- Prioritize historical research when the period lacks listings. Import researched
  evidence before making specific missing-content claims.

All external actions are **search links**, not verified listings, purchases or
identified tapes. Verify recordings and their date context when importing them.
Period pre-collection now works through supported daily-page adapters, saved HTML
and reviewed JSON sideloads; see `PERIOD_RESEARCH.md`. Universal source discovery
and semantic video recognition remain separate work.

The companion's current black/silence boundary detector, review/export and optional
physical cuts remain usable independently. A well-divided library bypasses it.

## Local endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/time-machine/options` | Catalog choices, named selections and saved signals |
| `POST /api/time-machine/recipe` | Save WHAT |
| `POST /api/time-machine/preflight` | Check a selection without changing the live station |
| `POST /api/time-machine/launch` | Tune a new context or resume the existing one |
| `GET /api/guide?context=…` | Same guide, selected timeline |
| `GET /api/tune?service=…&context=…` | Current segment/offset, never arbitrary playback time |
| `GET /api/broadcasts/health?mode=historical` | Mode-based lineup health |
| `POST /api/manager/health-standard` | Define assessment criteria only |

Selection rules support tags, excluded tags, included/excluded content identities
and continuity tags. Unsupported timing/seed/skip keys are rejected. Requests
can use a saved `recipe_id` or explicit service/rules. The same interfaces remain
usable without an AI provider or a hosted account.

The viewer now enters Time Machine and Block Party through separate manager
buttons; representative templates live in Block Party. Content/research tools
have moved to the server console. See `BROADCAST_SETUP.md` and `COMPLETE_BLOCKS.md`
for active reception layouts and intact local/remote source recordings.

## Block Party custom builder

Open `/block-party` for the multi-select cloud. Choose any number of themes,
years, months and networks, or leave all blank. Two selections in one group allow
either; groups combine together. Search narrows the visible cloud without clearing
selected tags; **Clear all tags** clears the facet selections.

The cloud comes from program metadata and inherited series tags, original-air dates,
approved availability periods and network records/metadata. Undated programs can
contribute bounded availability years (up to a 30-year interval); generic open-ended
ranges do not produce hundreds of year chips. `network:fox`, `year:1995` and
`month:7` tags are also recognized. These are library filters, not claims of exact
historical airings. Normal period/channel eligibility still applies.

Choose **15, 30, 60 or 90 minutes**, and independently enable **Commercials** and
**Bumpers and station continuity**. A block can hold multiple whole programs.
Programs are never truncated to meet its boundary; insufficient fitting material
appears as a real gap in preflight/health. Turning continuity off joins program acts
without inserted spots. Duration and continuity choices are saved with the selection;
returning resumes its fixed timeline. Anchored intact recordings are kept outside
this custom-recipe composition path. See ADR 0009.

### Generate and edit saved blocks

**Generate block** creates an editable JSON playlist from the current builder
settings. **New block** returns to the builder for a fresh selection. **Recent
blocks** offers Open, Regenerate and Delete; regeneration creates a new draft
using the original settings and keeps the original.

The editor shows ordered library segments and their duration total. Add a segment
from the library selector, replace a row with that selection, move rows up/down,
or remove them. Save changes or save as a new block. Unfilled time becomes a
station slate; over-capacity playlists cannot be saved. Generation filters guide
automatic selection; manual editing chooses the explicit segment order.

**Download JSON** exports the document. Under **Playlist JSON / import**, paste or
modify a document, apply it to the editor and save. The format is:

```json
{
  "version": 1,
  "name": "Saturday cartoons",
  "duration_minutes": 30,
  "selection": {
    "mode": "representative",
    "service_id": "kids",
    "destination": "1995-07-18T08:00",
    "rules": {"block_minutes": 30}
  },
  "items": [{"asset_id": "act-1"}, {"gap_ms": 30000}]
}
```

IDs must exist in your library; this example is a format illustration. Segment
references use their registered full spans. JSON cannot supply paths, seek controls
or unknown assets. **Tune saved block** copies the saved playlist into a fixed
broadcast context, repeating that block format along its advancing timeline.
Edits, regeneration and deletion affect drafts only; on-air copies continue
unchanged. Reopening the same tuned version resumes its clock. See ADR 0010.
