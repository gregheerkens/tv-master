# Importing the Rochester research packet

The supplied `TV-Master-Rochester.zip` contains a standalone research browser,
a data JSON, a reference SQLite database, CSV exports and research helpers.
Its README describes that research tool. TV MASTER imports its data through the
server CLI. Bundled scripts and HTML are not executed by the importer.

```sh
python -m retro_tv --db data/my-station.sqlite import-rochester TV-Master-Rochester.zip
```

This imports the packet's full 1995–2003 range. For a smaller period:

```sh
python -m retro_tv --db data/my-station.sqlite import-rochester TV-Master-Rochester.zip \
  --from-date 2000-09-01 --through-date 2000-09-30
```

The canonical data JSON and reference `.sqlite` are also accepted. Prefer ZIP/JSON
for the additional episode inventory and display/reference metadata absent from
the reference SQLite tables. CSV files and HTML remain research/export artifacts;
use the canonical packet for import. The default imports estimates. Add
`--exclude-estimates` to reproduce the packet's unchecked Include estimates mode.

## Services and media

Default service IDs are `rochester:CBS`, `rochester:NBC`, `rochester:ABC`,
`rochester:PBS`, `rochester:FOX`, `rochester:CN`, `rochester:NICK`, `rochester:MTV`.
Add these services to your reception layout in Manage Broadcasts, using your own
channel assignments where cable positions remain unknown. The packet's local
station numbers are OTA positions. No historical cable positions are invented.

To use an existing TV MASTER service, pass `--channel-map mapping.json`:

```json
{"NICK":"my-nickelodeon-service", "CN":"my-cartoon-network-service"}
```

Unspecified services use their default IDs. Use the same mapping on subsequent
imports. Names and episode identities are matched using the catalog's normalized
titles. Existing ambiguities are retained as separate research identities. Media
can be linked using the existing `import-records` identity links. Reference episode
entries, acquisition targets and 167 continuity leads do not establish ownership.
The full original data document and citations are retained. The source README
identifies CC BY-SA for the
TVmaze-derived episode references. Redistributed reference data needs that attribution.

## Resolution and updates

The adapter matches the packet engine's priority, episode-title and rule-date
precedence. It retains weekday 3–9 PM and weekend 7–11 AM windows, inclusive rule
end dates, local New York offsets and original scheduled bounds. Clipped bounds
become airing start/end times; original bounds remain in provenance. Open intervals
stay unresearched. Other hours also remain unresearched.

Original evidence labels, source citations, region, run status and notes are
preserved. Dated rows become `schedule_exact`, recurring rules `seasonal`, and
optional reconstruction labels `inferred`. A named episode in a secondary listing
is preserved without claiming contemporary exact verification. No date is used as
a special application home date.

Repeat imports are idempotent. Changed/unselected packet rows can be replaced in
the requested date range when no published context references them. A conflict
with published evidence or another imported schedule aborts the transaction.
Published timelines retain their existing media and timing. Keep backups when
changing research packs. Other periods are retained until explicitly re-imported.

## Validation of the November 18 packet

- Exact interval/source-row parity with its supplied JavaScript resolver across
  all 26,296 station-days from 1995 through 2003.
- Full import produced 86,765 resolved airings, with 1,075 program records,
  700 source references and 167 continuity leads retained.
- A repeat full import inserted no duplicates.
- JSON and SQLite inputs, estimate removal, changed boundaries, transaction
  rollback and virtual media fallback have integration coverage.
