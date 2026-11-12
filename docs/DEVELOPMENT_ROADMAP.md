# Remaining development work

The catalog, standalone composer, browser guide, Time Machine, viewer manager,
research staging and baseline companion already exist. See [STATUS](STATUS.md)
for delivered functionality; do not rebuild them from the original handoff plan.

1. **Validate a sourced historical block.** Combine a known period/channel listing
   with owned media, inspect episode matches, continuity gaps, anchors and source
   offsets, and retain a reproducible acceptance fixture.
2. **Test on a physical TV.** Check browser/wrapper D-pad focus, Guide/Back keys,
   numeric tuning, overscan, sound permissions and playback transitions. Use those
   results to choose the smallest TV wrapper; a native APK is not delivered yet.
3. **Broaden historical adapters.** Add a source at a time with cached fixtures,
   episode-title tests, midnight handling and clear unsupported cases. Historical
   station/provider/tier lookup needs sourced data, not assumed cable positions.
4. **Add reference-backed identification to the companion.** Test labeled examples
   and out-of-corpus unknowns, propose reviewable identities/dates, then prove the
   approved results import into the existing catalog. Keep it optional.
5. **Improve delivery and continuity where measured.** Evaluate a playout adapter,
   codec handling and campaign/repetition rules using actual gaps from validation.
6. **Optional local restoration workers.** Add source-preserving derivatives with
   reproducible settings and review, without making playback depend on a GPU.

Every slice must preserve fixed published timelines, server-only content tooling,
the prepared-library path, original media and explicit unknown historical coverage.
The [original design](archive/README.md) remains context, not a prerequisite order.
