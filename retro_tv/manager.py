"""Catalog-backed planning on scratch databases; no live-guide reset or reroll."""
import hashlib
import json
import math
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .catalog import fingerprint, import_library
from .records import Policy, utc_now
from . import broadcasts
from .health import resolve_path, timeline_health


def timestamp(value):
    stamp=datetime.fromisoformat(value)
    if stamp.tzinfo is None:raise ValueError('listing timestamps need explicit timezone offsets')
    return int(stamp.timestamp()*1000)


def import_plan(db,document):
    if document.get('version')!=1:raise ValueError('listing import version must be 1')
    with db:
        for row in document.get('airings',[]):
            a,b=timestamp(row['start']),timestamp(row['end'])
            if not 0<b-a<=12*3600000:raise ValueError('airing must last between 0 and 12 hours')
            if not row.get('provenance'):raise ValueError('listings require source provenance')
            provenance=row['provenance'];content_id=row.get('content_id')
            episode=row.get('episode_title') or (provenance.get('source_episode_text') if isinstance(provenance,dict) else None)
            if episode:
                from .identities import resolve
                current=db.execute('SELECT kind FROM content WHERE id=?',(content_id,)).fetchone()
                if not current or current['kind']!='episode':content_id=resolve(db,row['title'],episode)
                provenance={**(provenance if isinstance(provenance,dict) else {'source':provenance}),'source_episode_text':episode,'needs_check':True}
            db.execute('INSERT INTO historical_airing VALUES (?,?,?,?,?,?,?,?)',
                (row['id'],row['service_id'],content_id,row['title'],a,b,
                 row['evidence_state'],json.dumps(provenance)))
            for requirement in row.get('requirements',[]):
                duration=requirement['duration_ms']
                if type(duration) is not int or not 0<duration<=b-a:
                    raise ValueError('requirement duration must fit the airing')
                if not requirement.get('provenance'):raise ValueError('requirements need evidence')
                db.execute('INSERT INTO airing_requirement VALUES (?,?,?,?,?,?,?)',
                    (requirement['id'],row['id'],requirement.get('content_id'),requirement['kind'],
                     duration,requirement.get('note',''),json.dumps(requirement['provenance'])))


def inventory(db):
    policy=Policy(db)
    assets=[]
    for row in db.execute('''SELECT a.*,s.path,s.sha256,c.content_id FROM asset a
          JOIN source s ON s.id=a.source_id LEFT JOIN asset_content c ON c.asset_id=a.id ORDER BY a.title'''):
        assets.append({'id':row['id'],'title':row['title'],'kind':row['kind'],
            'content_id':row['content_id'],'duration_ms':row['out_ms']-row['in_ms'],
            'source_id':row['source_id'],'file_available':resolve_path(db,row['path'],row['sha256']) is not None,
            'excluded':row['id'] in policy.recordings,'path':row['path']})
    contents=[dict(r) for r in db.execute('SELECT id,title,kind,episode_title,tags FROM content ORDER BY title')]
    for row in contents:row['tags']=json.loads(row['tags'])
    channels=[dict(r) for r in db.execute('SELECT s.*,p.mode,p.theme_tags FROM service s LEFT JOIN channel_profile p ON p.service_id=s.id ORDER BY s.name')]
    return {'assets':assets,'contents':contents,'channels':channels,
        'programs':[dict(r) for r in db.execute('SELECT id,title FROM program ORDER BY title')],
        'sources':[dict(r) for r in db.execute('SELECT id,path,sha256 FROM source')],
        'alerts':[dict(r) for r in db.execute('SELECT * FROM quality_alert WHERE resolved_at IS NULL')]}


def dashboard(db,now,standard_id='channel',requested_date=None,days=3):
    from .recommendations import get_standard,standards,score
    standard=get_standard(db,standard_id)
    if type(days) is not int or not 1<=days<=3:raise ValueError('assess 1, 2 or 3 days')
    zone=ZoneInfo(broadcasts.timezone(db))
    day=requested_date if requested_date and standard['mode']!='channel' else datetime.fromtimestamp(now/1000,zone).date().isoformat()
    date.fromisoformat(day)
    channels=[]
    services=db.execute('SELECT * FROM service ORDER BY name').fetchall() if standard['mode']=='theme' else broadcasts.channels(db,day)
    allowed=broadcasts.service_ids(db)
    for service in services:
        if service['id'] not in allowed:continue
        health=timeline_health(db,service['id'],now,now+72*3600000)
        totals={k:sum(h[k] for h in health.values()) for k in ('playable_ms','slate_ms','missing_file_ms','program_ms','commercial_ms','continuity_ms','quality_alerts')}
        row={**dict(service),**totals,'blocks':len(health),
            'playable_percent':round(totals['playable_ms']/(72*3600000)*100,1),
            'gap_blocks':sum(h['status'] in ('missing','partial','offline','unknown') for h in health.values())}
        profile=db.execute('SELECT theme_tags FROM channel_profile WHERE service_id=?',(service['id'],)).fetchone()
        result=assess(db,{'service_id':service['id'],'date':day,'days':days,'mode':standard['mode'],
            'tags':json.loads(profile[0]) if profile else [],'standard_id':standard_id})
        if standard['mode']=='channel':
            result['playable_percent']=row['playable_percent']
            result['repeat_passes_needed']=math.ceil(row['program_ms']/result['unique_program_ms']) if result['unique_program_ms'] else 0
            result['health']=score(result,standard)
        row['assessment_health']=result['health'];row['assessed_playable_percent']=result['playable_percent']
        row['researched_percent']=result['known_schedule_percent']
        row['assessed_program_ms']=row['program_ms'] if standard['mode']=='channel' else result['program_ms']
        row['assessed_continuity_ms']=row['commercial_ms']+row['continuity_ms'] if standard['mode']=='channel' else result['commercial_ms']+result['continuity_ms']
        row['assessed_gap_blocks']=row['gap_blocks'] if standard['mode']=='channel' else len(result['gaps'])
        channels.append(row)
    healthy=sum(c['assessment_health']['status']=='ready' for c in channels)
    return {'now_ms':now,'timezone':broadcasts.timezone(db),
        'channels':channels,'inventory':inventory(db),
        'health_standard':standard,'health_standards':standards(db),
        'assessment_date':day,'assessment_days':days,
        'lineup_health':{'channel_count':len(channels),'healthy_channels':healthy,
            'unknown_channels':sum(c['assessment_health']['status'] in ('unknown','research_incomplete') for c in channels),
            'target_channels':standard['settings']['min_healthy_channels'],
            'meets_target':healthy>=standard['settings']['min_healthy_channels']},
        'historical_airings':db.execute('SELECT count(*) FROM historical_airing').fetchone()[0]}


def available_program(db,row,service,day,policy):
    from .scheduler import eligible
    if not eligible(row,service,day) or not policy.allowed(row['id'],service,day,program=True):return False
    for ident in json.loads(row['parts']):
        asset=db.execute('SELECT a.*,s.path,s.sha256 FROM asset a JOIN source s ON s.id=a.source_id WHERE a.id=?',(ident,)).fetchone()
        if not asset or not eligible(asset,service,day) or not policy.allowed(ident,service,day):return False
        if not resolve_path(db,asset['path'],asset['sha256']):return False
    return True


def assess(db,request):
    """Generate an isolated 1–3-day plan; live state and published blocks untouched."""
    from .scheduler import compose
    service=request['service_id'];mode=request.get('mode','channel')
    if not db.execute('SELECT 1 FROM service WHERE id=?',(service,)).fetchone():raise ValueError('unknown service')
    if mode not in ('channel','historical','theme'):raise ValueError('unknown assessment mode')
    days=request.get('days',1)
    if type(days) is not int or not 1<=days<=3:raise ValueError('assess 1, 2 or 3 days')
    start_date=date.fromisoformat(request['date'])
    state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
    zone=ZoneInfo(broadcasts.timezone(db))
    start=int(datetime.combine(start_date,datetime.min.time(),zone).timestamp()*1000)
    end=int(datetime.combine(start_date+timedelta(days=days),datetime.min.time(),zone).timestamp()*1000)
    scratch=sqlite3.connect(':memory:');scratch.row_factory=sqlite3.Row
    try:
        db.backup(scratch)
        scratch.execute('PRAGMA foreign_keys=OFF')
        for trigger in ('broadcast_no_delete','segment_no_delete','context_no_delete'):
            scratch.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        for table in ('viewing_event','broadcast_context','segment','broadcast'):
            scratch.execute(f'DELETE FROM {table}')
        tags=request.get('tags',[])
        if not isinstance(tags,list) or any(not isinstance(t,str) or not t.strip() for t in tags):raise ValueError('theme tags must be nonempty strings')
        if mode=='theme':
            scratch.execute("INSERT INTO viewing_mode VALUES (1,'representative') ON CONFLICT(id) DO UPDATE SET mode=excluded.mode")
            scratch.execute("UPDATE channel_profile SET mode='themed',theme_tags=? WHERE service_id=?",(json.dumps(tags),service))
            # A hypothetical theme does not claim to reproduce a historical lineup.
            scratch.execute('DELETE FROM airing_requirement')
            scratch.execute('DELETE FROM historical_airing')
        elif mode=='historical':
            scratch.execute("INSERT INTO viewing_mode VALUES (1,'historical') ON CONFLICT(id) DO UPDATE SET mode=excluded.mode")
            scratch.execute("UPDATE channel_profile SET mode='historical' WHERE service_id=?",(service,))
        policy=Policy(scratch)
        programs=scratch.execute('SELECT * FROM program').fetchall()
        unique={}
        for d in range(days):
            day=(start_date+timedelta(days=d)).isoformat()
            for row in programs:
                if available_program(scratch,row,service,day,policy):
                    ident=policy.program_ids.get(row['id'],row['id'])
                    duration=sum(scratch.execute('SELECT out_ms-in_ms FROM asset WHERE id=?',(a,)).fetchone()[0] for a in json.loads(row['parts']))
                    unique[ident]=max(unique.get(ident,0),duration)
        cursor=start
        while cursor<end:
            compose(scratch,service,cursor,state)
            cursor=scratch.execute('SELECT max(end_ms) FROM broadcast WHERE service_id=?',(service,)).fetchone()[0]
        health=timeline_health(scratch,service,start,end)
        totals={k:sum(h[k] for h in health.values()) for k in ('playable_ms','program_ms','block_ms','commercial_ms','continuity_ms','slate_ms','missing_file_ms')}
        history=[] if mode=='theme' else db.execute('SELECT * FROM historical_airing WHERE service_id=? AND start_ms<? AND end_ms>? ORDER BY start_ms',(service,end,start)).fetchall()
        known=sum(min(end,r['end_ms'])-max(start,r['start_ms']) for r in history if r['evidence_state'] in ('exact','schedule_exact'))
        exact=sum(min(end,r['end_ms'])-max(start,r['start_ms']) for r in history if r['evidence_state']=='exact')
        identified=sum(min(end,r['end_ms'])-max(start,r['start_ms']) for r in history if r['content_id'] and db.execute("SELECT 1 FROM content WHERE id=? AND kind='episode'",(r['content_id'],)).fetchone())
        gaps=[]
        for row in scratch.execute('SELECT * FROM broadcast WHERE service_id=? AND start_ms<? ORDER BY start_ms',(service,end)):
            status=health.get(row['id'],{})
            if status.get('status') in ('missing','partial','offline','unknown'):
                gaps.append({'id':row['id'],'title':row['title'],'start_ms':row['start_ms'],
                    'end_ms':min(row['end_ms'],end),'status':status['status'],'reasons':status['reasons'],
                    'program_missing':row['program_id'] is None and row['evidence']!='recorded_block',
                    'expected_content_id':next((r['content_id'] for r in history if r['start_ms']<=row['start_ms']<r['end_ms']),None),
                    'airing_id':next((r['id'] for r in history if r['start_ms']<=row['start_ms']<r['end_ms']),None)})
        requirements=[]
        for airing in history:
            for requirement in db.execute('SELECT * FROM airing_requirement WHERE airing_id=?',(airing['id'],)):
                candidates=[]
                for asset in scratch.execute('''SELECT a.*,s.path,s.sha256,c.content_id FROM asset a JOIN source s ON s.id=a.source_id
                         LEFT JOIN asset_content c ON c.asset_id=a.id WHERE a.kind=?''',(requirement['kind'],)):
                    if requirement['content_id'] and asset['content_id']!=requirement['content_id']:continue
                    day=datetime.fromtimestamp(airing['start_ms']/1000,zone).date().isoformat()
                    from .scheduler import eligible
                    if eligible(asset,service,day) and policy.allowed(asset['id'],service,day) and resolve_path(scratch,asset['path'],asset['sha256']):
                        candidates.append(asset)
                available=sum(a['out_ms']-a['in_ms'] for a in candidates)
                requirements.append({**dict(requirement),'airing_title':airing['title'],
                    'available_ms':available,'status':'ready' if available>=requirement['duration_ms'] else 'missing',
                    'provenance':json.loads(requirement['provenance'])})
        span=end-start
        daily=[]
        for d in range(days):
            a=int(datetime.combine(start_date+timedelta(days=d),datetime.min.time(),zone).timestamp()*1000)
            b=int(datetime.combine(start_date+timedelta(days=d+1),datetime.min.time(),zone).timestamp()*1000)
            daily_health=timeline_health(scratch,service,a,b)
            daily.append({'date':str(start_date+timedelta(days=d)),
                'playable_percent':round(sum(h['playable_ms'] for h in daily_health.values())/(b-a)*100,1),
                'gap_blocks':sum(h['status'] in ('missing','partial','offline','unknown') for h in daily_health.values())})
        substituted=sum(h['evidence']=='substituted' for h in health.values())
        result={'service_id':service,'mode':mode,'date':str(start_date),'days':days,'start_ms':start,'end_ms':end,
            'simulation_only':True,**totals,'playable_percent':round(totals['playable_ms']/span*100,1),
            'known_schedule_percent':round(known/span*100,1) if mode!='theme' else None,
            'exact_schedule_percent':round(exact/span*100,1) if mode!='theme' else None,
            'identified_episode_percent':round(identified/span*100,1) if mode!='theme' else None,
            'unique_programs':len(unique),'unique_program_ms':sum(unique.values()),
            'repeat_passes_needed':math.ceil(totals['program_ms']/sum(unique.values())) if unique else 0,
            'historically_complete':mode=='historical' and exact==span and not gaps and not substituted and all(r['status']=='ready' for r in requirements),
            'daily':daily,'substituted_blocks':substituted,
            'gaps':gaps,'requirements':requirements,'history':[dict(r) for r in history] if mode!='theme' else [],
            'note':'Analysis only. Finding media affects future composition; published slots stay fixed.'}
        from .recommendations import get_standard,enrich
        standard=get_standard(db,request.get('standard_id',mode))
        if standard['mode']!=mode:raise ValueError('choose a health standard for the assessment mode')
        return enrich(scratch,result,standard)
    finally:scratch.close()


def attach_media(db,value):
    """User identifies an already divided file inside a selected ripped-media folder."""
    content=db.execute('SELECT * FROM content WHERE id=?',(value['content_id'],)).fetchone()
    if not content:raise ValueError('unknown content identity')
    folder=Path(value['folder']).resolve(strict=True)
    path=(folder/value['file']).resolve(strict=True)
    if not folder.is_dir() or not path.is_relative_to(folder) or not path.is_file():raise ValueError('select a file inside the chosen prepared-media folder')
    digest=fingerprint(path);source_id=digest[:24]
    existing=db.execute('SELECT s.id,i.context FROM source s JOIN source_ingest i ON i.source_id=s.id WHERE s.sha256=? AND s.path=?',
                        (digest,str(path))).fetchone()
    context=json.loads(existing['context']) if existing else {'kind':'ripped'}
    if existing:source_id=existing['id']
    ident=hashlib.sha256((content['id']+digest).encode()).hexdigest()[:24]
    kind=content['kind'] if content['kind'] in ('commercial','bumper','promo','station_id','psa') else 'program'
    asset={'id':'located:'+ident,'source_id':source_id,'title':content['episode_title'] or content['title'],
        'kind':kind,'valid_from':value['valid_from'],'valid_until':value['valid_until'],
        'services':value.get('services',[]),'content_id':content['id'],
        'metadata':{'review_status':'approved','evidence':'User located and identified file'}}
    if db.execute('SELECT 1 FROM asset WHERE id=?',(asset['id'],)).fetchone():
        return {'asset_id':asset['id'],'status':'This recording is already linked to that content identity'}
    document={'version':1,'sources':[{'id':source_id,'path':str(path),'ingest':context,
        'provenance':{'origin':'manager: user-located prepared library file'}}],'assets':[asset]}
    if kind=='program':document['programs']=[{'id':asset['id'],'title':asset['title'],'parts':[asset['id']],
        'valid_from':value['valid_from'],'valid_until':value['valid_until'],'services':value.get('services',[]),
        'content_id':content['id']}]
    import_library(db,document,folder)
    return {'asset_id':asset['id'],'status':'Located file cataloged; published slots unchanged'}


def repair_source(db,value):
    row=db.execute('SELECT * FROM source WHERE id=?',(value['source_id'],)).fetchone()
    if not row:raise ValueError('unknown source')
    path=Path(value['path']).resolve(strict=True)
    if not path.is_file() or fingerprint(path)!=row['sha256']:raise ValueError('repair must be a byte-identical copy of the original source')
    with db:db.execute('INSERT INTO source_location VALUES (?,?,?) ON CONFLICT(sha256) DO UPDATE SET path=excluded.path,verified_at=excluded.verified_at',
                       (row['sha256'],str(path),utc_now()))
    return {'status':'Identical source located; existing published segments can play again'}


def set_override(db,value):
    if not value.get('note','').strip():raise ValueError('substitution requires a reason')
    with db:db.execute('INSERT INTO airing_override VALUES (?,?,?) ON CONFLICT(airing_id) DO UPDATE SET program_id=excluded.program_id,note=excluded.note',
                       (value['airing_id'],value['program_id'],value['note']))
    return {'status':'Explicit substitution saved for analysis and unpublished blocks only'}
