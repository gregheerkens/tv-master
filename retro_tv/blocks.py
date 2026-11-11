"""Whole recordings, local or remote, anchored to their original broadcast time."""
import hashlib
import json
import uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from .catalog import fingerprint,probe,integer
from .ingest import validate_context
from .records import utc_now


def timestamp(value):
    stamp=datetime.fromisoformat(value)
    if stamp.tzinfo is None:raise ValueError('Broadcast anchors need a timezone offset')
    return round(stamp.timestamp()*1000)


def bracket(value):
    if value.get('complete_block') is not True:raise ValueError('Mark this recording as a complete block')
    a=integer(value.get('source_in_ms',0),'source_in_ms')
    b=integer(value['source_out_ms'],'source_out_ms',1)
    if b<=a:raise ValueError('The recording bracket must have positive duration')
    if value.get('anchor'):
        anchor=value['anchor'];offset=integer(anchor['source_offset_ms'],'known airing source offset')
        if not a<=offset<b:raise ValueError('The known airing must lie inside the recording bracket')
        start=timestamp(anchor['aired_at'])-(offset-a)
    else:start=timestamp(value['broadcast_start'])
    end=start+b-a
    if value.get('broadcast_end') and timestamp(value['broadcast_end'])!=end:raise ValueError('Broadcast bracket and recording duration disagree')
    if b-a>24*3600000:raise ValueError('A complete block may span up to 24 hours')
    return start,end,a,b


def register(db,value,*,verify_media=True):
    value=dict(value);service=value['service_id']
    if (value.get('anchor') or {}).get('airing_id'):
        airing=db.execute('SELECT * FROM historical_airing WHERE id=? AND service_id=?',(value['anchor']['airing_id'],service)).fetchone()
        if not airing:raise ValueError('That known airing does not belong to this channel')
        value['anchor']={**value['anchor'],'aired_at':datetime.fromtimestamp(airing['start_ms']/1000,timezone.utc).isoformat(),'title':airing['title'],'content_id':airing['content_id']}
    start,end,a,b=bracket(value)
    if not db.execute('SELECT 1 FROM service WHERE id=?',(service,)).fetchone():raise ValueError('Unknown channel')
    if not value.get('title','').strip():raise ValueError('Name this block')
    existing=db.execute('SELECT * FROM source WHERE id=?',(value.get('source_id'),)).fetchone()
    remote=value.get('url')
    with db:
        if existing:
            source_id=existing['id'];duration=existing['duration_ms']
            if remote:raise ValueError('Choose an existing source or a remote URL')
        else:
            if remote:
                parts=urlsplit(remote)
                if parts.scheme!='https' or not parts.hostname or parts.username or parts.password:raise ValueError('Use a direct HTTPS video URL')
                if value.get('allow_remote') is not True:raise ValueError('Enable streaming for this remote recording')
                duration=integer(value['duration_ms'],'duration_ms',1)
                digest='remote-url:'+hashlib.sha256(remote.encode()).hexdigest();path=remote
            else:
                path=str(Path(value['path']).resolve(strict=True))
                duration=probe(path) if verify_media else integer(value['duration_ms'],'duration_ms',1)
                digest=fingerprint(path)
            source_id='block-source:'+uuid.uuid4().hex
            tags=value.get('tags',[])
            if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags):raise ValueError('Block tags must be a list of strings')
            context=validate_context({'tags':[t.strip().casefold() for t in tags],'kind':'recorded','recorded_date':value.get('recorded_date') or datetime.fromtimestamp(start/1000,datetime.fromisoformat(value['anchor']['aired_at'] if value.get('anchor') else value['broadcast_start']).tzinfo).date().isoformat(),
                'seasonal':value.get('seasonal'),'holiday':value.get('holiday'),'holiday_year':value.get('holiday_year')})
            provenance={'kind':'remote_recording' if remote else 'complete_recording','url':remote,'note':value.get('note',''),
                'hash_kind':'URL identity, not media checksum' if remote else 'media SHA-256'}
            db.execute('INSERT INTO source VALUES (?,?,?,?,?)',(source_id,path,duration,digest,json.dumps(provenance)))
            db.execute('INSERT INTO source_ingest VALUES (?,?,?)',(source_id,'recorded',json.dumps(context)))
            if remote:db.execute("INSERT INTO stream_source VALUES (?,?,1,'unknown',NULL)",(source_id,remote))
        if b>duration:raise ValueError('The recording bracket extends beyond the source duration')
        ident=uuid.uuid4().hex
        points=value.get('known_points',[])
        if not isinstance(points,list):raise ValueError('Known airing points must be a list')
        if value.get('anchor'):points=[value['anchor'],*points]
        for point in points:
            offset=integer(point['source_offset_ms'],'known point offset')
            if not a<=offset<b or timestamp(point['aired_at'])!=start+offset-a:raise ValueError('Known airing points disagree with this block anchor')
        db.execute('INSERT INTO complete_block VALUES (?,?,?,?,?,?,?,?,?,?)',(ident,service,source_id,value['title'].strip(),start,end,a,b,json.dumps(points),utc_now()))
    return {'id':ident,'source_id':source_id,'start_ms':start,'end_ms':end,'status':'Complete block anchored. Original order and timing preserved.'}


def stream(db,digest):
    return db.execute('SELECT r.* FROM stream_source r JOIN source s ON s.id=r.source_id WHERE s.sha256=?',(digest,)).fetchone()


def report_playback(db,value,now):
    row=db.execute('''SELECT s.source_hash FROM segment s WHERE s.id=? AND s.start_ms<=? AND s.end_ms>?''',(value['segment_id'],now,now)).fetchone()
    if not row:raise ValueError('Playback report must refer to the current segment')
    remote=stream(db,row[0])
    if not remote or value.get('status') not in ('online','offline'):raise ValueError('Unknown remote playback report')
    with db:db.execute('UPDATE stream_source SET availability=?,checked_at=? WHERE source_id=?',(value['status'],utc_now(),remote['source_id']))
    return {'status':'Playback health updated','source_id':remote['source_id']}


def compose(db,service,start,state):
    block=db.execute('SELECT b.*,s.path,s.sha256 FROM complete_block b JOIN source s ON s.id=b.source_id WHERE b.service_id=? AND b.start_ms<=? AND b.end_ms>?',(service,start,start)).fetchone()
    if not block:return False
    mode=db.execute('SELECT mode FROM viewing_mode WHERE id=1').fetchone()
    selected=db.execute('SELECT rules FROM selection_rule WHERE service_id=?',(service,)).fetchone()
    if mode and mode[0] in ('representative','surfing') and selected:
        rules=json.loads(selected[0]);context=db.execute('SELECT context FROM source_ingest WHERE source_id=?',(block['source_id'],)).fetchone()
        tags=set(json.loads(context[0]).get('tags',[])) if context else set()
        points=json.loads(block['known_points']);identities={p.get('content_id') for p in points if p.get('content_id')}
        for ident in list(identities):
            seen=set()
            while ident and ident not in seen:
                seen.add(ident);row=db.execute('SELECT parent_id,tags FROM content WHERE id=?',(ident,)).fetchone()
                if not row:break
                tags.update(t.casefold() for t in json.loads(row['tags']));ident=row['parent_id']
                if ident:identities.add(ident)
        if rules.get('tags') and not tags.intersection(rules['tags']):return False
        if tags.intersection(rules.get('exclude_tags',[])):return False
        if rules.get('content_ids') and not identities.intersection(rules['content_ids']):return False
        if identities.intersection(rules.get('exclude_content_ids',[])):return False
    from .scheduler import rank
    ident=rank(state['seed'],service,start)[:32]
    db.execute('INSERT INTO broadcast VALUES (?,?,?,?,?,?,?)',(ident,service,start,block['end_ms'],block['title'],None,'recorded_block'))
    db.execute('INSERT INTO segment(broadcast_id,start_ms,end_ms,asset_id,title,kind,path,source_in_ms,source_hash,reason) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (ident,start,block['end_ms'],None,block['title'],'block',block['path'],block['source_in_ms']+start-block['start_ms'],block['sha256'],None))
    return True


def attach_presentation(db,value):
    if value.get('approved') is not True:raise ValueError('Approve this copy as the same recording and timeline')
    row=db.execute('SELECT s.* FROM source s JOIN complete_block b ON b.source_id=s.id WHERE b.id=?',(value['block_id'],)).fetchone()
    if not row:raise ValueError('Unknown complete block')
    path=Path(value['path']).resolve(strict=True);duration=probe(path)
    if abs(duration-row['duration_ms'])>50:raise ValueError('A local copy must preserve the recording duration and timeline')
    with db:db.execute('INSERT INTO block_presentation VALUES (?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET path=excluded.path,sha256=excluded.sha256,duration_ms=excluded.duration_ms,approved_at=excluded.approved_at',
        (row['id'],str(path),fingerprint(path),duration,utc_now()))
    return {'status':'Local presentation linked; original recording and broadcast anchor preserved'}


def presentation(db,digest):
    row=db.execute('SELECT p.path FROM block_presentation p JOIN source s ON s.id=p.source_id WHERE s.sha256=?',(digest,)).fetchone()
    return row[0] if row and Path(row[0]).is_file() else None
