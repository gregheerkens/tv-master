"""Import the Rochester research packet without executing bundled scripts."""
import hashlib
import json
import sqlite3
import zipfile
from datetime import date,datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from .identities import show_key,episode_key,numbers
from .records import utc_now

ESTIMATES={'Reconstruction','Seasonal fallback','Rochester estimate','Rochester reconstruction','Reported start; estimated end'}
TABLES={'channels':'channel','airings':'historical_airing','rules':'schedule_rule','catalog':'program','assets':'commercial_asset','sources':'source','acquisitions':'acquisition_plan','episode_leads':'episode_lead'}


def load(path):
    path=Path(path)
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as archive:
            matches=[i for i in archive.infolist() if Path(i.filename).name=='TV-Master-Rochester-data.json']
            if len(matches)!=1 or matches[0].file_size>64*1024*1024:raise ValueError('Expected one Rochester data JSON up to 64 MB')
            return json.loads(archive.read(matches[0]))
    if path.suffix.lower() in ('.sqlite','.db'):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            doc={key:[dict(r) for r in db.execute('SELECT * FROM '+table)] for key,table in TABLES.items()}
        for rows in doc.values():
            for row in rows:
                for k,v in row.items():
                    if isinstance(v,str) and v[:1] in ('[','{'):
                        try:row[k]=json.loads(v)
                        except ValueError:pass
        doc['meta']={'timeline_id':'rochester-ny-east-1995-2003','timezone':'America/New_York','start':'1995-01-01','end':'2003-12-31'}
        return doc
    if path.suffix.lower()!='.json':raise ValueError('Choose the Rochester ZIP, canonical data JSON or reference SQLite database')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def resolve(doc,day,channel,include_estimates=True):
    weekday=date.fromisoformat(day).weekday();begin,end=(420,660) if weekday>=5 else (900,1260)
    dated=doc.get('_dated')
    rows=(dated.get((day,channel),[]) if dated is not None else [r for r in doc['airings'] if r['date']==day and r['channel']==channel])
    rules=doc.get('_rules',{}).get((weekday,channel),[]) if '_rules' in doc else doc['rules']
    rows=list(rows)+[r for r in rules if r['channel']==channel and r.get('priority',0)>0 and weekday in r['days'] and r['valid_from']<=day<=r['valid_to']]
    rows=[r for r in rows if r['start']<end and r['end']>begin and (include_estimates or r['evidence'] not in ESTIMATES) and (day!='2001-09-11' or r.get('date'))]
    # Stable sorts reproduce the packet's precedence and tie-breaking order.
    rows.sort(key=lambda r:r['id'])
    rows.sort(key=lambda r:r.get('valid_from',''),reverse=True)
    rows.sort(key=lambda r:bool(r.get('episode')),reverse=True)
    rows.sort(key=lambda r:r['priority'],reverse=True)
    points=sorted({begin,end,*[max(begin,r['start']) for r in rows],*[min(end,r['end']) for r in rows]})
    result=[]
    for a,b in zip(points,points[1:]):
        winner=next((r for r in rows if r['start']<=a and r['end']>=b),None)
        if result and result[-1]['source_row']==(winner or {}).get('id'):
            result[-1]['end']=b
        else:result.append({'start':a,'end':b,'source_row':(winner or {}).get('id'),'row':winner})
    return result


def import_packet(db,path,*,start=None,through=None,include_estimates=True,channel_map=None):
    doc=load(path)
    if not isinstance(doc,dict) or not isinstance(doc.get('meta'),dict) or any(not isinstance(doc.get(k),list) for k in ('channels','catalog','sources','airings','rules')):
        raise ValueError('Expected the full Rochester data packet; choose TV-Master-Rochester-data.json or its ZIP')
    meta=doc['meta'];packet=meta['timeline_id'];zone=ZoneInfo(meta['timezone'])
    first=date.fromisoformat(start or meta['start']);last=date.fromisoformat(through or meta['end'])
    if first>last or (last-first).days>3660:raise ValueError('Choose an inclusive range up to ten years')
    if first<date.fromisoformat(meta['start']) or last>date.fromisoformat(meta['end']):raise ValueError('Requested range lies outside the packet')
    payload=json.dumps(doc,ensure_ascii=False,sort_keys=True);digest=hashlib.sha256(payload.encode()).hexdigest()
    channels={c['id']:c for c in doc['channels']};mapping={c:'rochester:'+c for c in channels};mapping.update(channel_map or {})
    if set(mapping)!=set(channels) or any(not isinstance(v,str) or not v.strip() for v in mapping.values()) or len(set(mapping.values()))!=len(mapping):raise ValueError('Channel mapping must use distinct service IDs')
    for rows in (doc['airings'],doc['rules']):
        for r in rows:
            if r['channel'] not in channels or not 0<=r['start']<r['end']<=1440:raise ValueError('Invalid schedule interval or channel')
    sources={s['id']:s for s in doc['sources']}
    doc['_dated']={};doc['_rules']={}
    for r in doc['airings']:doc['_dated'].setdefault((r['date'],r['channel']),[]).append(r)
    for r in doc['rules']:
        for weekday in r['days']:doc['_rules'].setdefault((weekday,r['channel']),[]).append(r)
    existing={};parents={}
    for c in db.execute('SELECT * FROM content'):
        if c['kind']=='episode':continue
        existing.setdefault(show_key(c['title']),[]).append(c['id'])
    episode_ids={}
    for c in db.execute('SELECT * FROM content WHERE kind="episode"'):
        episode_ids.setdefault((show_key(c['title']),episode_key(c['episode_title'])),[]).append(c['id'])
    inserted=unchanged=updated=gaps=removed=0
    def identity(title,episode=''):
        key=show_key(title)
        if key not in parents:
            found=existing.get(key,[])
            ident=found[0] if len(found)==1 else 'listed-show:'+hashlib.sha256(key.encode()).hexdigest()[:24]
            db.execute("INSERT OR IGNORE INTO content(id,kind,title) VALUES (?,'series',?)",(ident,title));parents[key]=ident
        if not episode:return parents[key]
        ekey=(key,episode_key(episode));found=episode_ids.get(ekey,[])
        ident=found[0] if len(found)==1 else 'listed-episode:'+hashlib.sha256((key+':'+ekey[1]).encode()).hexdigest()[:24]
        n=numbers(episode)
        db.execute("INSERT OR IGNORE INTO content(id,kind,title,parent_id,episode_title,season_number,episode_number) VALUES (?,'episode',?,?,?,?,?)",(ident,title,parents[key],episode,n[0] if n else None,n[1] if n else None))
        episode_ids[ekey]=[ident]
        return ident
    with db:
        db.execute('INSERT INTO reference_packet VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET sha256=excluded.sha256,document=excluded.document,imported_at=excluded.imported_at',(packet,digest,payload,utc_now()))
        for c,service in mapping.items():
            db.execute('INSERT OR IGNORE INTO service VALUES (?,?)',(service,channels[c]['label']))
            db.execute("INSERT OR IGNORE INTO channel_profile(service_id,mode) VALUES (?,'historical')",(service,))
        catalog={p['id']:p for p in doc['catalog']}
        for p in doc['catalog']:identity(p['title'])
        for pid,inventory in doc.get('episode_inventory',{}).items():
            if pid not in catalog:continue
            for e in inventory.get('episodes',[]):
                ident=identity(catalog[pid]['title'],e['title'])
                # Reference metadata remains distinct from the evidence for an airing.
                db.execute('UPDATE content SET episode_metadata=coalesce(episode_metadata,?) WHERE id=?',(json.dumps({'packet':packet,'reference':e}),ident))
        day=first
        while day<=last:
            for channel,service in mapping.items():
                resolved=resolve(doc,day.isoformat(),channel,include_estimates)
                wanted={packet+':'+channel+':'+day.isoformat()+':'+str(s['start']):s for s in resolved if s['row']}
                prefix=packet+':'+channel+':'+day.isoformat()+':'
                for old in db.execute('SELECT a.* FROM historical_airing a JOIN packet_airing p ON p.airing_id=a.id WHERE p.packet_id=? AND p.airing_id>=? AND p.airing_id<?',(packet,prefix,prefix+'\uffff')).fetchall():
                    desired=wanted.get(old['id'])
                    new_end=int((datetime.combine(day,datetime.min.time(),zone)+timedelta(minutes=desired['end'])).timestamp()*1000) if desired else None
                    if not desired or old['end_ms']!=new_end:
                        if db.execute('SELECT 1 FROM broadcast_context WHERE airing_id=?',(old['id'],)).fetchone():raise ValueError('Updated research conflicts with a published airing: '+old['id'])
                        db.execute('DELETE FROM historical_airing WHERE id=?',(old['id'],));removed+=1
                for segment in resolved:
                    row=segment['row']
                    if not row:gaps+=segment['end']-segment['start'];continue
                    def stamp(minute):return int((datetime.combine(day,datetime.min.time(),zone)+timedelta(minutes=minute)).timestamp()*1000)
                    a,b=stamp(segment['start']),stamp(segment['end']);ident=packet+':'+channel+':'+day.isoformat()+':'+str(segment['start'])
                    evidence='inferred' if row['evidence'] in ESTIMATES else 'schedule_exact' if row.get('date') else 'seasonal'
                    provenance={'packet':packet,'source_row':row['id'],'source':sources.get(row.get('source'),{}),'original_evidence':row['evidence'],'region':row.get('region'),'run_status':row.get('run'),'scheduled_start':row['start'],'scheduled_end':row['end'],'original_row':row,'note':row.get('note'),'source_episode_text':row.get('episode'),'needs_check':True}
                    target=(service,identity(row['program'],row.get('episode','')),row['program'],a,b,evidence,json.dumps(provenance,sort_keys=True))
                    old=db.execute('SELECT service_id,content_id,title,start_ms,end_ms,evidence_state,provenance FROM historical_airing WHERE id=?',(ident,)).fetchone()
                    if old and tuple(old)==target:unchanged+=1;continue
                    if old:
                        if db.execute('SELECT 1 FROM broadcast_context WHERE airing_id=?',(ident,)).fetchone():raise ValueError('Updated research conflicts with a published airing: '+ident)
                        db.execute('DELETE FROM packet_airing WHERE airing_id=?',(ident,));db.execute('DELETE FROM historical_airing WHERE id=?',(ident,));updated+=1
                    else:inserted+=1
                    db.execute('INSERT INTO historical_airing VALUES (?,?,?,?,?,?,?,?)',(ident,*target))
                    db.execute('INSERT INTO packet_airing VALUES (?,?)',(ident,packet))
            day+=timedelta(days=1)
    return {'packet':packet,'sha256':digest,'from':str(first),'through':str(last),'inserted':inserted,'unchanged':unchanged,'updated':updated,'removed':removed,'unresolved_minutes':gaps,'services':mapping,'reference_programs':len(doc['catalog']),'reference_sources':len(sources),'continuity_leads':len(doc.get('assets',[])),'note':'Full original packet retained. Add the imported services to your personal broadcast layout. Cable positions remain unresolved.'}
