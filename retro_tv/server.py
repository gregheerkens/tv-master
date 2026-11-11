"""Local guide/player and same-origin station-manager endpoints."""
import json
import mimetypes
import re
import sqlite3
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .catalog import connect
from .scheduler import extend, guide, tune
from . import manager
from . import timelines
from . import recommendations
from . import research
from .health import resolve_path


def serve(database, host='127.0.0.1', port=8787):
    static = Path(__file__).with_name('static')

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, content_type='application/json', status=200):
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(payload)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            target = urlsplit(self.path)
            db = None
            try:
                context=parse_qs(target.query).get('context',[''])[0]
                global_route=target.path.startswith('/api/research') or target.path.startswith('/api/time-machine') or target.path=='/api/manager/health-standard'
                if context and target.path in ('/api/guide','/api/manager'):
                    timelines.sync_catalog(database,context)
                db=connect(timelines.context_path(database,context) if context and not global_route else database)
                if target.path == '/api/guide':
                    result=guide(db,extend(db))
                    if context:result['context']=timelines.context_info(database,context)
                    self.send(result)
                elif target.path=='/api/research':
                    self.send(research.overview(db))
                elif target.path=='/api/research/export':
                    self.send(research.export_bundle(db,parse_qs(target.query).get('batch',[''])[0]))
                elif target.path=='/api/time-machine/options':
                    self.send(timelines.options(db))
                elif target.path == '/api/tune':
                    service = parse_qs(target.query).get('service', [''])[0]
                    self.send(tune(db, service, extend(db)))
                elif target.path == '/api/manager':
                    query=parse_qs(target.query);standard=query.get('standard',['channel'])[0]
                    self.send(manager.dashboard(db,extend(db),standard,query.get('date',[None])[0],int(query.get('days',['3'])[0])))
                elif re.fullmatch(r'/media/\d+', target.path):
                    self.media(db, int(target.path.rsplit('/',1)[1]))
                elif target.path in ('/', '/app.js', '/style.css','/manager','/manager.js','/manager.css','/time-machine','/time-machine.js','/time-machine.css','/research','/research.js','/research.css'):
                    name='index.html' if target.path=='/' else 'manager.html' if target.path=='/manager' else 'time-machine.html' if target.path=='/time-machine' else 'research.html' if target.path=='/research' else target.path[1:]
                    path = static / name
                    self.send(path.read_bytes(), mimetypes.guess_type(path)[0] or 'text/plain')
                else:
                    self.send({'error': 'not found'}, status=404)
            except (ValueError, KeyError,sqlite3.Error) as error:
                self.send({'error': str(error)}, status=400)
            except (FileNotFoundError, PermissionError):
                self.send({'error': 'Published source is missing or unreadable; restore the file at its original path.'}, status=404)
            finally:
                if db is not None:db.close()

        def do_POST(self):
            # Local administrative routes accept same-origin JSON, never cross-site forms.
            origin=self.headers.get('Origin')
            expected='http://'+self.headers.get('Host','')
            if (origin and origin!=expected) or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send({'error':'Use same-origin JSON requests'},status=403)
            target=urlsplit(self.path)
            db=None
            try:
                context=parse_qs(target.query).get('context',[''])[0]
                global_route=target.path.startswith('/api/research') or target.path.startswith('/api/time-machine') or target.path=='/api/manager/health-standard'
                db=connect(timelines.context_path(database,context) if context and not global_route else database)
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2*1024*1024:raise ValueError('JSON body must be between 1 byte and 2 MB')
                value=json.loads(self.rfile.read(size))
                if not isinstance(value,dict):raise ValueError('JSON requests must be objects')
                routes={'/api/manager/assess':manager.assess,'/api/manager/attach':manager.attach_media,
                        '/api/manager/repair':manager.repair_source,'/api/manager/override':manager.set_override,
                        '/api/time-machine/recipe':timelines.save_recipe,
                        '/api/manager/health-standard':recommendations.save_standard,
                        '/api/research/create':research.create_batch,'/api/research/fetch':research.fetch_page,
                        '/api/research/sideload':research.sideload,'/api/research/accept':research.accept}
                if target.path=='/api/time-machine/preflight':self.send(timelines.preflight(database,value))
                elif target.path=='/api/time-machine/launch':self.send(timelines.launch(database,value))
                elif target.path=='/api/manager/import-plan':
                    manager.import_plan(db,value);self.send({'status':'Listings and requirements imported; published guide unchanged'})
                elif target.path in routes:self.send(routes[target.path](db,value))
                else:self.send({'error':'not found'},status=404)
            except (ValueError,KeyError,TypeError,OSError,sqlite3.Error,subprocess.CalledProcessError) as error:
                self.send({'error':str(error)},status=400)
            finally:
                if db is not None:db.close()

        def media(self, db, segment_id):
            # IDs resolve only snapshotted local files; no arbitrary filesystem paths or URLs.
            now = extend(db)
            row = db.execute('SELECT segment.path,segment.source_hash FROM segment JOIN broadcast ON broadcast.id=segment.broadcast_id WHERE segment.id=? AND segment.start_ms<=? AND segment.end_ms>?',
                             (segment_id, now, now)).fetchone()
            if row is None or row['path'] is None:
                self.send({'error': 'media is outside the current guide or is a slate'}, status=404)
                return
            resolved=resolve_path(db,row['path'],row['source_hash'])
            if not resolved:raise FileNotFoundError(row['path'])
            path = Path(resolved)
            with path.open('rb') as stream:
                size = path.stat().st_size
                first, last, status = 0, size-1, 200
                requested = self.headers.get('Range')
                if requested:
                    match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                    if not match or not any(match.groups()):
                        self.range_error(size)
                        return
                    left, right = match.groups()
                    if left:
                        first, last = int(left), min(int(right), size-1) if right else size-1
                    else:
                        first = max(0, size-int(right))
                    if first > last or first >= size:
                        self.range_error(size)
                        return
                    status = 206
                self.send_response(status)
                self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
                self.send_header('Content-Length', str(last-first+1))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Cache-Control', 'no-store')
                if status == 206:
                    self.send_header('Content-Range', f'bytes {first}-{last}/{size}')
                self.end_headers()
                if self.command == 'HEAD':
                    return
                stream.seek(first)
                remaining = last-first+1
                while remaining:
                    chunk = stream.read(min(256*1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def range_error(self, size):
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()

    stop = threading.Event()

    def maintain():
        while not stop.wait(30):
            with connect(database) as db:
                extend(db)

    with connect(database) as db:
        extend(db)
    thread = threading.Thread(target=maintain, daemon=True)
    thread.start()
    print(f'Retro TV: http://{host}:{port}', flush=True)
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    finally:
        stop.set()
