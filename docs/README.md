# Documentation

These guides describe the current Python/SQLite/browser app. Start with the root
[README](../README.md); use [STATUS](STATUS.md) for implementation limits and
[the roadmap](DEVELOPMENT_ROADMAP.md) for remaining work.

## Watching and configuring

- [Guide controls and manager](GUIDE_AND_MANAGER.md)
- [Time Machine and persistent contexts](USING_TIME_MACHINE.md)
- [Reception layouts and server-only tools](BROADCAST_SETUP.md)
- [Viewing-mode semantics](PRODUCT_MODES.md)

## Preparing and researching a library (server only)

- [Ingestion requirements and defaults](INGESTION.md)
- [Catalog records, eligibility and quality](RECORDKEEPING.md)
- [Complete local/remote recording blocks](COMPLETE_BLOCKS.md)
- [Period research, sideloads and local screenshot capture](PERIOD_RESEARCH.md)
- [Optional companion detector](COMPANION.md)
- [Metadata sources and future enrichment](DATA_SOURCES.md)

## Design and development

- [Branding](BRANDING.md) and [asset integration](BRANDING_INTEGRATION.md)
- [Architecture decisions](adr/) record the evolution of requirements.
- [Original design and handoff](archive/README.md) are historical reference,
  not current setup instructions or an implementation checklist.

Current task instructions and later accepted ADRs take precedence over the original
handoff. Runtime screenshot galleries stay local and are not checked in; the old
pre-branding captures were removed because they no longer show the current app.
