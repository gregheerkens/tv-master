"""Evidence-backed gaps, capacity diagnostics and honest external search links."""
import json
import re
from urllib.parse import urlencode
from datetime import datetime
from zoneinfo import ZoneInfo

from .health import resolve_path
from .records import Policy


def standards(db):
    return [{**dict(r),'settings':json.loads(r['settings'])} for r in db.execute('SELECT * FROM health_standard ORDER BY id')]


def get_standard(db,ident):
    row=db.execute('SELECT * FROM health_standard WHERE id=?',(ident,)).fetchone()
    if not row:raise ValueError('unknown health standard')
    return {**dict(row),'settings':json.loads(row['settings'])}


def save_standard(db,value):
    if not re.fullmatch(r'[a-z0-9_-]{1,50}',value['id']):raise ValueError('invalid health standard ID')
    if value['mode'] not in ('historical','theme','channel'):raise ValueError('invalid health mode')
    if not isinstance(value.get('name'),str) or not value['name'].strip():raise ValueError('name the health standard')
    settings=value['settings'];defaults=get_standard(db,value['mode'])['settings']
    if not isinstance(settings,dict) or set(settings)!=set(defaults):raise ValueError('supply all supported health criteria')
    for key,val in settings.items():
        if key=='allow_substitutions':
            if type(val) is not bool:raise ValueError('allow_substitutions must be boolean')
        elif type(val) not in (int,float) or not 0<=val<=10000:raise ValueError('health criteria must be finite nonnegative numbers')
        if key.endswith('_percent') and val>100:raise ValueError('percentages cannot exceed 100')
    if type(settings['min_healthy_channels']) is not int or settings['min_healthy_channels']<1:raise ValueError('choose a positive channel count')
    with db:db.execute('INSERT INTO health_standard VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,mode=excluded.mode,settings=excluded.settings',
        (value['id'],value['name'].strip(),value['mode'],json.dumps(settings)))
    return {'status':'Health standard saved. Broadcast timing and published schedules are unchanged.'}


def score(report,standard):
    s=standard['settings'];issues=[]
    history=report.get('known_schedule_percent')
    research='not_applicable' if report['mode']=='theme' else 'unresearched' if not history else 'partial' if history<100 else 'covered'
    if report['playable_percent']<s['min_playable_percent']:issues.append(f"Playable footage {report['playable_percent']}% is below {s['min_playable_percent']}%")
    if report['unique_program_ms']/3600000<s['min_unique_hours']:issues.append('Unique program inventory is below your target')
    if report['repeat_passes_needed']>s['max_inventory_passes']:issues.append('Program repetition exceeds your inventory-pass target')
    if report.get('unique_commercial_ms',0)/60000<s['ad_minutes_per_day']*report['days']:issues.append('Period commercial variety is below your target')
    if standard['mode']=='historical':
        if history is None or history<s['min_history_percent']:issues.append('Historical listings coverage is below your research target')
        if (report.get('identified_episode_percent',report.get('exact_schedule_percent')) or 0)<s['min_exact_percent']:issues.append('Identified episodes are below your target')
        if report['substituted_blocks'] and not s['allow_substitutions']:issues.append('Explicit substitutions do not meet this recreation standard')
    status='ready' if not issues else 'needs_work'
    if standard['mode']=='historical' and research in ('unresearched','partial'):
        status='unknown' if research=='unresearched' else 'research_incomplete'
    return {'status':status,'standard_id':standard['id'],'standard_name':standard['name'],
            'research_status':research,'issues':issues}


def search_links(query,*,dvd=False):
    if dvd:return [{'label':'Search eBay DVDs','url':'https://www.ebay.com/sch/i.html?'+urlencode({'_nkw':query+' DVD'})},{'label':'Find on Internet Archive','url':'https://archive.org/search?'+urlencode({'query':query+' mediatype:movies'})}]
    return [{'label':'Search Internet Archive','url':'https://archive.org/search?'+urlencode({'query':query})},
            {'label':'Search YouTube','url':'https://www.youtube.com/results?'+urlencode({'search_query':query})}]


def ranges(numbers):
    numbers=sorted(set(numbers));groups=[]
    for n in numbers:
        if groups and n==groups[-1][-1]+1:groups[-1].append(n)
        else:groups.append([n])
    return ', '.join(str(g[0]) if len(g)==1 else f'{g[0]}–{g[-1]}' for g in groups)


def enrich(db,report,standard):
    """Recommend only named requirements established by imported history.

    Category/variety shortages are assessments against user standards, never
    claims that a particular unresearched episode or commercial is missing.
    """
    from .scheduler import eligible
    policy=Policy(db);day=report['date'];service=report['service_id'];unique={}
    for row in db.execute('SELECT a.*,s.path,s.sha256,c.content_id FROM asset a JOIN source s ON s.id=a.source_id LEFT JOIN asset_content c ON c.asset_id=a.id WHERE a.kind!="program"'):
        if eligible(row,service,day) and policy.allowed(row['id'],service,day) and resolve_path(db,row['path'],row['sha256']):
            key=(row['kind'],row['content_id'] or row['id']);unique[key]=max(unique.get(key,0),row['out_ms']-row['in_ms'])
    report['unique_commercial_ms']=sum(v for (kind,_),v in unique.items() if kind=='commercial')
    report['unique_continuity_ms']=sum(v for (kind,_),v in unique.items() if kind!='commercial')
    report['health']=score(report,standard)
    recommendations=[]
    if report['mode']=='historical' and (report['known_schedule_percent'] or 0)<100:
        service_name=db.execute('SELECT name FROM service WHERE id=?',(service,)).fetchone()[0]
        query=f'{service_name} TV listings {report["date"]}'
        recommendations.append({'kind':'research','title':'Research this period before declaring its inventory missing',
            'detail':f'{report["known_schedule_percent"]}% of this period has imported listings. Uncovered times are unknown, not missing episodes.',
            'evidence':'coverage','actions':search_links(query)})
    known_missing={}
    history={r['id']:r for r in report['history']}
    for gap in report['gaps']:
        if gap.get('program_missing') and gap.get('expected_content_id'):
            evidence=history.get(gap['airing_id'],{}).get('evidence_state')
            content=db.execute('SELECT kind FROM content WHERE id=?',(gap['expected_content_id'],)).fetchone()
            if evidence=='exact' or (evidence=='schedule_exact' and content and (content['kind']!='episode' or json.loads(history[gap['airing_id']]['provenance']).get('source_episode_text'))):
                known_missing.setdefault(gap['expected_content_id'],[]).append(gap['airing_id'])
    groups={}
    for cid,airings in known_missing.items():
        content=db.execute('SELECT * FROM content WHERE id=?',(cid,)).fetchone()
        if not content:continue
        matched=[]
        for recipe in db.execute('SELECT p.*,c.content_id FROM program p JOIN program_content c ON c.program_id=p.id'):
            ident=recipe['content_id'];seen=set()
            while ident and ident not in seen:
                if ident==cid:matched.append(recipe);break
                seen.add(ident);ident=policy.parents.get(ident)
        if matched:
            available=False
            for recipe in matched:
                paths=[db.execute('SELECT s.path,s.sha256 FROM asset a JOIN source s ON s.id=a.source_id WHERE a.id=?',(part,)).fetchone() for part in json.loads(recipe['parts'])]
                if paths and all(r and resolve_path(db,r['path'],r['sha256']) for r in paths):available=True
            recommendations.append({'kind':'selection_mismatch' if available else 'offline',
                'title':('Review selection / eligibility: ' if available else 'Locate your cataloged recording: ')+content['title'],
                'detail':'A matching recipe is already cataloged. Check its files, exclusions, date windows and slot fit before acquiring another copy.',
                'content_ids':[cid],'airing_ids':sorted(set(airings)),'evidence':'catalog_and_imported_airings',
                'actions':[{'label':'Inspect library','url':'/broadcasts'}]})
            continue
        parent=db.execute('SELECT * FROM content WHERE id=?',(content['parent_id'],)).fetchone() if content['parent_id'] else None
        title=parent['title'] if parent else content['title']
        season=content['season_number']
        key=(title,season);group=groups.setdefault(key,{'episodes':[],'episode_titles':[],'content_ids':[],'airing_ids':[],'unspecified':False})
        group['content_ids'].append(cid);group['airing_ids']+=airings
        if content['episode_title']:group['episode_titles'].append(content['episode_title'])
        if content['episode_number'] is not None:group['episodes'].append(content['episode_number'])
        else:group['unspecified']=True
    for (title,season),group in groups.items():
        season_label=f' — Season {season}' if season is not None else ''
        episodes_label=f', Episodes {ranges(group["episodes"])}' if group['episodes'] else ''
        label=title+season_label+episodes_label
        if season is None and group['episode_titles']:label+=' — '+('; '.join(group['episode_titles']) if len(group['episode_titles'])<=2 else str(len(group['episode_titles']))+' named episodes')
        query=title+(f' season {season}' if season is not None else '')
        recommendations.append({'kind':'known_program_gap','title':label,
            'detail':'These identified items are required by imported airings and have no matched program in the assessed plan. Other unresearched episodes are not implied missing.',
            'episode_titles':group['episode_titles'],'content_ids':group['content_ids'],'airing_ids':sorted(set(group['airing_ids'])),
            'evidence':'imported_airings','actions':search_links(query,dvd=True)+[{'label':'Archive: '+name,'url':'https://archive.org/search?'+urlencode({'query':title+' '+name+' mediatype:movies'})} for name in group['episode_titles'][:3]]})
    target=standard['settings']['ad_minutes_per_day']*report['days']
    minutes=report['unique_commercial_ms']/60000
    if minutes<target:
        year=day[:4]
        recommendations.append({'kind':'variety','title':f'Expand the period commercial pool for {year}',
            'detail':f'{minutes:.1f} unique eligible ad minutes are available against your {target:g}-minute variety target for {report["days"]} days. More era recordings would reduce repeats; this is not proof of a missing named commercial.',
            'evidence':'library_capacity','actions':search_links(f'{year} television commercials bumpers VHS')})
    for requirement in report['requirements']:
        if requirement['status']=='missing':
            content=db.execute('SELECT title FROM content WHERE id=?',(requirement['content_id'],)).fetchone() if requirement['content_id'] else None
            title=content['title'] if content else requirement['note'] or requirement['kind']
            recommendations.append({'kind':'known_continuity_gap','title':'Required '+requirement['kind']+': '+title,
                'detail':f'Known requirement for {requirement["airing_title"]}; its provenance is retained with the airing.',
                'evidence':requirement['provenance'],'content_id':requirement['content_id'],
                'actions':search_links(f'{day[:4]} {title} {requirement["kind"]}')})
    report['recommendations']=recommendations
    report['search_note']='Links open targeted searches, not verified products or identified recordings. Review the source/date before importing.'
    return report
