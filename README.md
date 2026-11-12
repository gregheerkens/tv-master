# TV MASTER

A local period-TV app built from your prepared programs, commercials and bumpers.
Choose what belongs on your channels, then tune into fixed broadcasts already in
progress. The scheduler works independently of the optional analyzer and upscaler;
no AI account or GPU is required.

## Try it

Run from the repository root with Python 3.11+. Install FFmpeg and ffprobe on PATH
for the generated demo, media import and optional companion. The application uses
Python's standard library; no runtime Python dependencies need installing.

```sh
python -m retro_tv demo
python -m retro_tv serve
```

Open **http://127.0.0.1:8787**. The synthetic demo has six fictional channels and
colored test videos on an advancing July 1995 clock. It includes no TV footage or
verified historical cable lineup. Use a fresh database for your actual library.

Startup is the PIP guide. **TV MASTER MANAGER** opens:

- **Time Machine:** choose a historical date/time/channel, assess coverage, tune or resume.
- **Channel Surf:** join the station's advancing timeline.
- **Block Party:** choose representative period/theme blocks and saved selections.
- **Manage Broadcasts:** configure reception/channel maps and inspect mode-based health.

Arrows browse; Enter/OK tunes; G cycles PIP → bottom-third → TV; I shows details;
numbers tune channels; M opens the manager; F toggles fullscreen. A browser may
require the sound/resume button. See [guide controls](docs/GUIDE_AND_MANAGER.md).

## Use your own library

Edit `examples/station.json` into your own configuration before initializing:
set the historical start with timezone offset, market/provider and dated channels.
Example channel numbers are personal assignments, not Rochester cable facts.
Create a library JSON using `examples/library.json`, replacing paths, identities,
source ingestion context, dates and provenance with your material.

```sh
python -m retro_tv --db data/my-station.sqlite init my-station.json
python -m retro_tv --db data/my-station.sqlite import-library my-library.json
python -m retro_tv --db data/my-station.sqlite serve
```

Import your initial material **before** serving or running `guide`, because both
publish the initial horizon. Imports are transactional and append-only. Whole
files and virtual spans (`in_ms` / `out_ms`) are supported; archival media is
hashed and left unchanged. Recorded captures require an approximate recording
date and seasonal context. See [ingestion](docs/INGESTION.md) and
[catalog records](docs/RECORDKEEPING.md).

Use browser-supported H.264/AAC MP4, preferably with faststart. Importing another
codec/container does not transcode it. Complete recordings can remain intact at
fixed broadcast/source anchors, locally or from explicitly enabled HTTPS sources;
see [complete blocks](docs/COMPLETE_BLOCKS.md).

## Broadcast rules

The server owns the clock and publishes a rolling 72-hour guide. Tuning, refreshing,
changing channels or closing the app never restarts a show. Unwatched channels need
only metadata and a time check, not background video decoding. Published rows and
anchors cannot be edited, reset or rerolled through the app. New imports affect
unpublished programming; file repair can restore the same source without moving it.

Time Machine chooses a separate persistent historical context; it does not rewind
Channel Surf. Each context has fixed timing and resumes its clock on return. See
[Time Machine](docs/USING_TIME_MACHINE.md). Back up the station database, its
sibling `contexts/` directory and original media. These rules protect application
behavior; the server owner still controls the files and database.

## Server-only tools

Viewer frontends do not expose ingestion, source repair or research tools. Use
the CLI (`python -m retro_tv --help`) or a separate maintenance process:

```sh
python -m retro_tv --db data/my-station.sqlite serve --admin --port 8788
```

The admin process is loopback-only. Open `/server-manager`, `/research` or
`/block-editor` there. See [broadcast/server setup](docs/BROADCAST_SETUP.md),
[period research](docs/PERIOD_RESEARCH.md) and the [optional companion](docs/COMPANION.md).
The companion detects boundary candidates and exports reviewed spans; automatic
show/ad identification and historical dating are not implemented.

Historical evidence is independent of owned media. Supported source-specific
adapters, saved HTML and reviewed JSON can populate listings. Unknown history
stays unknown. Recommendations link to eBay, Internet Archive and YouTube searches;
they are not verified listings or automatic acquisitions.

## Development and documentation

```sh
python -m unittest discover -s tests -v
```

Browser checks use separately installed Playwright/Chromium. Runtime screenshots
are generated locally with `scripts/capture-runtime.cjs`; see the
[capture instructions](docs/PERIOD_RESEARCH.md#local-runtime-screenshot-library).
Obsolete screenshots are no longer shipped in the repository.

- [Documentation index](docs/README.md)
- [Current capabilities and limitations](docs/STATUS.md)
- [Remaining work](docs/DEVELOPMENT_ROADMAP.md)
- [Corrected branding and UI assets](docs/BRANDING_INTEGRATION.md)

The current delivery adapter is a browser player, not a native TV APK or HLS/IPTV
server. Physical TV remote testing, broader history adapters and automatic
identification remain work ahead. The guide uses supplied blue SD component shells
and a bundled pixel font; manager/server pages use warm cassette-style controls.
Original family artwork is on the optional About screen; startup remains the guide.
