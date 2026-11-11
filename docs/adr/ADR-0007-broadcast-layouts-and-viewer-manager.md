# ADR 0007: Broadcast setups and a viewer-first manager

Status: accepted from the user's November 11, 2026 direction.

The app opens as the PIP guide. TV MASTER MANAGER is a four-mode landing screen:
Time Machine, Channel Surf, Block Party and Manage Broadcasts. Small inline SVG
icons and cassette-era colors accompany modern forms and remote navigation.
Time Machine defaults to a specific historical destination; Block Party owns
representative templates. Both retain the same clock/composer/media foundation.

A saved reception layout defines region, timezone, antenna/cable, provider, tier,
channel membership/numbers and date validity. Multiple setups are supported;
switching is secondary and never resets the shared channel clocks. Existing
viewing contexts retain their setup, and new contexts include its identity in
their key. User-assigned maps do not become asserted historical cable facts.
Market eligibility follows the selected provider/region. A personal provider is
created when needed; imported station and affiliation history is not overwritten.

Default frontend routes contain no ingestion, organizing, ripping, research or
file-repair UI/API. Those tasks remain CLI/server operations. An explicitly
started `serve --admin`, restricted to loopback, enables maintenance consoles;
it is separate from the normal viewer server. It is not a general authentication
system or a remotely exposed administration product.

All live metrics derive from the catalog and current files/manifests. Isolated
`/test-ui` simulates population only after the user chooses it and never writes
catalog data or changes a guide. Simulated values never enter the live manager.

Use episode titles as identities rather than dropping them into annotations.
Unicode punctuation, segment separators, explicit aliases and numbered episode
labels normalize deterministically. Ambiguous identities are not guessed. Old
annotation-only imports migrate to identities without rewriting published rows.
Community source details remain accessible through small hover/focus flags.
Program-slot coverage, episode identification and playable footage stay separate.
Source-named episodes can drive gap lists even without independent verification;
this updates the prior over-restrictive exact-evidence gate at the user's request.

Next-day lookup resolves late slots. A different named midnight program implies
an end at 23:59 inclusive, stored as an exclusive midnight boundary to avoid a
one-minute hole. Matching continuation uses its next explicit boundary. Failed
or blank next-day lookups remain pending and can be retried from cached HTML.
