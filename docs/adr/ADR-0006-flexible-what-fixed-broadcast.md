# ADR 0006: Flexible WHAT; fixed broadcast friction and evidence-based health

Status: accepted from the user's 2026-11-11 implementation direction and manager
recommendation/research clarifications. Implements ADR 0005's first viewing slice.

Use the existing catalog/composer/player for Time Machine and filtered surfing.
Save reusable WHAT rules; keep clocks, seed selection, ordering, slot duration,
break budgets and the 72-hour guide out of those controls. Persist contexts and
resume identical choices. Compose from the day's origin before joining a requested
mid-program moment. Changing the entry minute does not change that day's seed.

Context databases contain metadata/manifests and share the original media paths.
Adopt new catalog entries/corrections without rewriting published rows. Materialize
elapsed/unwatched time using the prior catalog before adopting new material.
No new streaming stack, per-channel decoder, analyzer or upscaler is introduced.

Manager health is purpose-specific. User standards define footage/variety/repeat
targets and desired healthy-channel counts. Exact recreation also requires source
evidence. An unresearched period is unknown, never an invented list of missing
episodes. Specific episode acquisition targets derive from exact imported airings;
capacity recommendations remain distinct. External actions are explicit search
links, not claims that a product/tape was verified or instructions to purchase.

Public-source period pre-scraping remains a required next adapter milestone; no
arbitrary website scraper or automatic semantic identifier is falsely represented
as implemented. These additions preserve the canonical provenance, source-span,
continuous-clock and immutable-playout principles.
