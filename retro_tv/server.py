"""Small local read-only guide/playback server. Administrative changes use the CLI."""
import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .catalog import connect
from .scheduler import extend, guide, tune


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
            db = connect(database)
            try:
                if target.path == '/api/guide':
                    self.send(guide(db, extend(db)))
                elif target.path == '/api/tune':
                    service = parse_qs(target.query).get('service', [''])[0]
                    self.send(tune(db, service, extend(db)))
                elif re.fullmatch(r'/media/\d+', target.path):
                    self.media(db, int(target.path.rsplit('/',1)[1]))
                elif target.path in ('/', '/app.js', '/style.css'):
                    path = static / ('index.html' if target.path == '/' else target.path[1:])
                    self.send(path.read_bytes(), mimetypes.guess_type(path)[0] or 'text/plain')
                else:
                    self.send({'error': 'not found'}, status=404)
            except (ValueError, KeyError) as error:
                self.send({'error': str(error)}, status=400)
            except (FileNotFoundError, PermissionError):
                self.send({'error': 'Published source is missing or unreadable; restore the file at its original path.'}, status=404)
            finally:
                db.close()

        def media(self, db, segment_id):
            # IDs resolve only snapshotted local files; no arbitrary filesystem paths or URLs.
            now = extend(db)
            row = db.execute('SELECT segment.path FROM segment JOIN broadcast ON broadcast.id=segment.broadcast_id WHERE segment.id=? AND segment.start_ms<? AND segment.end_ms>?',
                             (segment_id, now+72*3600000, now)).fetchone()
            if row is None or row['path'] is None:
                self.send({'error': 'media is outside the current guide or is a slate'}, status=404)
                return
            path = Path(row['path'])
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
