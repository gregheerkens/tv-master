# Conversation-to-Codex handoff context

**Status:** supplemental product context and clarified intentions, recorded 2026-11-11.  
**Priority:** Canonical Design v0.2 remains authoritative for settled architecture. This file captures useful conversation-level nuance, especially from discussion *after* v0.2. Do not silently turn suggestions into locked technical requirements.

## Product identity

This project is not a 'nostalgic shuffle playlist' and not an attempt to synthesize a generic past. It is a historically aware archive and playout suite. Ask: *For a given historical Rochester provider/channel/date/time, what was scheduled, do we have that material, and how can we recreate the broadcast from our archive with period-appropriate ad breaks?*

Users should be able to browse a historical grid/TV-guide time machine and understand **which missing programs, episodes, commercial reels, network promos, local station IDs, or other assets they should acquire** to make a particular slice of a year playable.

The owner wants historically recognizable '90s television, not infinite channel universality. Historical schedule data itself is comparatively tiny; optimize for precision, queryability, source attribution, and thoughtful completeness reports—not aggressively compressed JSON.

## Three parallel classes of input

1. **Clean programs/DVD rips:** Intended act/commercial breaks may be absent from the file, so the program-break detector must infer *where commercials belonged*. Frame black/fades, audio stings/silence, act structure, transcript transitions, and reviewable confidence can help.
2. **Commercial blocks/tapes:** Long files may contain many discrete ads, promotions, bumpers, and station IDs. Identify them as nondestructive spans. Individual commercial files are supported, but need not exist.
3. **Historical schedules:** Scraped TV Guides and other researched sources establish schedule/lineup evidence. Recurring grids and exceptions, per-airing metadata, provenance, and ambiguity should all be representable.

## Rochester / localization cautions

The personal reference provider is historic Rochester Time Warner Cable, with a mid-tier lineup approximately channel 3 to channel 68 **with gaps**, plus local OTA stations. Network service identity and cable channel numbers must not be conflated. The owner's example channel numbers and schedule illustrations in prior discussions are not verified historical claims. Market, provider, date and lineup are separate dimensions.

Network continuity, national ads, and Rochester-specific station/local commercials should be selectable in different contexts. Repeated ads can improve historical plausibility rather than hurt it; do not impose a blanket 'never repeat'.

## Restoration: the underlying motivation

A singular surviving recording of a station bumper, episode, local commercial, or other historical fragment may have **bad VHS tracking, dropouts, static, compression damage, poor chroma, and noise**. Restoration is chiefly about recovering archival legibility where no better source survives—not making all standard-definition video look like synthetic 4K.

Useful **conceptual** classes to keep distinct:

- **Preservation source:** untouched capture/rip, hash and provenance recorded.
- **Restored presentation derivative:** conservative correction, deinterlacing/IVTC as appropriate, denoise, chroma/deblocking/audio improvement, and possibly modest upscale.
- **Reconstructed/inferential derivative:** frame repair, temporal inpainting, or generated detail where actual samples are missing. Allowed in principle for damaged rare material, but must be explicitly labeled, provenance-tracked, and subject to human review.

Restoration is **optional for playout** and never an obstacle to ingesting or cataloging an imperfect source. For interlaced VHS, cadence and field order need to be treated deliberately, not run blindly through an image model. Retain the untouched full original capture (including any overscan/head-switch signal that may inform later repair). A presentation copy may mask defects in nominally invisible raster areas if documented.

A useful archive-level prioritization notion is **rarity/scarcity × source damage × importance to historical reconstruction**. This is an optimization idea, not a finalized scoring formula. A common pristine DVD episode needs little restoration; a unique badly tracked Rochester bumper may warrant frame-level effort.

## Local processing hardware and workflow

The user has discussed running local enhancement as queued or overnight jobs on an **NVIDIA RTX 5070 Ti with 16 GB VRAM**. Local-first is a strong preference; GPU model/capacity is a target, not a mandated dependency for ingest/catalog/schema. Prefer optional workers and a CPU/software fallback for core archive functionality.

A plausible restoration worker flow (not a canonical exact pipeline):

1. Inspect codec, scan type, field order, frame rate, and source quality.
2. Suggest an appropriate profile for clean animation DVD, live-action DVD, VHS, or badly degraded capture.
3. Render a few short before/after validation clips, with regions chosen to expose failure modes.
4. Require review or explicit approval for destructive/inferential steps.
5. Queue offline source-appropriate full-length processing, record model/tool versions and settings.
6. Make the approved derivative available for playout, or fall back to the original.

Do **not** promise benchmark speed, model quality, or 16 GB support without validating actual models and source-specific runtime. AI upscaling models, hardware performance, QTGMC-like processing, restoration profiles and containerization remain implementation research areas, not accepted hard dependencies.

## Ambiguities not to 'resolve' by assumption

- Language and frontend/backend frameworks.
- Whether SQLite is the long-term DB (initially plausible; not canonically fixed).
- Codec/container/transcode choices and storage layout.
- Exact IPTV/EPG playout integration.
- Available legally sourced historical schedule corpus or validated station/channel listings.
- Automated break-detector accuracy, dataset size, chosen ML models, or hardware throughput.
- Whether the original source or a corrected derivative is the best input for detection (record source-referenced timing regardless).
- Exact source matching when historical listings name only a program and not an episode.

## A testable end-to-end example (fictional data, not historical claims)

Historical guide: `Rochester / Time Warner Cable / 1995-07-18 / [Nickelodeon service assigned through lineup] / 16:30 Rocko's Modern Life`.

Archive: an intact DVD episode file with approved program break markers, and a long 1995 Nickelodeon commercial tape whose spans include ads, promos, and bumpers.

Composer: chooses the best program asset, inserts period/service-appropriate spans into act breaks within the allotted time, records substitutions if the exact historical program or episode is missing, and generates a deterministic playout manifest. Optional approved restoration derivative can supply presentation frames without changing source-based segment timestamps.

This demonstrates the object relationships without asserting that Rocko aired at that exact time on that historical date or that a particular cable channel number was in use.
