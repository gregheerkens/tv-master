# Keep a complete block together

A recording can be an entire broadcast block, including programs, commercials and
bumpers. It does not need to be analyzed or cut before TV MASTER can use it.
This applies to an ordinary local file and an explicitly enabled remote video,
including a direct Internet Archive media URL.

On the server's `/block-editor`, check **This is a complete block**, select the
channel, bracket the recording, then identify one known airing inside it. You can
select an imported airing or enter its date/time with a timezone offset. The editor
shows the calculated broadcast bracket before saving. Streaming is a separate
opt-in checkbox. It is not enabled by the viewer frontend.

For example, if Power Rangers starts at 9:00 AM, 30 minutes into a 90-minute source:

```text
Source:           00:00 ───────── 00:30 ─────────────────── 01:30
Broadcast:      8:30 AM         9:00 AM                   10:00 AM
                               known airing
```

This is illustrative arithmetic, not a historical claim about a particular airing.
Tuning at 9:10 joins the recording at 40:00. The whole block remains together and
its source/broadcast offsets stay fixed across future contexts. If the source
bracket starts at 5:00 instead of 0:00, the broadcast bracket starts at 8:35, with
the known airing still anchored at 9:00. Contradictory known points are rejected.
Only this block's actual date/channel bracket is used; it is not silently repeated
on another date as a generic filler block. WHO filters may exclude it, not move it.

CLI templates:

```sh
python -m retro_tv --db data/station.sqlite import-block my-block.json
python -m retro_tv --db data/station.sqlite attach-block-presentation local-copy.json
```

```json
{
  "complete_block": true,
  "title": "Fox Kids recording — replace with your own recording",
  "service_id": "YOUR_STATION_ID",
  "path": "/media/recordings/your-recording.mp4",
  "source_in_ms": 0,
  "source_out_ms": 5400000,
  "anchor": {
    "title": "Power Rangers — known episode if available",
    "aired_at": "1995-07-15T09:00:00-04:00",
    "source_offset_ms": 1800000
  },
  "seasonal": false,
  "tags": ["fox kids", "cartoon"]
}
```

Replace illustrative IDs/dates/titles with the recording's own context. Local media
is probed and hashed. Existing catalog sources can be referenced with `source_id`
instead of `path`; their originals remain unchanged. `anchor.airing_id` can replace
`aired_at`/title when the airing is already in the schedule database. Additional
`known_points` must agree with the same timeline. A direct `broadcast_start` and
optional matching `broadcast_end` are also supported.

For remote input replace `path` with:

```json
{
  "url": "https://archive.org/download/YOUR_ITEM/YOUR_VIDEO.mp4",
  "duration_ms": 5400000,
  "allow_remote": true
}
```

A direct playable file is required; an Archive details page is not a media source.
Remote video is retrieved by the player only while watched. Seek/range support and
codec compatibility depend on that server/player. No full video download, proxy
transcoder or background per-channel decoder is needed. The app stays usable
entirely locally with streaming disabled/absent.

Remote availability starts unknown, not healthy by assumption. Real playback
success/failure updates its status and flows into live meters. Remote identifiers
are labeled URL identities, not fabricated content checksums. An approved local
copy is preferred without marking the remote URL healthy merely because the local
copy played.

Optional local presentation request:

```json
{
  "block_id": "ID_RETURNED_BY_IMPORT",
  "path": "/media/local-or-restored-copy.mp4",
  "approved": true
}
```

The duration must match the original timeline within 50 ms. Approval asserts the
copy represents the same recording, not just a video of the same length. The
original source and fixed bracket are preserved. Approved local presentations can
serve downloaded streams or restored local recordings. The companion can optionally
produce reviewed virtual spans or physical cuts from local originals; none of that
is required to play an intact block. No new AI upscaler/downloader is included.

New blocks/presentations never reset an existing published guide. New Time Machine
contexts and unpublished airtime adopt them; published slots remain fixed. Mixed
recordings count as intact-block footage, not falsely as a known amount of program,
commercial or bumper inventory.
