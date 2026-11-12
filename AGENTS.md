# Repository instructions for coding agents

## Current sources of truth

Read `README.md`, `docs/STATUS.md` and the relevant workflow guide from
`docs/README.md`. Accepted decisions are in `docs/adr/` (0001–0008). The original
canon and conversation handoff are in `docs/archive/` for historical context;
they do not override later user direction, delivered stack choices or ADRs.
`docs/DEVELOPMENT_ROADMAP.md` lists remaining work, not completed milestones.

## Product invariants

- Prepared libraries work independently of analysis, restoration, AI and GPUs.
  Current stack: Python 3.11+, SQLite, stdlib HTTP and browser JavaScript.
- Keep archival files unchanged. Segments normally reference source time spans;
  cuts and approved same-timeline presentation derivatives are optional.
- Preserve published broadcasts, anchors and the rolling 72-hour horizon. No
  reset/reroll/skip/restart flow. Separate Time Machine destinations are allowed;
  they never reset Channel Surf or rewrite existing contexts.
- Startup: PIP guide → TV MASTER MANAGER → Time Machine, Channel Surf, Block Party,
  Manage Broadcasts. Viewer surfaces never expose file/research/ingestion tools.
  Those belong to CLI or the explicit loopback-only admin console.
- Reception layouts scope region/provider/tier/channels. Services, dated station
  history and provider channel positions are separate identities. Do not invent
  Rochester lineup facts or treat personal assignments as historical evidence.
- History is independent of media availability. Unknown coverage remains unknown;
  named missing-episode claims require sourced identities. Preserve provenance
  internally; viewer uncertainty is a small hover/focus note.
- Health standards affect assessment, not broadcast timing. Meters use actual
  library/manifest data. Simulation belongs only to explicit Test UI.
- Complete local/opt-in remote recordings retain original source/broadcast anchors.
- Use supplied Corrected Branding v2 marks and Textless UI v1 shells; see
  `docs/BRANDING_INTEGRATION.md`. Keep guide/admin themes separate, runtime text
  in the DOM, artwork unchanged and source-pack demo values out of real screens.

## Engineering and maintenance

Favor small, inspectable vertical slices and deterministic synthetic fixtures.
Run checks appropriate to the change; no copyrighted footage is needed in tests.
Record material product/architecture changes in an ADR. Existing accepted ADRs
already supersede the original implementation order; no extra approval is needed
to follow them. Report changes, validation and material remaining limits.

Keep setup/route instructions aligned with the CLI/server. Runtime screenshots
stay in ignored local output directories, not committed as stale UI fixtures.
