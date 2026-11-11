"""Personal reception layouts select channels; they never reset a broadcast clock."""
import uuid
import hashlib
from datetime import date,datetime
from zoneinfo import ZoneInfo
from .records import utc_now


def active(db):
    return db.execute('SELECT l.* FROM broadcast_layout l JOIN broadcast_settings s ON s.active_layout=l.id WHERE s.id=1').fetchone()


def timezone(db):
    layout=active(db)
    return layout['timezone'] if layout else db.execute('SELECT timezone FROM state').fetchone()[0]


def channels(db,day):
    layout=active(db)
    mode=db.execute('SELECT mode FROM viewing_mode WHERE id=1').fetchone()
    if layout and not (mode and mode[0]=='representative'):
        return [dict(r) for r in db.execute('''SELECT s.*,e.channel FROM service s JOIN broadcast_layout_entry e ON e.service_id=s.id
            WHERE e.layout_id=? AND e.valid_from<=? AND e.valid_until>? ORDER BY length(e.channel),e.channel''',(layout['id'],day,day))]
    return [dict(r) for r in db.execute('''SELECT DISTINCT s.*,e.channel FROM service s JOIN lineup_entry e ON s.id=e.service_id
        JOIN lineup l ON l.id=e.lineup_id WHERE l.valid_from<=? AND l.valid_until>? ORDER BY length(e.channel),e.channel''',(day,day))]


def service_ids(db):
    layout=active(db)
    if not layout:return {r[0] for r in db.execute('SELECT id FROM service')}
    return {r[0] for r in db.execute('SELECT service_id FROM broadcast_layout_entry WHERE layout_id=?',(layout['id'],))}


def options(db):
    layouts=[]
    for row in db.execute('SELECT * FROM broadcast_layout ORDER BY created_at'):
        layouts.append({**dict(row),'channels':[dict(r) for r in db.execute('SELECT service_id,channel,valid_from,valid_until FROM broadcast_layout_entry WHERE layout_id=?',(row['id'],))]})
    layout=active(db)
    return {'active_layout':dict(layout) if layout else None,'layouts':layouts,'timezone':timezone(db),
        'providers':[dict(r) for r in db.execute('SELECT p.*,m.name region FROM provider p JOIN market m ON m.id=p.market_id')],
        'channels':[dict(r) for r in db.execute('SELECT id,name FROM service ORDER BY name')],
        'lineups':[{**dict(r),'channels':[dict(e) for e in db.execute('SELECT service_id,channel FROM lineup_entry WHERE lineup_id=?',(r['id'],))]} for r in db.execute('SELECT * FROM lineup')],
        'allowed_services':sorted(service_ids(db)),'configured':layout is not None}


def save(db,value):
    for field in ('name','region','timezone','provider_id','reception'):
        if not isinstance(value.get(field),str) or not value[field].strip():raise ValueError('Complete your broadcast '+field.replace('_',' '))
    ZoneInfo(value['timezone'])
    if value['reception'] not in ('antenna','cable'):raise ValueError('Choose antenna or cable')
    if not db.execute('SELECT 1 FROM provider WHERE id=?',(value['provider_id'],)).fetchone():raise ValueError('Choose a configured provider')
    entries=value.get('channels',[])
    if not isinstance(entries,list) or not entries or len(entries)>500:raise ValueError('Choose between 1 and 500 channels')
    known={r[0] for r in db.execute('SELECT id FROM service')};seen=[]
    for entry in entries:
        if entry['service_id'] not in known:raise ValueError('Unknown service')
        if not isinstance(entry['channel'],str) or not entry['channel'].strip():raise ValueError('Give each channel a number')
        a=date.fromisoformat(entry['valid_from']);b=date.fromisoformat(entry['valid_until'])
        if a>=b:raise ValueError('Channel end dates must follow start dates')
        for prior in seen:
            if (entry['channel']==prior['channel'] or entry['service_id']==prior['service_id']) and entry['valid_from']<prior['valid_until'] and entry['valid_until']>prior['valid_from']:
                raise ValueError('Overlapping channel numbers or duplicate services')
        seen.append(entry)
    ident=uuid.uuid4().hex
    provider=value['provider_id']
    with db:
        prior=db.execute('SELECT p.*,m.name region FROM provider p JOIN market m ON m.id=p.market_id WHERE p.id=?',(provider,)).fetchone()
        if prior['region'].casefold()!=value['region'].strip().casefold():
            market='personal-region:'+hashlib.sha256((value['region'].strip().casefold()+value['timezone']).encode()).hexdigest()[:16]
            db.execute('INSERT OR IGNORE INTO market VALUES (?,?,?)',(market,value['region'].strip(),value['timezone']))
            provider='personal-provider:'+hashlib.sha256((provider+market).encode()).hexdigest()[:16]
            db.execute('INSERT OR IGNORE INTO provider VALUES (?,?,?)',(provider,market,prior['name']))
        if value.get('provider_name','').strip() and value['provider_name'].strip()!=prior['name']:
            market=db.execute('SELECT market_id FROM provider WHERE id=?',(provider,)).fetchone()[0]
            provider='personal-provider:'+hashlib.sha256((value['provider_name'].strip()+market).encode()).hexdigest()[:16]
            db.execute('INSERT OR IGNORE INTO provider VALUES (?,?,?)',(provider,market,value['provider_name'].strip()))
        db.execute('INSERT INTO broadcast_layout VALUES (?,?,?,?,?,?,?,?)',(ident,value['name'].strip(),value['region'].strip(),value['timezone'],value['reception'],provider,value.get('tier','').strip(),utc_now()))
        for e in entries:db.execute('INSERT INTO broadcast_layout_entry VALUES (?,?,?,?,?)',(ident,e['service_id'],e['channel'].strip(),e['valid_from'],e['valid_until']))
        db.execute('INSERT INTO broadcast_settings VALUES (1,?) ON CONFLICT(id) DO UPDATE SET active_layout=excluded.active_layout',(ident,))
    return {'status':'Broadcast setup saved','id':ident}


def activate(db,value):
    if not db.execute('SELECT 1 FROM broadcast_layout WHERE id=?',(value['id'],)).fetchone():raise ValueError('Unknown broadcast setup')
    with db:db.execute('INSERT INTO broadcast_settings VALUES (1,?) ON CONFLICT(id) DO UPDATE SET active_layout=excluded.active_layout',(value['id'],))
    return {'status':'Broadcast setup selected. Your channels keep their clocks.'}


def home(db,now):
    from .health import timeline_health
    layout=active(db);zone=timezone(db);day=datetime.fromtimestamp(now/1000,ZoneInfo(zone)).date().isoformat()
    rows=channels(db,day);health=[]
    for row in rows:
        blocks=timeline_health(db,row['id'],now,now+72*3600000)
        playable=sum(b['playable_ms'] for b in blocks.values())
        health.append({**row,'playable_percent':round(100*playable/(72*3600000),1),'playable_ms':playable,'gap_blocks':sum(b['status']!='ready' for b in blocks.values())})
    return {'now_ms':now,'timezone':zone,'active_layout':dict(layout) if layout else None,'channels':health,
        'library':{'programs':db.execute('SELECT count(*) FROM program').fetchone()[0],
                   'recordings':db.execute('SELECT count(*) FROM source').fetchone()[0],
                   'complete_blocks':db.execute('SELECT count(*) FROM complete_block').fetchone()[0],
                   'identified_episodes':db.execute("SELECT count(*) FROM content WHERE kind='episode'").fetchone()[0]},
        'playable_percent':round(sum(r['playable_percent'] for r in health)/len(health),1) if health else 0}
