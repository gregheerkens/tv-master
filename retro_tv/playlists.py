"""Editable JSON block drafts; tuning copies a version into a fixed context."""
import json
import uuid
from .records import utc_now


def get(db,ident):
    row=db.execute('SELECT * FROM party_playlist WHERE id=?',(ident,)).fetchone()
    if not row:raise ValueError('Block not found')
    return {**json.loads(row['document']),'id':row['id'],'revision':row['revision'],
            'created_at':row['created_at'],'updated_at':row['updated_at']}


def listing(db):
    return {'blocks':[get(db,r[0]) for r in db.execute('SELECT id FROM party_playlist ORDER BY updated_at DESC,id DESC LIMIT 100')],
            'assets':[dict(r) for r in db.execute('SELECT id,title,kind,out_ms-in_ms AS duration_ms FROM asset ORDER BY title,id')]}


def validate(db,doc):
    from .timelines import normalize_request
    if not isinstance(doc,dict):raise ValueError('Block JSON must be an object')
    if set(doc)-{'version','name','duration_minutes','selection','items'}:raise ValueError('Unsupported block field')
    if doc.get('version')!=1:raise ValueError('Expected block version 1')
    name=doc.get('name')
    if not isinstance(name,str) or not name.strip() or len(name)>200:raise ValueError('Give the block a name (up to 200 characters)')
    duration=doc.get('duration_minutes')
    if type(duration) is not int or duration not in (15,30,60,90):raise ValueError('Choose 15, 30, 60 or 90 minutes')
    selection=doc.get('selection')
    if not isinstance(selection,dict) or 'block_id' in selection:raise ValueError('Use explicit generation settings, not another block ID')
    request=normalize_request(db,selection)
    if request['mode']!='representative' or request['rules'].get('block_minutes')!=duration:raise ValueError('Block selection and duration must match')
    items=doc.get('items')
    if not isinstance(items,list) or len(items)>2000:raise ValueError('Expected a playlist with at most 2000 segments')
    cleaned=[];total=0
    for item in items:
        if not isinstance(item,dict):raise ValueError('Invalid playlist segment')
        if set(item)=={'asset_id'}:
            asset=db.execute('SELECT out_ms-in_ms FROM asset WHERE id=?',(item['asset_id'],)).fetchone()
            if not asset:raise ValueError('Unknown library segment')
            total+=asset[0];cleaned.append({'asset_id':item['asset_id']})
        elif set(item)=={'gap_ms'} and type(item['gap_ms']) is int and item['gap_ms']>0:
            total+=item['gap_ms'];cleaned.append({'gap_ms':item['gap_ms']})
        else:raise ValueError('Use asset_id or positive gap_ms; paths and playback controls are not playlist fields')
    if total>duration*60000:raise ValueError('Playlist exceeds the block duration; remove material or choose a longer format')
    return {'version':1,'name':name.strip(),'duration_minutes':duration,'selection':selection,'items':cleaned}


def save(db,value):
    doc=validate(db,value['document']);ident=value.get('id');now=utc_now()
    with db:
        if ident:
            if type(value.get('revision')) is not int:raise ValueError('Reload the block before saving')
            changed=db.execute('UPDATE party_playlist SET document=?,revision=revision+1,updated_at=? WHERE id=? AND revision=?',
                               (json.dumps(doc),now,ident,value['revision'])).rowcount
            if not changed:raise ValueError('Block changed or was deleted; reopen it before saving')
        else:
            ident=uuid.uuid4().hex
            db.execute('INSERT INTO party_playlist VALUES (?,?,1,?,?)',(ident,json.dumps(doc),now,now))
    return get(db,ident)


def generate(db,value):
    from .timelines import normalize_request, build
    from .scheduler import wall_ms
    old=get(db,value['id']) if value.get('id') else None
    selection=old['selection'] if old else value['selection']
    request=normalize_request(db,selection)
    duration=request['rules'].get('block_minutes')
    if request['mode']!='representative' or duration not in (15,30,60,90):raise ValueError('Choose a Block Party format first')
    scratch,now=build(db,request,wall_ms(),composition_seed=uuid.uuid4().hex)
    try:
        origin=scratch.execute('SELECT historical_anchor_ms FROM state').fetchone()[0];span=duration*60000
        begin=origin+(now-origin)//span*span
        items=[]
        for row in scratch.execute('''SELECT s.* FROM segment s JOIN broadcast b ON b.id=s.broadcast_id
              WHERE b.service_id=? AND s.start_ms>=? AND s.start_ms<? ORDER BY s.start_ms''',(request['service_id'],begin,begin+span)):
            items.append({'asset_id':row['asset_id']} if row['asset_id'] else {'gap_ms':row['end_ms']-row['start_ms']})
        return save(db,{'document':{'version':1,'name':old['name']+' (regenerated)' if old else value.get('name') or 'New block',
                    'duration_minutes':duration,'selection':selection,'items':items}})
    finally:scratch.close()


def delete(db,value):
    with db:
        if not db.execute('DELETE FROM party_playlist WHERE id=? AND revision=?',(value['id'],value['revision'])).rowcount:
            raise ValueError('Block changed or was deleted; refresh recent blocks')
    return {'deleted':value['id']}


def compose(db,service,start,state,playlist):
    """Snapshot references into published segments; never consult the mutable draft."""
    from .scheduler import rank, eligible
    from .records import Policy
    from .broadcasts import timezone
    from datetime import datetime
    from zoneinfo import ZoneInfo
    span=playlist['duration_minutes']*60000;ident=rank(state['seed'],service,start)[:32]
    db.execute('INSERT INTO broadcast VALUES (?,?,?,?,?,?,?)',(ident,service,start,start+span,playlist['name'],None,'composed'))
    cursor=start;policy=Policy(db);zone=ZoneInfo(timezone(db))
    items=list(playlist['items']);used=0
    for item in items:
        asset=db.execute('SELECT a.*,s.path,s.sha256 FROM asset a JOIN source s ON s.id=a.source_id WHERE a.id=?',(item.get('asset_id'),)).fetchone() if 'asset_id' in item else None
        size=asset['out_ms']-asset['in_ms'] if asset else item.get('gap_ms',0)
        if size<=0 or used+size>span:raise ValueError('Invalid published playlist')
        valid=asset and all(eligible(asset,service,datetime.fromtimestamp(t/1000,zone).date().isoformat()) and
            policy.allowed(asset['id'],service,datetime.fromtimestamp(t/1000,zone).date().isoformat()) for t in (cursor,cursor+size-1))
        db.execute('INSERT INTO segment (broadcast_id,start_ms,end_ms,asset_id,title,kind,path,source_in_ms,source_hash,reason) VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (ident,cursor,cursor+size,asset['id'] if valid else None,asset['title'] if valid else 'Station slate',asset['kind'] if valid else 'slate',asset['path'] if valid else None,asset['in_ms'] if valid else 0,asset['sha256'] if valid else None,None if valid else 'Unfilled or ineligible playlist segment'))
        used+=size;cursor+=size
    if used<span:
        db.execute('INSERT INTO segment (broadcast_id,start_ms,end_ms,title,kind,source_in_ms,reason) VALUES (?,?,?,?,?,?,?)',
                   (ident,cursor,start+span,'Station slate','slate',0,'Unfilled playlist time'))
