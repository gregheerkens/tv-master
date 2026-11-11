import argparse
import json
import sqlite3
from pathlib import Path

from .catalog import connect, import_library
from .scheduler import initialize, extend, guide


def main():
    parser = argparse.ArgumentParser(description='Local period TV with a fixed rolling 72-hour guide')
    parser.add_argument('--db', default='data/station.sqlite')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create station once; simulation anchor cannot be reset')
    init.add_argument('config', type=Path)
    imp = sub.add_parser('import-library', help='Append reviewed sources, spans and ordered programs')
    imp.add_argument('manifest', type=Path)
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
