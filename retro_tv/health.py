"""Actual-file and published-timeline health. Never confuses a slate with footage."""
from pathlib import Path


def resolve_path(db,path,digest=None):
    if path and Path(path).is_file():return path
    if digest:
        row=db.execute('SELECT path FROM source_location WHERE sha256=?',(digest,)).fetchone()
        if row and Path(row[0]).is_file():return row[0]
    return None


def timeline_health(db,service,start,end):
    sources={}
    for row in db.execute('SELECT path,sha256 FROM source'):
        sources[row['path']]=resolve_path(db,row['path'],row['sha256'])
    quality_assets={r[0] for r in db.execute('SELECT asset_id FROM quality_alert WHERE resolved_at IS NULL AND asset_id IS NOT NULL')}
    quality_sources={r[0] for r in db.execute('SELECT source_id FROM quality_alert WHERE resolved_at IS NULL AND source_id IS NOT NULL')}
    asset_sources=dict(db.execute('SELECT id,source_id FROM asset'))
    identities=dict(db.execute('SELECT asset_id,content_id FROM asset_content'))
    coverage={}
    bad_scores={r[0] for r in db.execute('SELECT asset_id FROM recording_quality WHERE score<40')}
    result={}
    for row in db.execute('''SELECT s.*,b.program_id,b.evidence FROM segment s JOIN broadcast b ON b.id=s.broadcast_id
        WHERE b.service_id=? AND s.start_ms<? AND s.end_ms>? ORDER BY s.start_ms''',(service,end,start)):
        item=result.setdefault(row['broadcast_id'],{'playable_ms':0,'slate_ms':0,'missing_file_ms':0,
            'program_ms':0,'commercial_ms':0,'continuity_ms':0,'quality_alerts':0,'reasons':set(),
            'evidence':row['evidence'],'has_program':row['program_id'] is not None})
        duration=min(end,row['end_ms'])-max(start,row['start_ms'])
        if row['kind']=='slate':
            item['slate_ms']+=duration;item['reasons'].add(row['reason'] or 'Unfilled segment')
        elif sources.get(row['path']) or resolve_path(db,row['path'],row['source_hash']):
            item['playable_ms']+=duration
            tally=coverage.setdefault(row['broadcast_id'],{})
            key=(row['kind'],identities.get(row['asset_id']))
            tally[key]=tally.get(key,0)+duration
            field='program_ms' if row['kind']=='program' else 'commercial_ms' if row['kind']=='commercial' else 'continuity_ms'
            item[field]+=duration
        else:
            item['missing_file_ms']+=duration;item['reasons'].add('Source file unavailable')
        if row['asset_id'] in quality_assets|bad_scores or asset_sources.get(row['asset_id']) in quality_sources:
            item['quality_alerts']+=1
    for ident,item in result.items():
        used={}
        for requirement in db.execute('''SELECT r.* FROM airing_requirement r JOIN broadcast_context c
              ON c.airing_id=r.airing_id WHERE c.broadcast_id=?''',(ident,)):
            matching=[key for key in coverage.get(ident,{}) if key[0]==requirement['kind']
                      and (not requirement['content_id'] or key[1]==requirement['content_id'])]
            remaining=requirement['duration_ms']
            for key in matching:
                available=coverage[ident][key]-used.get(key,0)
                take=min(remaining,max(0,available));used[key]=used.get(key,0)+take;remaining-=take
            if remaining:item['reasons'].add('Missing known '+requirement['kind']+': '+requirement['note'])
        if item['missing_file_ms']:status='offline'
        elif not item['has_program']:status='unknown' if 'No historical listing for this time' in item['reasons'] else 'missing'
        elif item['evidence']=='substituted':status='substituted'
        elif item['slate_ms'] or item['quality_alerts'] or item['reasons']:status='partial'
        else:status='ready'
        item['status']=status;item['reasons']=sorted(item['reasons'])
    return result
