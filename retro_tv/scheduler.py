"""Append-only block composition and a server-owned, continuously running clock."""
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .records import Policy, backfill
from . import broadcasts
from . import blocks
from .identities import key as title_key

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
    selection=db.execute('SELECT rules FROM selection_rule WHERE service_id=?',(service,)).fetchone()
    builder=json.loads(selection[0]) if selection else {}
    if builder.get('playlist'):
        from .playlists import compose as compose_playlist
        compose_playlist(db,service,start,state,builder['playlist']);return
    block_ms=builder.get('block_minutes',0)*60000
    block_end=(state['historical_anchor_ms']+((start-state['historical_anchor_ms'])//block_ms+1)*block_ms) if block_ms else None
    if not block_ms and blocks.compose(db,service,start,state):return
    zone = ZoneInfo(broadcasts.timezone(db))
    day = datetime.fromtimestamp(start/1000, zone).date().isoformat()
    policy = Policy(db)
    assets = {r['id']: dict(r) for r in db.execute(
        'SELECT asset.*,source.path,source.sha256 FROM asset JOIN source ON source.id=asset.source_id')}
    viewing_mode=db.execute('SELECT mode FROM viewing_mode WHERE id=1').fetchone()
    use_history=not viewing_mode or viewing_mode[0]!='representative'
    expected=db.execute('SELECT * FROM historical_airing WHERE service_id=? AND start_ms<=? AND end_ms>?',
                        (service,start,start)).fetchone() if use_history else None
    override=db.execute('SELECT * FROM airing_override WHERE airing_id=?',(expected['id'],)).fetchone() if expected else None
    following=db.execute('SELECT min(start_ms) FROM historical_airing WHERE service_id=? AND start_ms>?',(service,start)).fetchone()[0] if use_history else None
    next_block=db.execute('SELECT min(start_ms) FROM complete_block WHERE service_id=? AND start_ms>?',(service,start)).fetchone()[0]
    if block_ms:next_block=None
    if next_block:following=min(following,next_block) if following else next_block
    boundary=expected['end_ms'] if expected else min(start+SLOT_MS,following) if following else start+SLOT_MS
    if next_block:boundary=min(boundary,next_block)
    if block_ms:boundary=block_end
    historical_mode=use_history and policy.profiles.get(service,{}).get('mode')=='historical'
    def identity_matches(program_id,target):
        identity=policy.program_ids.get(program_id);seen=set()
        while identity and identity not in seen:
            if identity==target:return True
            seen.add(identity);identity=policy.parents.get(identity)
        return False
    candidates = []
    for row in db.execute('SELECT * FROM program ORDER BY id'):
        if expected:
            if start!=expected['start_ms']:continue
            if override:
                if row['id']!=override['program_id']:continue
            elif expected['content_id']:
                if not identity_matches(row['id'],expected['content_id']):continue
            elif title_key(row['title'])!=title_key(expected['title']):continue
        elif historical_mode:
            continue
        parts = [assets[p] for p in json.loads(row['parts'])]
        if not eligible(row, service, day) or not policy.allowed(row['id'],service,day,program=True) or not all(eligible(p, service, day) and policy.allowed(p['id'],service,day) for p in parts):
            continue
        duration = sum(p['out_ms']-p['in_ms'] for p in parts)
        length = expected['end_ms']-start if expected else max(SLOT_MS, math.ceil(duration/SLOT_MS)*SLOT_MS)
        if block_ms:
            continuity=builder.get('include_commercials',True) or builder.get('include_bumpers',True)
            length=math.ceil(duration/(15*60000))*(15*60000) if continuity else duration
            if start+length>block_end:continue
        if duration>length or (following and start+length>following):continue
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
    length = chosen[2] if chosen else boundary-start
    ident = rank(state['seed'], service, start)[:32]
    title = chosen[0]['title'] if chosen else 'Missing: '+expected['title'] if expected else 'Listings unavailable' if historical_mode else 'Off air — library gap'
    evidence=('substituted' if override else expected['evidence_state']) if chosen and expected else 'composed' if chosen else 'missing'
    db.execute('INSERT INTO broadcast VALUES (?,?,?,?,?,?,?)',
               (ident, service, start, start+length, title,
                chosen[0]['id'] if chosen else None, evidence))
    if expected:
        db.execute('INSERT INTO broadcast_context VALUES (?,?,?,?)',(ident,expected['id'],expected['evidence_state'],
            json.dumps({'listing':json.loads(expected['provenance']),'substitution':override['note'] if override else None})))
    needed=[dict(r) for r in db.execute('SELECT * FROM airing_requirement WHERE airing_id=?',(expected['id'],))] if expected else []
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
            def matches(a,r):return a['kind']==r['kind'] and (not r['content_id'] or policy.asset_ids.get(a['id'])==r['content_id'])
            fitting.sort(key=lambda a: (not any(r['duration_ms']>0 and matches(a,r) for r in needed),
                                        rank(state['seed'], service, cursor, index, a['id'])))
            asset = fitting[0]
            emit(asset)
            for requirement in needed:
                if requirement['duration_ms']>0 and matches(asset,requirement):
                    requirement['duration_ms']-=asset['out_ms']-asset['in_ms'];break
            budget -= asset['out_ms']-asset['in_ms']
            last, index = asset['id'], index+1
            if opening:
                return budget
        return 0

    if not chosen:
        reason='Missing required program: '+expected['title'] if expected else 'No historical listing for this time' if historical_mode else 'No approved program matches this service and historical date'
        emit(None, length, reason)
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
    from .health import timeline_health
    end = now+HORIZON_MS
    channels = []
    zone = ZoneInfo(broadcasts.timezone(db))
    day = datetime.fromtimestamp(now/1000, zone).date().isoformat()
    for service in broadcasts.channels(db,day):
        first_start=db.execute('SELECT min(start_ms) FROM broadcast WHERE service_id=? AND end_ms>?',(service['id'],now)).fetchone()[0]
        health=timeline_health(db,service['id'],first_start if first_start is not None else now,end)
        entries = []
        for item in db.execute('SELECT * FROM broadcast WHERE service_id=? AND end_ms>? AND start_ms<? ORDER BY start_ms',
                               (service['id'], now, end)):
            entry = dict(item)
            entry['health']=health.get(item['id'],{'status':'missing','reasons':['No segment metadata']})
            content=db.execute('''SELECT c.episode_title,c.description,c.original_air_date FROM content c
                  JOIN program_content p ON p.content_id=c.id WHERE p.program_id=?''',(item['program_id'],)).fetchone()
            context=db.execute('SELECT a.content_id,a.provenance FROM historical_airing a JOIN broadcast_context c ON c.airing_id=a.id WHERE c.broadcast_id=?',(item['id'],)).fetchone()
            if context:
                listed=db.execute('SELECT episode_title,description,original_air_date FROM content WHERE id=?',(context['content_id'],)).fetchone()
                if listed:content=listed
                entry['source_note']=json.loads(context['provenance']).get('source_episode_text','Imported listing')
            if item['evidence']=='recorded_block':
                entry['source_note']='Complete recording · original broadcast bracket'
                block=db.execute('SELECT known_points,start_ms,end_ms FROM complete_block WHERE service_id=? AND start_ms<=? AND end_ms>=?',(service['id'],item['start_ms'],item['end_ms'])).fetchone()
                if block:entry['block']={**dict(block),'known_points':json.loads(block['known_points'])}
            entry['content']=dict(content) if content else None
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
    result['remote']=blocks.stream(db,row['source_hash']) is not None and blocks.presentation(db,row['source_hash']) is None
    result['offset_ms'] = row['source_in_ms']+now-row['start_ms']
    result['remaining_ms'] = row['end_ms']-now
    result['now_ms'] = now
    return result
