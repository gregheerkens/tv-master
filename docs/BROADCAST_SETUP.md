# A viewer frontend, with the machinery on the server

Normal startup is the full PIP guide. Choose **TV MASTER MANAGER** (or press M):

- **TIME MACHINE:** a specific historical date/time/channel, with episode-aware lookup.
- **CHANNEL SURF:** the station's advancing clock, joined in progress.
- **BLOCK PARTY:** period/theme blocks, representative Saturday/weekday templates,
  saved show selections and the same fixed broadcast behavior after tuning.
- **MANAGE BROADCASTS:** region, reception, provider, cable tier, dated channel map,
  live on-air coverage, mode-based assessments and adjustable health standards.

Both the modern cassette-style manager and its forms support remote focus. The
TV guide uses a separate blue SD/pixel-font skin. Source notes are small hover/focus flags,
not repeated verification dialogs. Named episode details appear in the guide and
preflight; sourced episode identities also drive eBay and Internet Archive links.

## Set up reception

Choose a configured provider or supply a personal provider name. Set your region,
timezone, antenna/cable reception, cable level and channel membership/numbers.
Copy an imported dated lineup or use your own numbers. The tier describes the
selected membership; this release does not fetch a cable company's historical
package automatically. Add authoritative station/provider history on the server.

Save the setup; its channels appear in the guide and selectors. Existing program
order and clocks do not reset. New contexts include the setup identity; saved
contexts keep their original setup. Additional reception layouts live in the
secondary switcher. Personal maps are personal configuration, not asserted facts
about Rochester cable history. Regional eligibility uses the selected market;
new user-named regions/providers remain separate from imported historical facts.

Live health reads current local file availability, recorded playback results for
remote sources and the published 72-hour manifest. Individual mode/date assessments
run on scratch plans. Bars display the same measured percentages as their labels.
Counters are catalog counts, not claims that every registered recording is online.
The explicit **Test UI** screen simulates a populating or stocked library without
writing data or affecting the actual manager. It is never the startup view.

## Server tools stay on the server

The normal `serve` command does not expose source-file or research management
routes. Use CLI operations for ingest, research, organizing, source attachment,
complete blocks and presentation approval. For maintenance on the server itself:

```sh
python -m retro_tv --db data/station.sqlite serve --admin --port 8788
```

This optional console binds only to loopback. `/server-manager`, `/research` and
`/block-editor` are available there, not in the ordinary viewer server. The normal
frontends contain no links or controls for ripping, files, source import or repair.
The optional companion remains an independent server-side tool.

## Endpoint surfaces

- Viewer: `/`, `/manager`, `/time-machine`, `/block-party`, `/broadcasts`, `/test-ui`, `/about`.
- Viewer metadata: `/api/home`, `/api/broadcasts`, `/api/broadcasts/health`,
  `/api/health-standards`, existing guide/tune/Time Machine endpoints.
- Server only: research endpoints and source/repair/import endpoints, plus
  `/api/blocks/register`, `/api/blocks/presentation`, `/api/blocks/options`.

See `COMPLETE_BLOCKS.md` for local and remote intact recordings.
