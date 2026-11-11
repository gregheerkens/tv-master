# Proposed development roadmap

This is an **implementation proposal**, not a replacement for the canonical v0.2 design. Keep milestones independently testable. Avoid building a streaming server before the data model and composition contract are proven.

## Milestone 0 — repository foundation (first Codex task)

- Read this repository's design material; inspect any existing code, if present.
- Select or recommend a small initial stack, noting that the stack is *not yet canonical*. Record consequential choices in `docs/adr/`.
- Establish a minimal module boundary for metadata/catalog, history, composer, analysis workers, and delivery adapters (these need not be separate services yet).
- Provide deterministic smoke tests and minimal tooling to run them; no copyrighted media required.

## Milestone 1 — metadata and virtual spans

Deliver a tiny end-to-end library operation:

- Register a source with path/hash/technical metadata (a stubbed probe is fine in unit tests).
- Register a `MediaSpan` against the source's timebase, with type and in/out timestamps.
- Validate bounds, identifier integrity, and ambiguity in units/timebases.
- Retrieve spans and original source provenance without generating extracted videos.

Acceptance example: a synthetic 10-minute reel can hold three separately addressed 30-second ad spans with no file splitting, and a source can hold multiple episode act boundaries.

## Milestone 2 — human-in-the-loop review and detection interfaces

- Add candidate markers/spans with source, confidence, evidence, and review status.
- Implement simple baseline detectors (e.g., conventional black/silence/scene detection) behind interfaces; do not integrate a heavyweight model unnecessarily.
- Make correction of candidates easy before spending effort on sophisticated model inference.

## Milestone 3 — historical guide normalization

- Build `Market`, `Provider`, `Service`, `Lineup`, `LineupEntry`, `Program`, `Episode`, `Airing` and provenance relationships.
- Support recurrence/templates and date-specific overrides while preserving evidence state.
- Start with *synthetic historical listings* to verify mapping logic, especially channel moves and missing episodes.

## Milestone 4 — coverage reporting

- Report fraction of known schedule that can be satisfied by available assets, distinguishing program-only and exact-episode availability.
- Prioritize missing acquisition targets by known/estimated airtime and historical importance, with transparent scoring.

## Milestone 5 — initial broadcast composer

- Build deterministic, testable act + commercial span manifest composition.
- Respect wall-clock slot budgets, repetition policy, period and locale affinity, and known original commercial blocks.
- No live streaming required; test against manifest JSON and synthetic fixtures.

## Milestone 6 — restoration queue and playout adapter

- Model `RestorationProfile`, `MediaDerivative`, reproducibility, and source timeline mapping.
- Add local offline worker/presets and preview/approval stages, only after representative sources are available.
- Evaluate existing playout software against manifest and wall-clock semantics; implement a delivery adapter rather than another media server unless necessary.

## Milestone 7 — first realistic channel evening

Reconstruct a **multi-hour summer-1995 Nickelodeon block** from legally held source files and documented schedule evidence. Evaluate temporal correctness, continuity/repetition, confidence reporting, and substitute handling. Expand later to evening WUHF and Toonami.

## Not first-pass work

- Training custom super-resolution models.
- Designing an elaborate retro EPG shell before data semantics work.
- Maintaining hundreds of services or all U.S. markets.
- Splitting every commercial into a physical MP4.
- Running all segments through an upscale worker automatically.
