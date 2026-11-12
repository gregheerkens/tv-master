"""Choose WHAT once. Then join fixed broadcasts using the existing composer/player."""
import hashlib
import json
import re
import sqlite3
import uuid
from urllib.parse import quote
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .catalog import connect
from . import broadcasts
from .records import utc_now
from .scheduler import extend, tune, wall_ms
from .health import timeline_health

RULE_KEYS=('tags','exclude_tags','content_ids','exclude_content_ids','continuity_tags')
BUILDER_KEYS=('years','months','networks','block_minutes','include_commercials','include_bumpers')
TEMPLATES={
    'saturday_morning':{'label':'Saturday morning','weekday':5,'time':'08:00'},
    'weekday_afternoon':{'label':'Weekday afternoon','weekday':1,'time':'16:30'},
    'late_night':{'label':'Late-night television','weekday':4,'time':'22:00'},
}


def normalize_rules(value,db):
    if not isinstance(value,dict) or set(value)-set(RULE_KEYS+BUILDER_KEYS):
        raise ValueError('unsupported selection rule; timing and playback controls are not customizable')
    result={}
    for key in RULE_KEYS:
        values=value.get(key,[])
        if not isinstance(values,list) or len(values)>200 or any(not isinstance(v,str) or not v.strip() for v in values):
            raise ValueError(f'{key} must be a list of nonempty strings')
        result[key]=sorted(set(v.strip().casefold() if key in ('tags','exclude_tags','continuity_tags') else v.strip() for v in values))
    if any(key in value for key in BUILDER_KEYS):
        from .block_party import DURATIONS
        duration=value.get('block_minutes',30)
        if type(duration) is not int or duration not in DURATIONS:raise ValueError('Block duration must be 15, 30, 60 or 90 minutes')
        result['block_minutes']=duration
        for key in ('include_commercials','include_bumpers'):
            flag=value.get(key,True)
            if type(flag) is not bool:raise ValueError(f'{key} must be a boolean')
            result[key]=flag
        for key,low,high in (('years',1,9999),('months',1,12)):
            values=value.get(key,[])
            if not isinstance(values,list) or len(values)>200 or any(type(v) is not int or not low<=v<=high for v in values):raise ValueError(f'invalid {key} selection')
            result[key]=sorted(set(values))
        values=value.get('networks',[])
        if not isinstance(values,list) or len(values)>200 or any(not isinstance(v,str) or not v.strip() for v in values):raise ValueError('invalid network selection')
        result['networks']=sorted(set(v.strip().casefold() for v in values))
    for ident in result['content_ids']+result['exclude_content_ids']:
        if not db.execute('SELECT 1 FROM content WHERE id=?',(ident,)).fetchone():raise ValueError('unknown content selection')
    return result


def save_recipe(db,value):
    if not isinstance(value.get('name'),str) or not value['name'].strip():raise ValueError('give this selection a name')
    service=value['service_id']
    if not db.execute('SELECT 1 FROM service WHERE id=?',(service,)).fetchone():raise ValueError('unknown channel')
    rules=normalize_rules(value.get('rules',{}),db)
    ident=uuid.uuid4().hex
    with db:db.execute('INSERT INTO channel_recipe VALUES (?,?,?,?,?)',
        (ident,value['name'].strip(),service,json.dumps(rules,sort_keys=True),utc_now()))
    return {'id':ident,'name':value['name'].strip(),'service_id':service,'rules':rules}


def destination(value,zone,real_now=None):
    kind=value.get('destination_type','specific')
    if kind not in ('specific','date','today'):raise ValueError('Unknown destination choice')
    if kind!='specific' and value.get('template'):raise ValueError('Choose a destination type or a legacy template, not both')
    if kind=='today':
        year=value.get('year')
        if type(year) is not int or not 1900<=year<=2100:raise ValueError('Choose a year from 1900 to 2100')
        current=datetime.fromtimestamp((wall_ms() if real_now is None else real_now)/1000,zone)
        try:stamp=current.replace(year=year,tzinfo=None,microsecond=0)
        except ValueError:raise ValueError('February 29 does not exist in that year; choose a leap year or a specific date')
        if value.get('destination'):stamp=datetime.fromisoformat(value['destination'])
        value={**value,'destination':stamp.isoformat()}
    elif kind=='date':
        try:day=date.fromisoformat(value['destination'])
        except (ValueError,KeyError,TypeError):raise ValueError('Choose a specific date')
        value={**value,'destination':day.isoformat()+'T00:00'}
    template=value.get('template')
    if template:
        if template not in TEMPLATES:raise ValueError('unknown period template')
        year=value['year'];month=value.get('month',7)
        if type(year) is not int or type(month) is not int:raise ValueError('year and month must be integers')
        first=date(year,month,1);preset=TEMPLATES[template]
        day=first+timedelta(days=(preset['weekday']-first.weekday())%7)
        stamp=datetime.fromisoformat(f'{day}T{preset["time"]}')
    else:
        raw=value.get('destination')
        if not isinstance(raw,str):raise ValueError('choose a historical date and time')
        stamp=datetime.fromisoformat(raw)
    if stamp.tzinfo is None:
        stamp=stamp.replace(tzinfo=zone)
        # Reject nonexistent spring-forward times instead of silently moving the destination.
        checked=datetime.fromtimestamp(stamp.timestamp(),zone)
        if checked.replace(tzinfo=None)!=stamp.replace(tzinfo=None):raise ValueError('that local time does not exist in this timezone')
    return stamp.astimezone(zone)


def normalize_request(db,value,*,real_now=None):
    if not isinstance(value,dict):raise ValueError('expected a viewing selection')
    allowed={'mode','service_id','rules','recipe_id','destination','template','year','month','block_id','destination_type'}
    if set(value)-allowed:raise ValueError('timing controls, seeds, skips and rerolls are not supported')
    mode=value.get('mode','representative')
    if mode not in ('representative','historical','surfing'):raise ValueError('unknown viewing mode')
    saved_block=None
    if value.get('block_id'):
        from .playlists import get
        saved_block=get(db,value['block_id'])
        if set(value)-{'block_id'}:raise ValueError('Tune a saved block by its ID')
        value=saved_block['selection'];mode='representative'
    service=value.get('service_id');rules=value.get('rules',{})
    if value.get('recipe_id'):
        recipe=db.execute('SELECT * FROM channel_recipe WHERE id=?',(value['recipe_id'],)).fetchone()
        if not recipe:raise ValueError('unknown saved selection')
        if 'service_id' in value or 'rules' in value:raise ValueError('choose a saved selection or custom rules, not both')
        service=recipe['service_id'];rules=json.loads(recipe['rules'])
    if not db.execute('SELECT 1 FROM service WHERE id=?',(service,)).fetchone():raise ValueError('choose a known channel')
    result={'mode':mode,'service_id':service,'rules':normalize_rules(rules,db)}
    if 'block_minutes' in result['rules'] and mode!='representative':raise ValueError('Custom block rules belong to Block Party')
    layout=broadcasts.active(db)
    if layout:result['layout_id']=layout['id']
    if service not in broadcasts.service_ids(db):raise ValueError('That channel is outside your broadcast setup')
    state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
    if not state:raise ValueError('initialize the station first')
    if mode=='surfing':
        if any(k in value for k in ('destination','template','year','month','destination_type')):raise ValueError('Channel Surfing uses the station clock; its time cannot be chosen')
    else:
        if mode=='historical' and value.get('template'):raise ValueError('historical lookup requires a specific destination')
        stamp=destination(value,ZoneInfo(broadcasts.timezone(db)),real_now)
        if mode=='historical' and service not in {c['id'] for c in broadcasts.channels(db,str(stamp.date()))}:
            raise ValueError('No dated lineup maps this channel at that destination; configure your broadcast setup')
        result['destination']=stamp.isoformat()
        result['template']=value.get('template')
        if value.get('destination_type')=='today':result['destination_type']='today';result['year']=value['year']
    if saved_block:result['playlist']={k:saved_block[k] for k in ('name','duration_minutes','items')}
    return result


def key_for(request):
    if request.get('destination_type')=='today':request={**request,'destination':request['destination'][:10]}
    return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def selection_name(db,request):
    saved=db.execute('SELECT name FROM channel_recipe WHERE service_id=? AND rules=? ORDER BY created_at DESC LIMIT 1',
        (request['service_id'],json.dumps(request['rules'],sort_keys=True))).fetchone()
    if saved:return saved['name']
    channel=db.execute('SELECT name FROM service WHERE id=?',(request['service_id'],)).fetchone()[0]
    if request['rules'].get('block_minutes'):return channel+' / '+str(request['rules']['block_minutes'])+' min block'
    if request['rules']['tags']:return channel+' / '+', '.join(request['rules']['tags'])
    if request['rules']['content_ids']:
        titles=[db.execute('SELECT title FROM content WHERE id=?',(ident,)).fetchone()[0] for ident in request['rules']['content_ids'][:2]]
        return channel+' / '+', '.join(titles)
    return channel


def options(db):
    state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
    if not state:raise ValueError('initialize the station first')
    tags=set()
    for row in db.execute('SELECT tags FROM content'):tags.update(t.casefold() for t in json.loads(row[0]))
    from .block_party import options as block_options
    return {'block_facets':block_options(db),'block_durations':[15,30,60,90],'timezone':broadcasts.timezone(db),'default_destination':datetime.fromtimestamp(state['historical_anchor_ms']/1000,ZoneInfo(broadcasts.timezone(db))).isoformat(),
        'channels':[dict(r) for r in db.execute('SELECT id,name FROM service ORDER BY name') if r['id'] in broadcasts.service_ids(db)],
        'tags':sorted(tags),'collections':[dict(r) for r in db.execute("""SELECT DISTINCT c.id,c.title,c.kind FROM content c
            LEFT JOIN program_content p ON p.content_id=c.id WHERE c.kind='series' OR
            (p.program_id IS NOT NULL AND c.parent_id IS NULL) ORDER BY c.title""")],
        'templates':[{'id':k,**v} for k,v in TEMPLATES.items()],
        'recipes':[{**dict(r),'rules':json.loads(r['rules'])} for r in db.execute('SELECT * FROM channel_recipe ORDER BY created_at DESC')],
        'contexts':[{k:r[k] for k in ('id','name','mode','created_at')} for r in db.execute('SELECT * FROM viewing_context ORDER BY created_at DESC LIMIT 30')]}


def build(db,request,real_now,*,composition_seed=None):
    """Copy metadata only; all videos remain references to their original files."""
    scratch=sqlite3.connect(':memory:');scratch.row_factory=sqlite3.Row
    try:
        db.backup(scratch)
        scratch.execute('PRAGMA foreign_keys=OFF')
        for name in ('broadcast_no_delete','segment_no_delete','context_no_delete','anchor_no_update','clock_no_rewind'):
            scratch.execute(f'DROP TRIGGER IF EXISTS {name}')
        if composition_seed:scratch.execute('UPDATE state SET seed=? WHERE id=1',(composition_seed,))
        if request['mode']=='surfing':
            ids=[r[0] for r in scratch.execute('SELECT id FROM broadcast WHERE service_id=?',(request['service_id'],))]
            for ident in ids:
                scratch.execute('DELETE FROM viewing_event WHERE segment_id IN (SELECT id FROM segment WHERE broadcast_id=?)',(ident,))
                scratch.execute('DELETE FROM broadcast_context WHERE broadcast_id=?',(ident,))
                scratch.execute('DELETE FROM segment WHERE broadcast_id=?',(ident,))
                scratch.execute('DELETE FROM broadcast WHERE id=?',(ident,))
        else:
            for table in ('viewing_event','broadcast_context','segment','broadcast'):
                scratch.execute(f'DELETE FROM {table}')
        state=scratch.execute('SELECT * FROM state').fetchone()
        if request['mode']!='surfing':
            zone=ZoneInfo(broadcasts.timezone(db));stamp=datetime.fromisoformat(request['destination'])
            midnight=stamp.replace(hour=0,minute=0,second=0,microsecond=0)
            origin=int(midnight.timestamp()*1000);selected=int(stamp.timestamp()*1000)
            # Compose from midnight, but join at the requested instant inside that timeline.
            scratch.execute('UPDATE state SET historical_anchor_ms=?,real_anchor_ms=?,high_water_ms=? WHERE id=1',
                (origin,real_now-(selected-origin),real_now))
            if request['mode']=='historical':scratch.execute("UPDATE channel_profile SET mode='historical'")
        if request['mode']=='representative':
            # Plausible period programming must not masquerade as an exact historical airing.
            scratch.execute("UPDATE channel_profile SET mode='custom' WHERE mode='historical'")
            base=scratch.execute('''SELECT l.* FROM lineup l JOIN lineup_entry e ON e.lineup_id=l.id
                WHERE e.service_id=? ORDER BY l.valid_from DESC LIMIT 1''',(request['service_id'],)).fetchone()
            layout=broadcasts.active(db)
            if layout:
                entries=[];seen_services=set();seen_channels=set()
                for row in scratch.execute('SELECT channel,service_id FROM broadcast_layout_entry WHERE layout_id=? ORDER BY valid_from DESC',(layout['id'],)):
                    if row['service_id'] in seen_services or row['channel'] in seen_channels:continue
                    entries.append(row);seen_services.add(row['service_id']);seen_channels.add(row['channel'])
                provider=layout['provider_id']
            else:
                if not base:raise ValueError('selected channel has no configured lineup')
                entries=scratch.execute('SELECT channel,service_id FROM lineup_entry WHERE lineup_id=?',(base['id'],)).fetchall();provider=base['provider_id']
            market=scratch.execute('SELECT market_id FROM provider WHERE id=?',(provider,)).fetchone()[0]
            scratch.execute('DELETE FROM lineup_entry');scratch.execute('DELETE FROM lineup')
            scratch.execute("INSERT OR REPLACE INTO provider VALUES ('context-personal',?,'Personal representative lineup')",(market,))
            scratch.execute("INSERT INTO lineup VALUES ('context-personal','context-personal','0001-01-01','9999-12-31')")
            for row in entries:scratch.execute("INSERT INTO lineup_entry VALUES ('context-personal',?,?)",tuple(row))
        scratch.execute('INSERT INTO viewing_mode VALUES (1,?) ON CONFLICT(id) DO UPDATE SET mode=excluded.mode',(request['mode'],))
        scratch.execute('INSERT INTO selection_rule VALUES (?,?) ON CONFLICT(service_id) DO UPDATE SET rules=excluded.rules',
                        (request['service_id'],json.dumps({**request['rules'],**({'playlist':request['playlist']} if 'playlist' in request else {})},sort_keys=True)))
        scratch.commit()
        # Reinstall the same immutable-schedule/anchor guards as the main station.
        scratch.executescript(Path(__file__).with_name('schema.sql').read_text())
        scratch.executescript(Path(__file__).with_name('manager.sql').read_text())
        now=extend(scratch,real_now=real_now)
        return scratch,now
    except Exception:scratch.close();raise


def summary(db,request,now):
    service=request['service_id']
    state=db.execute('SELECT timezone FROM state').fetchone()
    playing=tune(db,service,now)
    slots=db.execute('SELECT * FROM broadcast WHERE service_id=? AND start_ms<=? AND end_ms>?',(service,now,now)).fetchone()
    health=timeline_health(db,service,now,now+72*3600000)
    playable=sum(h['playable_ms'] for h in health.values())
    listed=db.execute('SELECT c.episode_title FROM content c JOIN historical_airing a ON a.content_id=c.id WHERE a.service_id=? AND a.start_ms<=? AND a.end_ms>?',(service,now,now)).fetchone()
    block=db.execute('SELECT known_points FROM complete_block WHERE service_id=? AND start_ms<=? AND end_ms>?',(service,now,now)).fetchone()
    points=json.loads(block[0]) if block else []
    return {'mode':request['mode'],'service_id':service,'timezone':broadcasts.timezone(db),'now_ms':now,'episode_title':listed[0] if listed else None,'block_anchor_title':points[0].get('title') if points else None,
        'resolved_selection':{k:v for k,v in request.items() if k not in ('layout_id','playlist')},'block_minutes':request['rules'].get('block_minutes'),'destination':request.get('destination'),'current_title':slots['title'],
        'current_segment':playing['title'],'current_kind':playing['kind'],'current_offset_ms':playing['offset_ms'],
        'current_status':health[slots['id']]['status'],'playable_percent':round(playable/(72*3600000)*100,1),
        'gap_blocks':sum(h['status'] in ('missing','partial','offline','unknown') for h in health.values()),
        'historical_evidence':slots['evidence'],'rules':request['rules'],
        'note':'Once tuned, the clock continues. Returning to the same selection resumes its existing timeline.'}


def context_path(main_db_path,context_id):
    if not re.fullmatch(r'[a-f0-9]{32}',context_id):raise ValueError('invalid viewing context')
    with connect(main_db_path) as db:
        row=db.execute('SELECT path FROM viewing_context WHERE id=?',(context_id,)).fetchone()
    if not row:raise ValueError('unknown viewing context')
    path=Path(row['path'])
    if not path.is_file():raise ValueError('viewing timeline is unavailable; it will not be reset automatically')
    return path


def preflight(main_db_path,value,*,real_now=None):
    real_now=wall_ms() if real_now is None else real_now
    with connect(main_db_path) as db:
        request=normalize_request(db,value,real_now=real_now)
        if request['mode']=='surfing' and not any(request['rules'].values()):
            scratch=sqlite3.connect(':memory:');scratch.row_factory=sqlite3.Row
            try:
                db.backup(scratch);now=extend(scratch,real_now=real_now)
                return {**summary(scratch,request,now),'context_id':None,'resuming':True}
            finally:scratch.close()
        existing=db.execute('SELECT * FROM viewing_context WHERE context_key=?',(key_for(request),)).fetchone()
        if existing:
            sync_catalog(main_db_path,existing['id'])
            with connect(context_path(main_db_path,existing['id'])) as session:
                now=extend(session,real_now=real_now)
                return {**summary(session,request,now),'context_id':existing['id'],'resuming':True}
        scratch,now=build(db,request,real_now)
        try:return {**summary(scratch,request,now),'context_id':None,'resuming':False}
        finally:scratch.close()


def launch(main_db_path,value,*,real_now=None):
    real_now=wall_ms() if real_now is None else real_now
    db=connect(main_db_path)
    try:
        request=normalize_request(db,value,real_now=real_now);key=key_for(request)
        if request['mode']=='surfing' and not any(request['rules'].values()):
            return {'context_id':None,'url':'/?channel='+quote(request['service_id']),'resuming':True}
        existing=db.execute('SELECT * FROM viewing_context WHERE context_key=?',(key,)).fetchone()
        if existing:return {'context_id':existing['id'],'url':'/?context='+existing['id'],'resuming':True}
        scratch,now=build(db,request,real_now)
        ident=uuid.uuid4().hex
        directory=Path(main_db_path).resolve().parent/'contexts';directory.mkdir(parents=True,exist_ok=True)
        path=directory/(ident+'.sqlite')
        try:
            target=sqlite3.connect(path)
            try:scratch.backup(target)
            finally:target.close()
            name=selection_name(db,request)+' / '+('Channel Surfing' if request['mode']=='surfing' else request['destination'][:16].replace('T',' '))
            try:
                with db:db.execute('INSERT INTO viewing_context VALUES (?,?,?,?,?,?,?)',
                    (ident,key,request['mode'],name,json.dumps(request,sort_keys=True),str(path),utc_now()))
            except sqlite3.IntegrityError:
                # Concurrent identical launches converge on one fixed timeline.
                row=db.execute('SELECT id FROM viewing_context WHERE context_key=?',(key,)).fetchone()
                if not row:raise
                path.unlink(missing_ok=True);ident=row[0]
            return {'context_id':ident,'url':'/?context='+ident,'resuming':False,
                    'preflight':summary(scratch,request,now)}
        except Exception:
            if not db.execute('SELECT 1 FROM viewing_context WHERE id=?',(ident,)).fetchone():path.unlink(missing_ok=True)
            raise
        finally:scratch.close()
    finally:db.close()


def context_info(main_db_path,ident):
    with connect(main_db_path) as db:
        row=db.execute('SELECT name,mode,request FROM viewing_context WHERE id=?',(ident,)).fetchone()
    if not row:raise ValueError('unknown viewing context')
    return {'id':ident,'name':row['name'],'mode':row['mode'],'service_id':json.loads(row['request'])['service_id']}


def sync_catalog(main_db_path,ident):
    """Share new catalog entries/repairs with an existing timeline, never its order.

    Run when refreshing the guide, not for every media byte-range request. Local
    context-specific additions remain; selection rules and published rows stay fixed.
    """
    path=context_path(main_db_path,ident)
    origin=connect(main_db_path);target=connect(path)
    try:
        info=origin.execute('SELECT mode FROM viewing_context WHERE id=?',(ident,)).fetchone()
        with target:target.execute('INSERT OR IGNORE INTO viewing_mode VALUES (1,?)',(info['mode'],))
        # Materialize elapsed/unwatched airtime with the previously pinned catalog
        # before adopting new material. A return visit cannot rewrite the past.
        extend(target)
        tables=['market','provider','service','source','source_ingest','content','asset','program',
                'asset_content','program_content','content_alias','network','station_history','affiliation_history',
                'eligibility_window','channel_profile','complete_block','historical_airing','airing_requirement','airing_override']
        if info['mode']!='representative':tables+=['lineup','lineup_entry']
        with target:
            for table in tables:
                columns=origin.execute(f'PRAGMA table_info({table})').fetchall()
                primary=[r['name'] for r in sorted(columns,key=lambda r:r['pk']) if r['pk']]
                names=[r['name'] for r in columns]
                present={tuple(r) for r in target.execute(f'SELECT {",".join(primary)} FROM {table}')}
                for row in origin.execute(f'SELECT * FROM {table}'):
                    if tuple(row[k] for k in primary) in present:continue
                    target.execute(f'INSERT INTO {table}({",".join(names)}) VALUES ({",".join("?" for _ in names)})',tuple(row))
                    if table=='channel_profile' and info['mode']=='historical':
                        target.execute("UPDATE channel_profile SET mode='historical' WHERE service_id=?",(row['service_id'],))
                    elif table=='channel_profile' and info['mode']=='representative' and row['mode']=='historical':
                        target.execute("UPDATE channel_profile SET mode='custom' WHERE service_id=?",(row['service_id'],))
            # These are user corrections/preferences, not broadcast-order inputs already published.
            for table in ('stream_source','block_presentation','source_location','recording_quality','quality_alert','content_preference','recording_preference','health_standard'):
                columns=origin.execute(f'PRAGMA table_info({table})').fetchall()
                names=[r['name'] for r in columns];mutable=[r['name'] for r in columns if not r['pk']]
                updates=','.join(f'{c}=excluded.{c}' for c in mutable)
                for row in origin.execute(f'SELECT * FROM {table}'):
                    target.execute(f'INSERT INTO {table}({",".join(names)}) VALUES ({",".join("?" for _ in names)}) ON CONFLICT DO UPDATE SET {updates}',tuple(row))
    finally:origin.close();target.close()
