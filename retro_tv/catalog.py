"""Validated, transactional import shared by prepared libraries and companion output."""
import hashlib
import json
import math
import sqlite3
import subprocess
from datetime import date, time
from pathlib import Path


def connect(path):
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(Path(__file__).with_name('schema.sql').read_text())
    return db


def fingerprint(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                             'format=duration', '-of', 'json', str(path)],
                            check=True, capture_output=True, text=True)
    seconds = float(json.loads(result.stdout)['format']['duration'])
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('source duration must be positive')
    return round(seconds * 1000)


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def window(item):
    start, end = item['valid_from'], item['valid_until']
    if date.fromisoformat(start) >= date.fromisoformat(end):
        raise ValueError('valid_until must be later than valid_from (exclusive end)')
    return start, end


def services(item, known):
    values = item.get('services', [])
    if not isinstance(values, list) or any(v not in known for v in values):
        raise ValueError('services must be a list of known service IDs')
    return json.dumps(values)


def metadata(item):
    value = item.get('metadata', {})
    if not isinstance(value, dict):
        raise ValueError('metadata must be an object')
    for rule in value.get('dayparts', []):
        for key in ('start','end'):
            stamp = time.fromisoformat(rule[key])
            if stamp.strftime('%H:%M') != rule[key]:
                raise ValueError('daypart times must use HH:MM')
        if rule['start']==rule['end']:
            raise ValueError('daypart start and end must differ; omit rules for all-day')
        if any(type(day) is not int or not 0<=day<=6 for day in rule.get('weekdays', [])):
            raise ValueError('weekdays must be integers 0 through 6')
    return value


def import_library(db, document, base, *, verify_media=True):
    """Append catalog IDs. Duplicate IDs fail; sources are never overwritten or split.

    verify_media=False is solely for synthetic tests and the metadata-only example.
    """
    base = Path(base).resolve()
    if document.get('version') != 1:
        raise ValueError('library version must be 1')
    with db:
        known = {r[0] for r in db.execute('SELECT id FROM service')}
        for source in document.get('sources', []):
            path = (base / source['path']).resolve()
            duration = probe(path) if verify_media else source['duration_ms']
            integer(duration, 'duration_ms', 1)
            digest = fingerprint(path) if verify_media else source.get('sha256', 'synthetic')
            if verify_media and 'sha256' in source and source['sha256'] != digest:
                raise ValueError(f'source hash mismatch: {source["id"]}')
            db.execute('INSERT INTO source VALUES (?,?,?,?,?)',
                       (source['id'], str(path), duration, digest,
                        json.dumps(source['provenance'])))
        for asset in document.get('assets', []):
            start, end = window(asset)
            a = integer(asset.get('in_ms', 0), 'in_ms')
            row = db.execute('SELECT duration_ms FROM source WHERE id=?',
                             (asset['source_id'],)).fetchone()
            if row is None:
                raise ValueError('unknown source_id')
            b = integer(asset.get('out_ms', row[0]), 'out_ms', 1)
            if not a < b <= row[0]:
                raise ValueError('span must satisfy 0 <= in_ms < out_ms <= source duration')
            details = metadata(asset)
            if details.get('review_status') != 'approved':
                raise ValueError('only reviewed/approved assets enter the playout catalog')
            db.execute('INSERT INTO asset VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (asset['id'], asset['source_id'], asset['title'], asset['kind'],
                        a, b, start, end, services(asset, known), json.dumps(details)))
        for program in document.get('programs', []):
            start, end = window(program)
            parts = program['parts']
            if not isinstance(parts, list) or not parts:
                raise ValueError('program requires ordered asset IDs in parts')
            for part in parts:
                asset = db.execute('SELECT kind FROM asset WHERE id=?', (part,)).fetchone()
                if asset is None or asset[0] != 'program':
                    raise ValueError('program parts must reference program assets')
            db.execute('INSERT INTO program VALUES (?,?,?,?,?,?,?)',
                       (program['id'], program['title'], json.dumps(parts),
                        services(program, known), start, end,
                        json.dumps(metadata(program))))
