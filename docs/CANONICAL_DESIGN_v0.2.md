# Retro TV Historical Broadcast Reconstruction Suite

**Canonical System Design v0.2**  
**Status:** Concept baseline / canonical architecture  
**Primary personal deployment:** Rochester, New York OTA and Rochester Time Warner Cable  
**Historical focus:** principally the 1990s through early 2000s  
**Date established:** 2026-08-24  
**Revised:** 2026-08-26

## 0. Purpose of this document

This document fixes the conceptual architecture of a home historical-television reconstruction system so that implementation can proceed without repeatedly redefining the project. It is intentionally more rigid about **domain boundaries, data semantics, and reconstruction behavior** than about programming languages, databases, machine-learning models, or streaming packages.

Future implementation documents may refine components, but should not silently contradict the canonical decisions in Section 14. A material departure should be recorded as an Architecture Decision Record (ADR) or a later revision of this document.

---

## 1. System purpose

The system reconstructs plausible historical television from legitimately acquired local media and historical schedule data. Given a simulated historical **market, provider, date, time, and channel**, it should determine what was scheduled, locate the best available program media, insert historically appropriate commercial/promotional material at the intended breaks, and serve the result as continuous pseudo-live television.

The system is therefore not merely a media player and not merely a playlist generator. It is an **archive-management and historical broadcast-composition system whose primary interface is television**.

### 1.1 Personal target

The software must remain generic enough to represent other markets and providers, but the reference deployment is unapologetically Rochester-centric:

- Rochester-area over-the-air television stations.
- Rochester Time Warner Cable historical lineups.
- Personal cable scope roughly the traditional mid-tier channel range of **3 through 68, with gaps**, not hundreds of modern services.
- Priority reconstruction targets:
  - Nickelodeon, approximately 1993-1996.
  - Cartoon Network / Toonami, approximately 1999-2002.
  - Evening WUHF FOX 31, approximately 1994-1999.

### 1.2 Non-goals

The canonical system is **not** required to:

- Model every North American market or cable provider.
- Reconstruct every day of every year with equal completeness.
- Physically split every source video into separate files.
- Replace mature media-server or IPTV software where existing playout can satisfy the delivery layer.
- Pretend uncertain historical information is exact.
- Guarantee a unique historically exact commercial sequence when the source evidence does not establish one.
- Transform period SD material into synthetic modern-HD imagery by altering framing, cadence, or invented visual detail as a default behavior.

---

## 2. Architectural principles

### 2.1 A suite, not a monolith

The system is a set of cooperating tools and services. A practical implementation may combine some components into one application initially, but their responsibilities remain conceptually separate.

### 2.2 Nondestructive media first

Original rips and captures are archival sources. Detection and editing should normally produce **metadata referencing time ranges**, not derivative video files.

A segment is a virtual span:

```text
source_file + in_timestamp + out_timestamp + semantic_type + metadata
```

Physical extraction remains supported for convenience, interchange, or performance, but is not the canonical representation.

### 2.3 History and media are independent datasets

The question **"what was broadcast?"** is separate from **"what media do I own?"**

Historical schedule records must exist even when the matching episode is missing. Media assets must be catalogable even if their exact historical airing is not yet known. Composition joins the two datasets at runtime or manifest-generation time.

### 2.4 Explicit uncertainty

Historical reconstruction must record provenance and confidence. The system should say that something is inferred, substituted, or missing rather than laundering an approximation into an apparent fact.

### 2.5 Rochester-centric data, generic machinery

Domain entities should support other markets, providers, stations, and lineups without redesign. The personal archive and tooling priorities, however, are optimized for Rochester-area OTA and Time Warner Cable.

### 2.6 Playout is downstream

The custom intellectual core is media analysis, archival metadata, historical scheduling, composition, and coverage analysis. Existing pseudo-live TV / IPTV software may be used for the final delivery layer if it exposes sufficient control.

### 2.7 Restoration is derivative and conservative

Cleanup, deinterlacing, and AI-assisted upscaling are presentation operations performed on derivatives, never replacements for archival sources. Enhancement should recover a cleaner and more watchable representation of the source without silently changing aspect ratio, content timing, original composition, or historical character.

---

## 3. High-level architecture

```text
                         HISTORICAL DATA
                  TV Guide / listings / research
                              |
                              v
                    +---------------------+
                    | Historical Schedule |
                    |      Database       |
                    +----------+----------+
                               |
                               |
                               v
+-------------+     +----------+----------+      +----------------+
| DVD / files | --> | Media Ingest &      | ---> | Archive Catalog |
| VHS captures|     | Analysis            |      | + Virtual Spans |
+-------------+     +----------+----------+      +--------+-------+
                               |                          |
                +--------------+-------------+            |
                |                            |            |
                v                            v            v
        +---------------+           +----------------+  +----------------+
        | Act / Break   |           | Spot / Block   |  | Restoration /  |
        | Detector      |           | Segmenter      |  | Upscale Cache  |
        +---------------+           +----------------+  +--------+-------+
                                                                  |
                               +----------------------------------+
                               |
                               v
                     +----------------------+
                     | Broadcast Composer   |
                     | + Contextual Ad Pool |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     | Playout Manifest /   |
                     | Live Stream Adapter  |
                     +----------+-----------+
                                |
                                v
                      TV / client / guide UI
```

---

## 4. Core domain model

The following vocabulary is canonical. Exact schema names may differ in code, but the concepts should remain recognizable.

### 4.1 Market

A geographic television market.

Example: `Rochester, NY`.

### 4.2 Provider

A distribution provider within a market.

Examples: Rochester Time Warner Cable; over-the-air broadcast may be represented as a special provider/delivery context where useful.

### 4.3 Service

The logical program service independent of a channel number or delivery path.

Examples: Nickelodeon, Cartoon Network, WUHF, WROC.

A service is **not inherently channel 31, 44, or any other number**.

### 4.4 Lineup

A historically bounded mapping of provider channel positions to services.

A lineup answers: "On this provider, during this period, what service did channel N carry?"

### 4.5 LineupEntry

A mapping within a lineup:

```text
lineup_id
channel_number
service_id
valid_from
valid_to
optional tier / notes / provenance
```

Channel number belongs here, not on Service.

### 4.6 Program

A series, movie, special, short, news program, interstitial program, or other scheduled title.

### 4.7 Episode

A specific installment of a Program when episodic identity is known.

### 4.8 Airing

A historical or reconstructed scheduled occurrence of a Program/Episode on a Service at a date and time.

An Airing may be exact, partially known, inferred from a recurring schedule, or unresolved at episode level.

### 4.9 MediaSource

An immutable or archival source file: DVD rip, VHS capture, downloaded capture, audio/video master, etc.

### 4.10 MediaSpan

A nondestructive virtual segment of a MediaSource, defined by in/out timestamps and semantic metadata.

Examples: episode act, commercial, bumper, station ID, promo, PSA.

### 4.11 BreakMarker

A point or narrow interval in program media at which a historical commercial break belongs. A marker may have a confidence score, detection evidence, and human-review status.

### 4.12 Campaign / Spot

A commercial or promotional creative and, optionally, the broader campaign identity that permits realistic repetition rules.

### 4.13 PlayoutManifest

An ordered, time-addressable description of what should play on a reconstructed channel. It references MediaSpans rather than requiring a pre-rendered continuous video.

### 4.14 RestorationProfile

A reproducible set of cleanup/enhancement operations and parameters appropriate to a class of sources, such as clean DVD SD, noisy VHS, or degraded off-air capture. The profile records tool/model versions and should be reusable across similar material.

### 4.15 MediaDerivative

A regenerable presentation copy derived from a MediaSource under a RestorationProfile. It retains explicit lineage to the source, is never archival truth, and should preserve content timing so MediaSpans remain valid across source and derivative representations.

---

## 5. Tool / component responsibilities

### 5.1 Media Ingest

**Purpose:** register source media and establish stable technical identity.

Responsibilities include:

- File hashing / duplicate detection.
- ffprobe-style technical inspection.
- Duration, streams, codecs, aspect ratio, frame rate, interlacing, audio, subtitles/CC.
- Source provenance and acquisition notes.
- Association with known Program/Episode when available.
- Creation of archival source records without modifying the media.

The ingest process should tolerate imperfect filenames and incomplete metadata.

### 5.2 Program Act / Break Detector

**Purpose:** find where commercials belonged in clean program masters such as DVD rips.

This is not ordinary commercial detection because the commercial content has already been removed. The detector searches for editorial evidence of an intended break.

Candidate signals include:

- Fade or cut to black.
- Sustained dark frames.
- Audio fade or silence.
- Musical sting.
- Scene boundary strength.
- Narrative transition.
- Subtitle/transcript discontinuity.
- Expected act count and running-time priors.
- Similar break locations in other episodes from the same production format.

Output is a set of BreakMarkers with confidence and review state. Human correction is expected and valuable.

### 5.3 Commercial Block / Spot Segmenter

**Purpose:** divide long VHS/commercial compilations into discrete virtual MediaSpans.

Candidate evidence includes:

- Black-frame and scene transitions.
- Silence / strong audio changes.
- Common spot-length priors such as 10, 15, 20, 30, and 60 seconds.
- Station/network bumpers between ads.
- Logos, OCR, speech/transcript, or model classification where useful.

The segmenter should distinguish at least:

- national advertisement
- local advertisement
- network promo
- local/station promo
- network/station ID
- bumper / interstitial
- PSA
- unknown

The original block may remain a single source file indefinitely.

### 5.4 Archive Catalog

**Purpose:** become the authoritative metadata store for owned media and virtual spans.

It should support human review and correction. No automated classifier is authoritative merely because it produced a high confidence score.

Useful metadata includes:

- Source file and time span.
- Content type.
- Program / episode.
- Advertiser / product / campaign.
- Duration.
- Exact capture date, approximate date, or valid date range.
- Service/network.
- Market and station locality.
- Source tape / source program.
- Seasonality or event relevance.
- Audience/context tags.
- Provenance.
- Confidence.
- Review state.

### 5.5 Historical Guide Engine

**Purpose:** determine what should be scheduled for a requested market/provider/date/channel/time.

Historical schedule representation should support:

- Recurring weekly schedules.
- Effective date ranges.
- Specials and marathons.
- One-off overrides.
- Local preemptions where known.
- Exact episode identity where known.
- Program-only identity when episode information is unavailable.
- Multiple source citations and conflicting evidence.

Recurring schedule templates plus exceptions are preferred for human comprehensibility, though explicit materialized Airings may be generated or stored because schedule data is trivially small by modern standards.

### 5.6 Broadcast Composer

**Purpose:** join historical schedule intent with available media and construct a plausible broadcast.

For each Airing, the composer:

1. Resolves the best available program media.
2. Determines intended break positions.
3. Computes available wall-clock time and break budget.
4. Selects contextually appropriate ads/promos/bumpers.
5. Applies repetition/campaign rules.
6. Inserts station/network continuity where appropriate.
7. Produces a PlayoutManifest and records substitutions or uncertainty.

### 5.7 Playout Adapter / Server

**Purpose:** expose the composed result as watchable pseudo-live television.

The adapter may be custom or may integrate an existing media/IPTV stack. It should ideally support:

- Continuous wall-clock channels.
- M3U/HLS or equivalent stream exposure.
- XMLTV/EPG or equivalent guide exposure.
- Seeking into the correct position when a viewer tunes in mid-program.
- Changing away and back without resetting the channel.
- Multiple simultaneously available reconstructed channels.

### 5.8 Media Restoration / Enhancement Pipeline

**Purpose:** create local-first, regenerable presentation derivatives for material that benefits from cleanup or upscaling.

Responsibilities include:

- Prefer source-appropriate cleanup before spatial upscaling: correct deinterlacing, denoise, deblocking/ringing reduction, chroma cleanup, mild stabilization, and related restoration as needed.
- Use AI-assisted super-resolution conservatively to recover legibility and perceived detail, not to invent a modern-HD aesthetic.
- Preserve source aspect ratio, composition, duration, and historical cadence by default. Do not stretch 4:3 to 16:9, crop for widescreen, or use motion interpolation as ordinary cleanup.
- Record source hash, RestorationProfile, tool/model versions, parameters, output technical metadata, and human approval state.
- Permit multiple derivatives from one source and allow playout to fall back to the archival source when no approved derivative exists.
- Processing should be offline-capable and local-first; cloud enhancement may exist as an optional extension but must not be required for the archive to function.

---

## 6. Historical schedule model

### 6.1 Lineups and schedules are separate

A historical lineup determines **where** a service appears. A service schedule determines **what** it airs.

Example conceptual path:

```text
Rochester, NY
  -> Time Warner Cable
      -> lineup effective 1995-07-18
          -> channel 44
              -> Nickelodeon
                  -> 16:30 airing
                      -> Rocko's Modern Life
```

If Nickelodeon moves from one cable channel to another, its schedule does not need to be duplicated.

### 6.2 Recurrence plus overrides

A network's ordinary weekday/weekend grid should be representable as a recurring schedule template with a validity range. Historical anomalies are explicit overrides.

Example:

```text
Nickelodeon / Summer 1995 / Weekdays
16:00  Rugrats
16:30  Rocko's Modern Life
17:00  Doug
```

Then:

```text
1995-07-04 -> Independence Day marathon override
```

An implementation may materialize this into individual Airings for query speed, provenance, or guide export.

### 6.3 Historical confidence states

At minimum, schedule and airing evidence should support the following concepts:

| State | Meaning |
|---|---|
| Exact | Contemporary evidence establishes the specific airing/episode. |
| Schedule-exact | The program slot is established, but episode identity is not. |
| Seasonal | A recurring schedule is established for the period. |
| Inferred | Best reconstruction from adjacent or incomplete evidence. |
| Substituted | Known scheduled content is unavailable; replacement media is being used. |
| Missing | No acceptable media/reconstruction is available. |

These are evidence/reconstruction states, not merely cosmetic UI labels.

---

## 7. Commercial and continuity model

### 7.1 Geographic / institutional levels

Commercial and continuity material should distinguish at least:

**National**
- Consumer advertising usable across many services/markets during an appropriate date range.

**Network / service**
- Nickelodeon promos and bumpers.
- FOX promos.
- Toonami continuity.

**Local / station / market**
- Rochester-area businesses.
- WUHF local promotions or IDs.
- Locally inserted advertising.

A spot can carry more than one applicable tag when appropriate.

### 7.2 Selection should be scored, not purely random

A candidate spot can be ranked using factors such as:

```text
historical date proximity
+ network/service affinity
+ market/station affinity
+ audience/context fit
+ seasonal/event fit
+ known-source affinity
- excessive recent repetition
- excessive advertiser repetition
```

Exact weights are implementation details and may vary by channel format.

### 7.3 Repetition is historically authentic

The system should **not** enforce "never repeat an ad." Real television campaigns repeated heavily.

Useful campaign controls may include:

- Campaign frequency class.
- Minimum repeat interval.
- Maximum impressions per simulated day or hour.
- Advertiser spacing.
- Creative rotation within one campaign.

The goal is plausible saturation, not maximal variety.

### 7.4 Known blocks should remain representable

When an original commercial block is known to belong to a specific program/date, the system should be able to preserve that block as an especially high-confidence composition rather than decomposing and randomizing it merely because it can.

---

## 8. Reconstruction and playout semantics

### 8.1 A channel is wall-clock state

A reconstructed channel exists independently of whether anyone is watching it.

If simulated time is 16:47:12 and a program began at 16:30:00, tuning in should enter 17 minutes and 12 seconds into the composed broadcast timeline, not restart the episode.

### 8.2 Manifest-first composition

The preferred output of composition is an ordered timeline of references:

```text
16:30:00.000  program_act_1
16:41:04.000  commercial_0042
16:41:34.000  promo_0017
16:41:49.000  commercial_0138
16:42:19.000  program_act_2
...
```

The manifest may later be rendered, transcoded, or streamed, but it is the canonical description of the reconstructed broadcast.

### 8.3 Runtime vs precomposed manifests

The architecture permits either:

- pre-generating a day/channel manifest; or
- resolving portions just before playout.

Determinism should be available. Given the same simulation seed, archive state, and schedule version, a reconstructed day should be reproducible when desired.

### 8.4 Break duration mismatch

DVD-master runtimes, syndication cuts, and historical broadcast slots will not always align perfectly. The composer must therefore tolerate:

- variable commercial load,
- short bumpers/IDs,
- optional filler,
- small schedule drift,
- alternate cuts of a program,
- explicit substitution or truncation rules where unavoidable.

The system should record what it did rather than hiding the discrepancy.

### 8.5 Restoration and playout selection

Composition references content identity and time, not a permanently preferred encoding. At playout, an approved MediaDerivative may satisfy a MediaSpan in place of its archival source so long as the derivative preserves the same content timeline. Restoration therefore improves presentation without contaminating segmentation, schedule evidence, or archival provenance.

---

## 9. Coverage and acquisition intelligence

A major purpose of the archive manager is to tell the program master **what to acquire next**.

Coverage reporting should be available by:

- market
- provider
- lineup
- year / month / date range
- service
- daypart
- program
- episode / season
- commercial context
- local/network/national continuity type

Representative measures:

```text
Known schedule coverage
Playable program coverage
Exact episode coverage
Period commercial coverage
Network promo/bumper coverage
Rochester-local commercial coverage
Station ID/continuity coverage
```

Acquisition reports should rank gaps by reconstruction value rather than merely list missing files. For example, acquiring one DVD season that fills 24 known prime-time airings should rank above an obscure show appearing once.

The report may suggest categories rather than exact products when evidence is incomplete:

```text
High value gap: WUHF, Fall 1995, weekday 19:00-20:00
High value gap: Nickelodeon summer 1995 promos
High value gap: Rochester local commercial material, 1994-1996
```

---

## 10. Data storage and interchange

### 10.1 Storage volume is not a design constraint for metadata

Historical schedule metadata is tiny compared with video. The system should prefer correctness, provenance, and queryability over aggressive compression.

A whole Rochester historical lineup/schedule corpus is expected to be modest by modern storage standards even if individual Airings are materialized.

### 10.2 Likely storage pattern

A relational database is a natural fit for canonical metadata because Market, Provider, Lineup, Service, Airing, MediaSource, MediaSpan, and provenance are relational concepts.

SQLite is sufficient for an initial single-user deployment; migration to another relational engine should not require changing the domain model.

JSON remains useful for:

- import/export,
- scraped schedule staging,
- manifests,
- debugging,
- reproducible fixtures,
- external tooling.

No particular database product is canonical at v0.2.

### 10.3 Media files remain outside the database

The database stores stable references, hashes, technical metadata, and time ranges. Large media files remain ordinary files in managed storage.

### 10.4 Restored media is disposable in the archival sense

Enhanced derivatives may consume substantial storage, but they are caches or presentation assets rather than irreplaceable masters. A derivative should be reproducible from its MediaSource plus RestorationProfile, and may therefore be deleted and regenerated without losing archival information.

---

## 11. Suggested internal identifiers and example schema surface

This section is illustrative, not a frozen SQL schema.

```text
Market
  id
  name
  timezone

Provider
  id
  market_id
  name

Service
  id
  name
  kind              # station, cable_network, etc.
  market_id?        # present for local stations where useful

Lineup
  id
  provider_id
  valid_from
  valid_to
  name

LineupEntry
  lineup_id
  channel_number
  service_id
  valid_from?
  valid_to?

Program
  id
  title
  kind

Episode
  id
  program_id
  season
  episode
  title

Airing
  id
  service_id
  start_time
  end_time
  program_id
  episode_id?
  evidence_state
  provenance_id

MediaSource
  id
  path
  hash
  duration
  technical_metadata

MediaSpan
  id
  source_id
  in_time
  out_time
  type
  metadata

BreakMarker
  id
  media_span_or_source_id
  timestamp
  confidence
  review_state

RestorationProfile
  id
  name
  operations
  parameters
  tool_model_versions

MediaDerivative
  id
  source_id
  restoration_profile_id
  path
  technical_metadata
  approved_for_playout

PlayoutManifest
  id
  market/provider/date/service context
  seed
  generated_at
  archive_version
```

---

## 12. First vertical slice

The first end-to-end implementation should reconstruct **one coherent multi-hour Nickelodeon block from summer 1995**.

A deliberately small corpus is sufficient:

- Several hours of program media.
- Correct or plausible act-break markers.
- Roughly dozens, not hundreds, of period commercials.
- A useful pool of Nickelodeon bumpers/promos/IDs.
- One historically researched schedule period.
- One lineup mapping for Rochester Time Warner Cable.
- One representative restoration profile and an approved derivative for at least one source type.

The vertical slice is successful when the system can:

1. Ingest the sources.
2. Review/accept virtual break and commercial segments.
3. Resolve a historical schedule.
4. Report missing media.
5. Generate and approve a local restoration derivative without invalidating source-based MediaSpan timing.
6. Compose plausible breaks.
7. Produce a deterministic day/channel manifest.
8. Tune into the reconstructed channel at the correct simulated wall-clock position.

The objective is not perfect automation. It is proving the complete data and reconstruction loop.

---

## 13. Development sequence

A sensible order is:

1. **Domain schema + archive catalog.** Establish identity, provenance, and virtual spans first.
2. **Manual segmentation/review UI.** Make the archive usable before automation is perfect.
3. **Program break detector.** Automate clean-master break suggestions.
4. **Commercial block segmenter.** Automate spot boundary suggestions and classification.
5. **Restoration/enhancement pipeline.** Establish reproducible local cleanup and derivative lineage before playout depends on it.
6. **Historical schedule importer/normalizer.** Convert scraped TV Guide and other listings into canonical entities.
7. **Coverage/acquisition reporting.** Make missing material visible early.
8. **Broadcast composer.** Join schedule, program media, contextual continuity, and approved presentation derivatives.
9. **Playout integration.** Serve manifests through an existing or custom pseudo-live layer.
10. **Specialized retro guide/UI.** Build presentation polish only after reconstruction semantics are stable.

Components may overlap in implementation, but dependencies should flow in approximately this direction.

---

## 14. Canonical decisions (v0.2)

The following are considered settled until deliberately revised:

1. **The project is a suite of cooperating tools/services, not one conceptual monolith.**
2. **Media segmentation is nondestructive by default.** Source files remain intact; virtual spans and markers are canonical.
3. **Historical schedule truth is independent of owned media availability.**
4. **Market, Provider, Lineup, Service, and channel-number mapping are distinct concepts.**
5. **Channel numbers belong to historical lineups, not intrinsically to networks/stations.**
6. **The personal reference scope is Rochester OTA + Rochester Time Warner Cable, roughly channels 3-68 with gaps.**
7. **The architecture remains generic enough to represent other markets/providers without redesign.**
8. **Priority personal eras are Nickelodeon 1993-1996, WUHF evenings 1994-1999, and Cartoon Network/Toonami 1999-2002.**
9. **Schedule recurrence plus exceptions is a first-class representation; materialized airings are permitted.**
10. **Historical provenance and uncertainty must be explicit.** Exact, schedule-exact, seasonal, inferred, substituted, and missing are meaningful states.
11. **Commercial/continuity metadata distinguishes national, network/service, and local/station context.**
12. **Commercial selection is contextual and may intentionally repeat campaigns.** Repetition is part of authenticity.
13. **Known original commercial blocks may be preserved as high-confidence sequences rather than randomized.**
14. **The canonical composition product is a time-addressable playout manifest, not necessarily a newly rendered video file.**
15. **Pseudo-live channels follow simulated wall-clock time and continue when nobody is watching.**
16. **Coverage/acquisition reporting is a core product feature, not an administrative afterthought.**
17. **Custom development should concentrate on reconstruction intelligence; the final streaming layer may use existing software.**
18. **The first vertical slice is a multi-hour summer-1995 Nickelodeon reconstruction.**
19. **Restoration and AI-assisted upscaling are nondestructive presentation processes.** Archival MediaSources remain authoritative.
20. **Restoration is local-first and offline-capable.** Cloud processing may be optional but cannot be required for core archive function.
21. **Approved derivatives must preserve source timeline semantics.** Aspect-ratio changes, widescreen crops, motion interpolation, and duration-changing enhancement are not default cleanup behavior.
22. **Enhancement should be conservative and source-appropriate.** Recover clarity and suppress defects without treating invented detail as historical truth.

---

## 15. Deliberately open decisions

These should not drift into assumptions before implementation evidence exists:

- Programming language(s) and application framework.
- Whether components are separate processes, modules in one codebase, or both.
- Exact relational database product beyond initial suitability of SQLite.
- Exact machine-learning models used for break detection or classification.
- Whether speech transcription is local, optional, or always enabled.
- Exact metadata vocabulary for audience/context tagging.
- Which existing playout package, if any, becomes the long-term delivery backend.
- Whether manifests are generated a day at a time, lazily, or hybrid.
- How aggressively alternate cuts/runtimes are normalized.
- Final retro-TV guide UX.
- Exact local restoration toolchain and AI model(s).
- Default RestorationProfiles for DVD, VHS, and off-air captures.
- Whether common derivatives are precomputed, generated on demand, or managed as a hybrid cache.
- Preferred derivative resolutions, codecs, and storage-retention policy.

These are implementation decisions, not project identity.

---

## 16. Decision-change protocol

To avoid architectural drift:

- Minor implementation choices may change freely if they do not violate Section 14.
- A change to a canonical decision should receive an **Architecture Decision Record (ADR)**.
- An ADR should state:
  - Context/problem.
  - Previous assumption.
  - Decision.
  - Consequences and trade-offs.
  - Migration effect, if any.
- When several ADRs materially alter the premise, issue a new canonical design revision (v0.2, v1.0, etc.).

Suggested ADR naming:

```text
ADR-0001-use-sqlite-for-initial-catalog.md
ADR-0002-playout-integration-choice.md
ADR-0003-materialize-airings-or-resolve-dynamically.md
```

An ADR records **why** a decision changed; this document records **what the system is**.

---

## 17. Glossary

**Airing** - a scheduled occurrence of a program on a service at a historical time.  
**BreakMarker** - intended transition point from program content to commercial/continuity material.  
**Composer** - engine that turns an Airing plus archive assets into a broadcast timeline.  
**Continuity** - promos, bumpers, IDs, PSAs, and related material around programs/ads.  
**Lineup** - historically bounded provider mapping from channel positions to services.  
**Market** - geographic TV market, e.g. Rochester, NY.  
**MediaSource** - original archival video/audio file.  
**MediaSpan** - semantic virtual segment of a MediaSource addressed by timestamps.  
**MediaDerivative** - regenerable presentation copy created from a MediaSource under a RestorationProfile.  
**PlayoutManifest** - ordered timeline of media spans representing a reconstructed channel.  
**Program master** - the user/curator operating the reconstruction archive and choosing acquisition priorities.  
**Provider** - distributor such as Rochester Time Warner Cable.  
**RestorationProfile** - versioned, reproducible cleanup/upscaling recipe for a class of source material.  
**Service** - logical station/network independent of provider channel number.  
**Spot** - discrete advertisement or promotional creative.  
**Virtual span** - nondestructive reference to a portion of a media source.

---

## 18. Canonical one-paragraph description

The Retro TV Historical Broadcast Reconstruction Suite is a Rochester-centric but generically modeled archive and composition system that combines historical television schedules with locally owned program media and period commercial/continuity material. It keeps source media intact, represents acts and spots as time-addressable virtual spans, distinguishes services from historical provider lineups, records historical provenance and uncertainty, reports acquisition gaps, and composes reproducible pseudo-live channel manifests in which period-appropriate national, network, and Rochester-local material is inserted at intended program breaks. A local-first restoration layer may create versioned, regenerable cleanup or AI-upscaled presentation derivatives while preserving source timing, framing, and archival provenance. The final delivery layer may use existing IPTV/pseudo-live software; the custom core exists to determine what should have aired, what archival material is available, how it should be presented, and how to reconstruct the most historically coherent broadcast possible.
