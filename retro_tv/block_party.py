"""Library-derived facets for the optional Block Party builder."""
import calendar
import json
from datetime import date, timedelta

DURATIONS=(15,30,60,90)

def metadata_facets(db):
    """Only cataloged program identities/ancestors contribute to the cloud."""
    contents={r['id']:dict(r) for r in db.execute('SELECT * FROM content')}
    result={}
    for row in db.execute('SELECT p.*,pc.content_id FROM program p LEFT JOIN program_content pc ON pc.program_id=p.id'):
        tags=set();years=set();months=set();networks=set();seen=set();ident=row['content_id']
        while ident and ident not in seen:
            seen.add(ident);c=contents.get(ident)
            if not c:break
            tags.update(t.strip().casefold() for t in json.loads(c['tags']) if t.strip())
            if c['original_air_date']:
                stamp=date.fromisoformat(c['original_air_date']);years.add(stamp.year);months.add(stamp.month)
            for window in db.execute('SELECT * FROM eligibility_window WHERE content_id=?',(ident,)):
                if window['network_id']:networks.add(window['network_id'].casefold())
                months.update(json.loads(window['months']))
            meta=json.loads(c['episode_metadata']) if c['episode_metadata'] else {}
            if isinstance(meta,dict):
                for key in ('network','network_id'):
                    v=meta.get(key)
                    if isinstance(v,str) and v.strip():networks.add(v.strip().casefold())
                for key,target,low,high in (('year',years,1,9999),('month',months,1,12)):
                    v=meta.get(key)
                    if type(v) is int and low<=v<=high:target.add(v)
            ident=c['parent_id']
        services=json.loads(row['services'])
        if services:
            for affiliation in db.execute('SELECT * FROM affiliation_history'):
                if affiliation['service_id'] in services and affiliation['valid_from']<row['valid_until'] and row['valid_from']<affiliation['valid_until']:
                    networks.add(affiliation['network_id'].casefold())
        meta=json.loads(row['metadata'])
        for key in ('network','network_id'):
            v=meta.get(key)
            if isinstance(v,str) and v.strip():networks.add(v.strip().casefold())
        for key,target,low,high in (('year',years,1,9999),('month',months,1,12)):
            v=meta.get(key)
            if type(v) is int and low<=v<=high:target.add(v)
        # Explicit tags such as network:fox remain usable even without structured metadata.
        for tag in tags:
            if tag.startswith('network:') and tag[8:].strip():networks.add(tag[8:].strip())
            for prefix,target,low,high in (('year:',years,1,9999),('month:',months,1,12)):
                if tag.startswith(prefix) and tag[len(prefix):].isdigit():
                    v=int(tag[len(prefix):])
                    if low<=v<=high:target.add(v)
        # Undated identities can still be selected by their approved availability era.
        if not years:
            first=date.fromisoformat(row['valid_from']);last=date.fromisoformat(row['valid_until'])-timedelta(days=1)
            if last.year-first.year<=30:
                years.update(range(first.year,last.year+1))
        if not months:
            first=date.fromisoformat(row['valid_from']);last=date.fromisoformat(row['valid_until'])-timedelta(days=1)
            months.update(range(1,13) if (last-first).days>=365 else
                              { (first+timedelta(days=d)).month for d in range((last-first).days+1)})
        result[row['id']]={'tags':tags,'years':years,'months':months,'networks':networks}
    return result


def options(db):
    rows=metadata_facets(db).values()
    names={r['id'].casefold():r['name'] for r in db.execute('SELECT * FROM network')}
    groups={key:set().union(*(r[key] for r in rows)) for key in ('tags','years','months','networks')}
    return {key:[{'value':v,'label':calendar.month_name[v] if key=='months' else names.get(v,v) if key=='networks' else str(v)}
                 for v in sorted(values)] for key,values in groups.items()}


def matches(facets,rules):
    return all(not rules.get(key) or set(rules[key]) & facets[key] for key in ('years','months','networks'))
