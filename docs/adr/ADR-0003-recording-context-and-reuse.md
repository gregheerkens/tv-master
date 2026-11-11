# ADR 0003: Require source context and infer conservative continuity reuse

Status: accepted from the user's explicit 2026-11-11 ingestion requirements.

Ripped-media intake selects a folder; recorded-media intake selects one file and
requires an approximate-or-exact recording date and explicit seasonal answer.
Seasonal recordings additionally name the American holiday and holiday year.
Preserve supplied precision; file modification time is not recording evidence.

Recordings suggest estimated ±2-year reuse for ads/continuity only. Seasonal
reuse follows the named holiday in each target year, provisionally 30 days before
through the holiday. Evidence can replace the bracket, including annual campaign
restrictions. Per-segment corrections can identify evergreen ads inside seasonal
recordings. Episode premieres and eligibility are never inferred from this rule.

Additive schema v3 preserves legacy unknown context and immutable published slots.
New library imports and companion jobs enforce context at their entry points.
No AI or upscaler dependency is introduced. The graphical form and automatic
recognition of dated campaign evidence are separate future milestones.
