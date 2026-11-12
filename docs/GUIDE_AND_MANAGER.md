# TV guide and TV MASTER manager

## TV-facing guide

The guide is drawn on a fixed 640×480 surface, fitted to the screen at 4:3.
It uses the supplied blue component shells, beveled borders, a bundled pixel font
and a blue focused cell with white text. A widescreen display pillarboxes this
early-firmware layout; see [asset integration](BRANDING_INTEGRATION.md).

Guide cycles between a full four-row grid with a live upper-right preview, a
two-row bottom-third overlay and unobstructed TV. The video element is retained
across modes; browsing other channels does not retune it.

| Control | Action |
| --- | --- |
| Arrows | Browse channel/time cells |
| OK / Enter | Tune a current listing; show options for a future listing |
| Guide / G | Full guide → bottom third → TV → full guide |
| Info / I | Program details, coverage and evidence |
| Back / Escape | Close details, then step out of the guide |
| ChannelUp / ChannelDown | Tune the next/previous channel live |
| Number keys, Enter | Direct channel-number tuning |
| PageUp / PageDown | Browse a day backward/forward, bounded by the 72-hour guide |
| F | Browser fullscreen, including the guide |
| M | TV MASTER manager |

Ready slots have a green indicator. Unfilled continuity/quality issues are amber;
missing programs red; unavailable source files purple; explicit substitutes cyan;
unknown historical listings gray. Channel/time labels are yellow; selection uses a brighter blue frame. Text labels in the
information panel distinguish these states without relying on color alone.

Tests cover keyboard/D-pad-equivalent browser events, not physical TV hardware.
A future native wrapper may need to translate device-specific Guide/Back keys.

## Viewer manager and assessments

Open `/manager` for the four-mode viewer hub. Choose **Manage Broadcasts**
(`/broadcasts`) for reception layouts and assessments. It provides:

- Live 72-hour channel health: playable program/continuity hours, unfilled time,
  unavailable media and quality alerts.
- A 1–3-day analysis of current channel rules, historical reconstruction or a
  hypothetical tagged theme. All composition occurs in a disposable database
  copy. The live clock and published schedules are unchanged.
- Unique content inventory and repetition pressure, separated from raw playable
  airtime. Repeating one episode cannot establish historical completeness.
- Historical evidence coverage, episode gaps and known commercial/bumper
  requirements, with source provenance independent of media availability.

Source inventory search, located-media linking, explicit substitutions and
checksum-verified repair belong to `/server-manager` on the separate
loopback-only `serve --admin` console, not the viewer manager.

Analysis of another historical date is an administrative planning tool, not a
way to reset, reroll or seek the live station. It never exposes future playback.

### Fill a gap versus change a published slot (server console)

**Locate prepared media:** select a server-local ripped/prepared-library folder,
the divided file inside it, its catalog identity and an approved eligibility
period. Source registration and identity links are atomic. This makes the file
available for later composition and new assessments. Recorded captures still
use the mandatory context workflow documented in `INGESTION.md`.

**Restore a missing source:** locate a byte-identical copy. Its hash must match
the original. A separate location record lets existing published segments play
again without changing their identity, offsets or schedule.

**Explicit substitute:** select an existing program recipe and record a reason
for replacing unavailable historical content. Analysis and unpublished blocks
label it `substituted`. Existing published gaps are not rerolled.

The server console is for trusted local maintenance. Its write routes accept same-origin
JSON; this release does not add remote-account authentication or Internet hosting.

## Importing historical requirements (server only)

Import normalized, sourced JSON in `/server-manager` on the admin console or with:

```sh
python -m retro_tv import-plan examples/listings.json
python -m retro_tv assess --service kids --date 1995-07-18 --days 3 --mode historical
python -m retro_tv assess --service kids --date 1995-07-18 --mode theme --tags cartoon,summer
```

The example expects the identities from `examples/records.json`. All example
listings are synthetic and explicitly labeled. A listing can reference a content
identity that has no media. Continuity requirements can name a known missing
commercial or describe a required category and duration with evidence.

Imported airings constrain composition at their actual boundaries. Exact episode
matches remain distinct from program-only/seasonal/inferred listings. In historical
mode, uncovered periods remain unknown; the composer does not fill them with
unrelated programming and call them reconstructed history.

Known continuity requirements are checked against the actual composed segments,
not merely the existence of a generic ad pool. Daily wiki-table and Kids Block Blog+ adapters, saved HTML and reviewed JSON
sideloads are available; see [period research](PERIOD_RESEARCH.md). Universal
website/PDF/OCR scraping is not implemented. Scraped facts must retain citations and
uncertainty. The sources below were used to research interface behavior/imagery,
not to fabricate episode schedules or Rochester cable assignments.

## Visual research

Primary period anchor:

- [Scientific-Atlanta ER1/IPG quick-reference card, October 2000, Part 717868 Rev C](https://assets.ctfassets.net/8kj4n9zmpxu3/6hSCwXaXjJGAKaaA9boiKI/38aa1dbd7c7209ec488d04257091452c/sa-er1-remote-qrg.pdf).
  The dated guide illustrates the live upper-right preview, directional browsing
  and separate treatment of future program selections.
- [Explorer 2000 manual, 1999](https://www.manualslib.com/manual/149635/Scientific-Atlanta-Explorer-2000.html).
- [TVWeek, Passport navigation software, February 26, 2001](https://www.tvweek.com/in-depth/2001/02/product-spotlight-passport-nav/).
  Establishes a period Passport/Time Warner deployment, with market variation.

Other references examined:

- [Passport designer's portfolio](https://www.geoffombao.com/passport-dvr): useful
  layout reference, but not treated as proof of a particular early firmware date.
- [Time Warner Passport Echo deployment report, October 2004](https://www.nexttv.com/news/time-warner-dvr-glitch-fixed-337268).

The UI is an original recreation of period conventions, not copied firmware or a
claim to reproduce one verified Rochester software build. No third-party guide
screenshots or provider branding are bundled as application assets.
