# Repository instructions for coding agents

## Latest authorized scope

Use the supplied Corrected Branding v2 marks and Textless UI v1 component shells;
see `docs/BRANDING_INTEGRATION.md`. Keep guide/admin styles separate, values in
the DOM, original artwork unchanged, and sample/demo strings out of real screens.
Do not replace the corrected letterforms with a CSS imitation.

The latest user direction is documented in ADR 0007 and 0008. Default startup is
PIP guide → TV MASTER MANAGER → Time Machine, Channel Surf, Block Party, Manage
Broadcasts. Viewer frontends never serve file ingestion, ripping, organization or
research tools; CLI and an explicit loopback-only server console own those tasks.
Use active region/reception/provider/tier layouts to scope channels and eligibility.
Live meters use library/manifest data; simulation belongs only to explicit Test UI.
Source episode titles are usable identities with small hover/focus flags. Preserve
citations internally without repeatedly asking users to verify community listings.
Complete local/opt-in remote recordings keep their original bracket and timing.
Optional cuts/presentations never move their anchor or rewrite published rows.


Read `docs/PRODUCT_MODES.md` and ADR 0005 for the latest product direction:
**Time Machine** selects an independent historical reconstruction context;
**Channel Surfing** joins a fixed timeline that advances without background video
decoding. Time Machine sessions and saved WHAT selections now work; see ADR 0006
and `docs/USING_TIME_MACHINE.md`. The no-reset/no-
reroll rule below protects Channel Surfing and published entries; it must not be
interpreted as prohibiting the separately requested Time Machine destination flow.

User-adjustable health standards never change broadcast timing. Unknown historical
coverage must stay unknown. Named missing-episode recommendations require an identified episode from sourced
listings; do not invent inventory gaps from unresearched periods.

Read `docs/adr/ADR-0001-standalone-block-station.md` alongside the original canon.
The user explicitly prioritizes a standalone prepared-library station, optional
analysis/restoration, and an immutable rolling 72-hour guide. These newer user
requirements override the original suggested implementation order. Do not make
the scheduler depend on a video analyzer, upscaler or GPU. Do not introduce a
guide reset/reroll/edit feature. The original canon remains useful historical
context; read README and docs/STATUS.md for the actual implementation boundary.

This is a historical broadcast reconstruction suite. **Read `docs/CANONICAL_DESIGN_v0.2.md` and `docs/HANDOFF_CONTEXT.md` before planning or editing the project.** These files are the source of truth about project identity and requirements. Read `docs/DEVELOPMENT_ROADMAP.md` for the suggested order of work.

## Invariants (do not change silently)

- Suite of cooperating components; modularity matters more than process boundaries or microservices.
- Preserve raw/archive media unmodified. Episode acts, commercials, bumpers, station IDs, etc. are normally *virtual time spans* against an archival source. Physical extraction is optional.
- Historical schedule evidence is independent from whether the user owns the media. Missing assets must not erase scheduled airings.
- Model `Market`, `Provider`, `Lineup`, `LineupEntry`, and `Service` separately. A channel number is a position in a dated provider lineup, **not** an intrinsic service identity.
- Personal focus: Rochester NY OTA and Rochester Time Warner Cable, with historic occupied channel positions generally 3–68 with gaps. Generic core; Rochester-centric fixtures/data. Never invent or assert unverified lineup positions.
- Personal priority eras: Nickelodeon 1993–1996, evening WUHF/FOX 31 1994–1999, Cartoon Network/Toonami 1999–2002.
- Distinguish exact, schedule-exact, seasonal, inferred, substituted, and missing reconstruction/evidence states. Record provenance. Differentiate certainty of schedule information from substitution of playable media.
- Commercial and continuity selection should consider time period, network, locality, audience, and repetition. Known original commercial blocks can be kept together.
- Compose time-addressed, reproducible playout manifests, not necessarily rendered 24-hour media files. Virtual channel state tracks simulation wall-clock time even when nobody watches.
- Local-first restoration/upscaling creates traceable, regenerable presentation derivatives. Preserve the archival original, content timing, original aspect ratio, and appropriate cadence. No aggressive hallucinated detail as a default.
- Archive coverage and targeted acquisition gap reporting are first-class features.
- Prefer integrating suitable IPTV/pseudo-live servers to writing one from scratch; choice is not yet finalized.

## Engineering guidance

- The canonical domain model and user goals are fixed; implementation frameworks, database product, language, UI toolkit, local AI models, and playout package are not fixed yet.
- Favor simple, inspectable, testable code and explicit interfaces. Avoid speculative abstractions, premature microservices, unexplained AI dependencies, and generated boilerplate.
- Prefer deterministic tests with synthetic/mock media metadata. Do not need actual copyrighted TV content in tests.
- Use FFmpeg/ffprobe as integration candidates, not mandatory choices.
- Keep the source timeline canonical even if an approved restoration derivative is selected for playout.
- Build small vertical slices with a working demonstration/test, not a sweeping infrastructure scaffold.
- Never silently encode speculative historical data as fact; fixtures must be marked illustrative/synthetic unless independently sourced.

## Changes to decisions

If implementation requires a material change to Section 14 of the canon, **stop and explain the conflict**. Propose an Architecture Decision Record in `docs/adr/` using the template. Do not rewrite canon to match implementation by default.

When concluding a coding task, report: changed files, tests run, known gaps, and the next independently testable step.
