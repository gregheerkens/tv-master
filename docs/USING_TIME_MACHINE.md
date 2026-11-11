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
  unknown. This release does not scrape public listings automatically.
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
the same archived media. Source-specific context corrections can be made through
the manager opened from that viewing context.

## The TV Master is the curator

The manager offers broadcast-operation, historical-recreation and theme-block
views of the same lineup. Define thresholds for playable footage, unique program
hours, repetition, period ad variety and the desired healthy-channel count.
Historical standards also specify listing/exact-episode coverage and whether
explicit substitutions are acceptable. Criteria change the assessment, not TV
timing or published programming.

Historical coverage is **unresearched**, **partial**, or **covered**. Unresearched
time is not a missing-program list. Named missing episodes require exact imported
airing evidence; a program-only listing does not establish an episode identity.
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
Automatic period pre-scraping and semantic video recognition remain separate
adapter/companion work; the app does not pretend those exist.

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
| `GET /api/manager?standard=historical` | Mode-based lineup health |
| `POST /api/manager/health-standard` | Define assessment criteria only |

Selection rules support tags, excluded tags, included/excluded content identities
and continuity tags. Unsupported timing/seed/skip keys are rejected. Requests
can use a saved `recipe_id` or explicit service/rules. The same interfaces remain
usable without an AI provider or a hosted account.

## Preview images

[Time Machine chooser](screenshots/time-machine.png) and
[manager recommendations](screenshots/manager-recommendations.png) use generated
test footage and explicitly synthetic episode/listing evidence. They are UI
examples, not claims about actual historical programming.
