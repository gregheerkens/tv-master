import argparse
import json
import sqlite3
from pathlib import Path

from .catalog import connect, import_library
from .scheduler import initialize, extend, guide
from . import records
from .ingest import ingest_path, add_recording_arguments, arguments_context


def main():
    parser = argparse.ArgumentParser(description='Local period TV with a fixed rolling 72-hour guide')
    parser.add_argument('--db', default='data/station.sqlite')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create station once; simulation anchor cannot be reset')
    init.add_argument('config', type=Path)
    imp = sub.add_parser('import-library', help='Append reviewed sources, spans and ordered programs')
    imp.add_argument('manifest', type=Path)
    rips=sub.add_parser('ingest-rips',help='Register a ripped-media folder without running the analyzer')
    rips.add_argument('folder',type=Path)
    recording=sub.add_parser('ingest-recording',help='Register one recording with mandatory date/season context')
    recording.add_argument('file',type=Path)
    add_recording_arguments(recording)
    metadata = sub.add_parser('import-records', help='Import identities, channel history and eligibility windows')
    metadata.add_argument('manifest', type=Path)
    lookup = sub.add_parser('channels', help='Look up imported dated station/affiliation/lineup facts')
    lookup.add_argument('--market', required=True)
    lookup.add_argument('--provider', required=True)
    lookup.add_argument('--date', required=True)
    exclude = sub.add_parser('exclude', help='Exclude content or one recording from future composition')
    exclude.add_argument('id')
    exclude.add_argument('--recording', action='store_true')
    exclude.add_argument('--allow', action='store_true', help='Remove the future scheduling exclusion')
    exclude.add_argument('--note')
    favorite = sub.add_parser('favorite', help='Mark content as a favorite; does not reroll the guide')
    favorite.add_argument('id');favorite.add_argument('--remove',action='store_true')
    quality = sub.add_parser('quality', help='Assess a recording without excluding the content identity')
    quality.add_argument('asset_id');quality.add_argument('--score',type=int)
    quality.add_argument('--assessment',required=True)
    alert = sub.add_parser('alert', help='Attach a quality alert to a source or recording')
    alert.add_argument('id');alert.add_argument('--code',required=True);alert.add_argument('--details',required=True)
    target = alert.add_mutually_exclusive_group(required=True)
    target.add_argument('--asset');target.add_argument('--source')
    alert.add_argument('--severity',choices=['info','warning','error'],default='warning')
    stats = sub.add_parser('stats', help='Separate scheduled/actually aired counts from explicit viewing records')
    stats.add_argument('content_id')
    demo = sub.add_parser('demo', help='Create a self-contained station with generated public test patterns')
    demo.add_argument('--directory', type=Path, default=Path('data/demo'))
    sub.add_parser('guide', help='Append future blocks and print the current 72-hour guide')
    serve = sub.add_parser('serve')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', default=8787, type=int)
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.command == 'serve':
            from .server import serve
            serve(args.db, args.host, args.port)
            return
        with connect(args.db) as db:
            if args.command == 'init':
                initialize(db, json.loads(args.config.read_text()))
                print('Station initialized. Import a library before publishing the guide.')
            elif args.command == 'import-library':
                import_library(db, json.loads(args.manifest.read_text()), args.manifest.parent)
                print('Library imported; published programming is unchanged.')
            elif args.command in ('ingest-rips','ingest-recording'):
                context={'kind':'ripped'} if args.command=='ingest-rips' else arguments_context(args)
                path=args.folder if args.command=='ingest-rips' else args.file
                print(json.dumps({'source_ids':ingest_path(db,path,context),
                    'status':'Registered; content identification/approval still required'},indent=2))
            elif args.command == 'import-records':
                records.import_records(db,json.loads(args.manifest.read_text()))
                print('Catalog records imported. Published programming is unchanged.')
            elif args.command == 'channels':
                print(json.dumps(records.channel_lookup(db,args.market,args.provider,args.date),indent=2))
            elif args.command == 'exclude':
                records.set_preference(db,args.id,recording=args.recording,excluded=not args.allow,note=args.note)
                print('Future scheduling preference saved; published slots remain fixed.')
            elif args.command == 'favorite':
                records.set_favorite(db,args.id,not args.remove)
                print('Favorite preference saved.')
            elif args.command == 'quality':
                records.quality(db,args.asset_id,args.score,args.assessment)
                print('Recording quality assessment saved.')
            elif args.command == 'alert':
                records.alert(db,args.id,code=args.code,details=args.details,asset_id=args.asset,source_id=args.source,severity=args.severity)
                print('Quality alert recorded; no automatic content ban was applied.')
            elif args.command == 'stats':
                from .scheduler import clock
                print(json.dumps(records.content_stats(db,args.content_id,clock(db)),indent=2))
            elif args.command == 'demo':
                from .demo import create
                create(db, args.directory)
                print('Synthetic demo ready. Run: python -m retro_tv serve')
            elif args.command == 'guide':
                print(json.dumps(guide(db, extend(db)), indent=2))
    except (ValueError, KeyError, OSError, sqlite3.Error) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
