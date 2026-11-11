"""Append-only block composition and a server-owned, continuously running clock."""
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .records import Policy, backfill

HORIZON_MS = 72 * 60 * 60 * 1000
SLOT_MS = 30 * 60 * 1000


def wall_ms():
    return time.time_ns() // 1_000_000


def initialize(db, config, *, real_now=None):
    real_now = wall_ms() if real_now is None else real_now
    anchor = datetime.fromisoformat(config['historical_start'])
    if anchor.tzinfo is None:
        raise ValueError('historical_start needs an explicit UTC offset')
    ZoneInfo(config['timezone'])
    start, end = config['lineup']['valid_from'], config['lineup']['valid_until']
    if start >= end or not start <= anchor.astimezone(ZoneInfo(config['timezone'])).date().isoformat() < end:
        raise ValueError('historical start must be within lineup validity')
    with db:
        db.execute('INSERT INTO state VALUES (1,?,?,?,?,?)',
                   (real_now, int(anchor.timestamp()*1000), real_now,
                    config['timezone'], config.get('seed', 'retro-tv')))
        market = config['market']
        db.execute('INSERT INTO market VALUES (?,?,?)',
                   (market['id'], market['name'], config['timezone']))
        provider = config['provider']
        db.execute('INSERT INTO provider VALUES (?,?,?)',
                   (provider['id'], market['id'], provider['name']))
        lineup = config['lineup']
        db.execute('INSERT INTO lineup VALUES (?,?,?,?)',
                   (lineup['id'], provider['id'], start, end))
        for entry in config['channels']:
            db.execute('INSERT INTO service VALUES (?,?)', (entry['service_id'], entry['name']))
            db.execute('INSERT INTO lineup_entry VALUES (?,?,?)',
                       (lineup['id'], str(entry['number']), entry['service_id']))
        backfill(db)


def clock(db, real_now=None):
    state = db.execute('SELECT * FROM state WHERE id=1').fetchone()
    if state is None:
        raise ValueError('initialize this station first')
    real = max(state['high_water_ms'], wall_ms() if real_now is None else real_now)
    db.execute('UPDATE state SET high_water_ms=? WHERE id=1', (real,))
    return state['historical_anchor_ms'] + real - state['real_anchor_ms']


def eligible(row, service, local_day):
    allowed = json.loads(row['services'])
    return (not allowed or service in allowed) and row['valid_from'] <= local_day < row['valid_until']


def rank(seed, *values):
    return hashlib.sha256(':'.join(map(str, (seed, *values))).encode()).hexdigest()


def daypart_matches(row, local):
    """Optional local-time block rules; weekdays use Monday=0 through Sunday=6."""
    rules = json.loads(row['metadata']).get('dayparts', [])
    if not rules:
        return True
    clock = local.strftime('%H:%M')
    for rule in rules:
        begin, end = rule['start'], rule['end']
        if begin < end:
            inside = begin <= clock < end
            weekday = local.weekday()
        else:
            inside = clock >= begin or clock < end
            # Post-midnight portion belongs to the day the block began.
            weekday = (local.weekday()-(clock < end)) % 7
        if inside and weekday in rule.get('weekdays', list(range(7))):
            return True
    return False


def compose(db, service, start, state):
    """Freeze a whole block; final block may cross the visible horizon.

    Date eligibility covers the entire block, including a local midnight crossing.
    Source paths, hashes, offsets and display titles are snapshotted for playout.
    """
    zone = ZoneInfo(state['timezone'])
    day = datetime.fromtimestamp(start/1000, zone).date().isoformat()
    policy = Policy(db)
    assets = {r['id']: dict(r) for r in db.execute(
        'SELECT asset.*,source.path,source.sha256 FROM asset JOIN source ON source.id=asset.source_id')}
    candidates = []
    for row in db.execute('SELECT * FROM program ORDER BY id'):
        parts = [assets[p] for p in json.loads(row['parts'])]
        if not eligible(row, service, day) or not policy.allowed(row['id'],service,day,program=True) or not all(eligible(p, service, day) and policy.allowed(p['id'],service,day) for p in parts):
            continue
        duration = sum(p['out_ms']-p['in_ms'] for p in parts)
        length = max(SLOT_MS, math.ceil(duration/SLOT_MS)*SLOT_MS)
        if length > 12 * 60 * 60 * 1000:
            continue
        last_day = datetime.fromtimestamp((start+length-1)/1000, zone).date().isoformat()
        # Check all occupied minutes so a block cannot cross a forbidden daypart.
        daypart_ok = all(daypart_matches(row, datetime.fromtimestamp(t/1000, zone))
                         for t in range(start, start+length, 60000))
        daypart_ok = daypart_ok and daypart_matches(row, datetime.fromtimestamp((start+length-1)/1000, zone))
        if daypart_ok and eligible(row, service, last_day) and policy.allowed(row['id'],service,last_day,program=True) and all(eligible(p, service, last_day) and policy.allowed(p['id'],service,last_day) for p in parts):
            candidates.append((dict(row), parts, length))
    previous = db.execute('SELECT program_id FROM broadcast WHERE service_id=? ORDER BY start_ms DESC LIMIT 1',
                          (service,)).fetchone()
    alternate = [p for p in candidates if not previous or p[0]['id'] != previous[0]]
    if alternate:
        candidates = alternate
    candidates.sort(key=lambda p: rank(state['seed'], service, start, p[0]['id']))
    chosen = candidates[0] if candidates else None
    length = chosen[2] if chosen else SLOT_MS
    ident = rank(state['seed'], service, start)[:32]
    title = chosen[0]['title'] if chosen else 'Off air — library gap'
    db.execute('INSERT INTO broadcast VALUES (?,?,?,?,?,?,?)',
               (ident, service, start, start+length, title,
                chosen[0]['id'] if chosen else None, 'composed' if chosen else 'missing'))
    cursor = start

    def emit(asset, duration=None, reason=None):
        nonlocal cursor
        size = duration if duration is not None else asset['out_ms']-asset['in_ms']
        if size <= 0:
            return
        db.execute('INSERT INTO segment (broadcast_id,start_ms,end_ms,asset_id,title,kind,path,source_in_ms,source_hash,reason) VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (ident, cursor, cursor+size, asset['id'] if asset else None,
                    asset['title'] if asset else 'Station slate', asset['kind'] if asset else 'slate',
                    asset['path'] if asset else None, asset['in_ms'] if asset else 0,
                    asset['sha256'] if asset else None, reason))
        cursor += size

    def fill(budget, opening=False):
        nonlocal cursor
        last_day = datetime.fromtimestamp((cursor+max(1,budget)-1)/1000, zone).date().isoformat()
        pool = [a for a in assets.values() if a['kind'] != 'program'
                and eligible(a, service, day) and eligible(a, service, last_day)
                and policy.allowed(a['id'],service,day) and policy.allowed(a['id'],service,last_day)]
        if opening:
            pool = [a for a in pool if a['kind'] in ('bumper','station_id')]
        index, last = 0, None
        while budget > 0:
            fitting = [a for a in pool if a['out_ms']-a['in_ms'] <= budget]
            alternatives = [a for a in fitting if a['id'] != last]
            if alternatives:
                fitting = alternatives
            if not fitting:
                if not opening:
                    emit(None, budget, 'No eligible whole spot fits the remaining break')
                return budget
            fitting.sort(key=lambda a: rank(state['seed'], service, cursor, index, a['id']))
            asset = fitting[0]
            emit(asset)
            budget -= asset['out_ms']-asset['in_ms']
            last, index = asset['id'], index+1
            if opening:
                return budget
        return 0

    if not chosen:
        emit(None, length, 'No approved program matches this service and historical date')
    else:
        parts = chosen[1]
        remaining = length - sum(p['out_ms']-p['in_ms'] for p in parts)
        opening_budget = min(remaining, 15000)
        unused = fill(opening_budget, opening=True)
        remaining -= opening_budget-unused
        # Breaks between manually divided acts, plus final continuity to the slot boundary.
        for index, part in enumerate(parts):
            emit(part)
            budget = remaining // (len(parts)-index)
            fill(budget)
            remaining -= budget
    assert cursor == start+length


def extend(db, *, real_now=None):
    """One writer transaction; concurrent requests cannot generate different futures."""
    db.execute('BEGIN IMMEDIATE')
    try:
        now = clock(db, real_now)
        state = db.execute('SELECT * FROM state WHERE id=1').fetchone()
        for row in db.execute('SELECT id FROM service ORDER BY id').fetchall():
            service = row[0]
            tail = db.execute('SELECT MAX(end_ms) FROM broadcast WHERE service_id=?', (service,)).fetchone()[0]
            cursor = tail if tail is not None else state['historical_anchor_ms']
            # Preserve elapsed airtime during shutdown, too. No replay or restart.
            while cursor < now+HORIZON_MS:
                compose(db, service, cursor, state)
                cursor = db.execute('SELECT MAX(end_ms) FROM broadcast WHERE service_id=?', (service,)).fetchone()[0]
        db.commit()
        return now
    except Exception:
        db.rollback()
        raise


def guide(db, now):
    end = now+HORIZON_MS
    channels = []
    zone = ZoneInfo(db.execute('SELECT timezone FROM state').fetchone()[0])
    day = datetime.fromtimestamp(now/1000, zone).date().isoformat()
    for service in db.execute('SELECT service.*,lineup_entry.channel FROM service JOIN lineup_entry ON service.id=lineup_entry.service_id JOIN lineup ON lineup.id=lineup_entry.lineup_id WHERE lineup.valid_from<=? AND lineup.valid_until>? ORDER BY length(lineup_entry.channel),lineup_entry.channel', (day,day)):
        entries = []
        for item in db.execute('SELECT * FROM broadcast WHERE service_id=? AND end_ms>? AND start_ms<? ORDER BY start_ms',
                               (service['id'], now, end)):
            entry = dict(item)
            entry['visible_start_ms'] = max(now, item['start_ms'])
            entry['visible_end_ms'] = min(end, item['end_ms'])
            # Do not expose scheduling beyond the three-day horizon.
            entry['end_ms'] = min(end, item['end_ms'])
            entries.append(entry)
        channels.append({**dict(service), 'entries': entries})
    return {'now_ms': now, 'until_ms': end, 'timezone': str(zone), 'channels': channels}


def tune(db, service, now):
    row = db.execute('SELECT segment.*,broadcast.service_id FROM segment JOIN broadcast ON broadcast.id=segment.broadcast_id WHERE broadcast.service_id=? AND segment.start_ms<=? AND segment.end_ms>?',
                     (service, now, now)).fetchone()
    if row is None:
        raise ValueError('service is not scheduled')
    result = dict(row)
    result.pop('path')
    result['offset_ms'] = row['source_in_ms']+now-row['start_ms']
    result['remaining_ms'] = row['end_ms']-now
    result['now_ms'] = now
    return result
