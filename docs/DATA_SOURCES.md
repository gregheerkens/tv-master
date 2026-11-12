# Metadata acquisition direction

Core playback and composition remain local and keyless. Neither an AI provider
nor network metadata access is required to populate the catalog: users can import
their own structured records and continue offline. Supported historical-listing adapters, saved HTML and reviewed JSON sideloads
already work; see [period research](PERIOD_RESEARCH.md). The general metadata and
station-directory providers below remain candidates, not integrated importers.

Recommended order:

1. User metadata, local sidecars and cached regional/history reference packs.
2. Source-specific structured public APIs, preferably keyless where appropriate.
3. Source-specific HTML/PDF import and OCR where structured data is absent.
4. Optional user-selected AI for extraction, matching and review suggestions.

Prefer a public API to scraping the same data when its terms and coverage fit.
An API is a data interface, not necessarily an AI service or a paid/keyed product.
Fetch/cache during setup or library enrichment, never on every tune or guide
refresh. Preserve source URLs, retrieval dates, identifiers and evidence states.

Candidate references researched on 2026-11-11:

- TVmaze's public API: https://www.tvmaze.com/api — show/episode metadata; public
  access is distinct from its premium user API. Retain required attribution and
  check the data license when designing distributable reference packs.
- World Radio History's Television Factbook archive:
  https://www.worldradiohistory.com/Television_Factbook_Page.htm — historical
  station-directory evidence; extracting scans is not the same as obtaining a
  ready-made dated cable lineup database.

Station affiliation, a provider's cable channel position, an episode premiere,
and a later local rerun are separate assertions. No one source should be assumed
to cover all four. Broadcast-channel directories alone cannot establish old cable
positions. Ordinary show databases cannot establish every local rerun date.

Commercials/bumpers are especially incomplete in general-purpose databases.
Keep unidentified material usable with user-reviewed descriptions and windows.
AI can suggest matches and extract dated evidence but must return unknown when
unsupported; an AI's confidence is not a historical citation.

An eventual “connect your AI” feature should offer provider/model selection and a
bounded enrichment job, independent of the station runtime. Record its proposed
changes for review and apply accepted facts only to catalog/future composition.
