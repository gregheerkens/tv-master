"""Content identities, channel history, eligibility and personal library records."""
import json
from datetime import date, datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def backfill(db):
    """Give legacy rows stable identities without touching broadcast snapshots."""
    db.execute("INSERT OR IGNORE INTO content(id,kind,title) SELECT 'asset:'||id,kind,title FROM asset")
    db.execute("INSERT OR IGNORE INTO asset_content SELECT id,'asset:'||id FROM asset")
    db.execute("INSERT OR IGNORE INTO content(id,kind,title) SELECT 'program:'||id,'program',title FROM program")
    db.execute("INSERT OR IGNORE INTO program_content SELECT id,'program:'||id FROM program")
    db.execute("INSERT OR IGNORE INTO channel_profile(service_id,mode) SELECT id,'custom' FROM service")


def bracket(item):
    a,b=item['valid_from'],item['valid_until']
    if date.fromisoformat(a)>=date.fromisoformat(b):
        raise ValueError('date window must have a later exclusive end')
    if item['evidence_state'] not in ('verified','estimated','user_defined'):
        raise ValueError('invalid evidence state')
    if not item.get('provenance'):
        raise ValueError('dated assertions require provenance')
    return a,b


def strings(value):
    if not isinstance(value,list) or any(not isinstance(v,str) or not v for v in value):
        raise ValueError('expected a list of nonempty strings')
    return json.dumps(value)


def import_records(db, document):
    """Transactional metadata-only import. No media tools or live-guide edits."""
    if document.get('version')!=1:
        raise ValueError('records version must be 1')
    with db:
        backfill(db)
        for item in document.get('contents',[]):
            original=item.get('original_air_date')
            if original:
                date.fromisoformat(original)
                if not item.get('date_evidence'):
                    raise ValueError('original air date requires evidence')
            for key in ('season_number','episode_number'):
                value=item.get(key)
                if value is not None and (type(value) is not int or value<0):
                    raise ValueError(f'{key} must be a nonnegative integer or null')
            db.execute('INSERT INTO content VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (item['id'],item['kind'],item['title'],item.get('parent_id'),
                 item.get('episode_title'),item.get('season_number'),item.get('episode_number'),
                 original,item.get('date_evidence'),
                 json.dumps(item['episode_metadata']) if item.get('episode_metadata') is not None else None,
                 item.get('description'),strings(item.get('tags',[]))))
        for key,table,identifier in [('asset_links','asset_content','asset_id'),
                                      ('program_links','program_content','program_id')]:
            for item in document.get(key,[]):
                # Reidentification affects future composition, never source files or playout rows.
                db.execute(f'INSERT INTO {table} VALUES (?,?) ON CONFLICT({identifier}) DO UPDATE SET content_id=excluded.content_id',
                           (item[identifier],item['content_id']))
        for item in document.get('networks',[]):
            db.execute('INSERT INTO network VALUES (?,?)',(item['id'],item['name']))
        for item in document.get('channels',[]):
            db.execute('INSERT INTO channel_profile VALUES (?,?,?) ON CONFLICT(service_id) DO UPDATE SET mode=excluded.mode,theme_tags=excluded.theme_tags',
                       (item['service_id'],item['mode'],strings(item.get('theme_tags',[]))))
        for item in document.get('station_history',[]):
            a,b=bracket(item)
            db.execute('INSERT INTO station_history VALUES (?,?,?,?,?,?,?,?,?)',
                (item['id'],item['service_id'],item['market_id'],item['call_sign'],
                 str(item['broadcast_channel']),a,b,item['evidence_state'],json.dumps(item['provenance'])))
        for item in document.get('affiliations',[]):
            a,b=bracket(item)
            db.execute('INSERT INTO affiliation_history VALUES (?,?,?,?,?,?,?)',
                (item['id'],item['service_id'],item['network_id'],a,b,
                 item['evidence_state'],json.dumps(item['provenance'])))
        for item in document.get('windows',[]):
            a,b=bracket(item)
            months=item.get('months',[])
            if not isinstance(months,list) or any(type(m) is not int or not 1<=m<=12 for m in months):
                raise ValueError('months must be integers 1 through 12')
            db.execute('INSERT INTO eligibility_window VALUES (?,?,?,?,?,?,?,?,?,?)',
                (item['id'],item['content_id'],a,b,item.get('service_id'),item.get('network_id'),
                 item.get('market_id'),json.dumps(months),item['evidence_state'],json.dumps(item['provenance'])))


def set_preference(db, identifier, *, recording=False, excluded=True, note=None):
    if type(excluded) is not bool:
        raise ValueError('excluded must be boolean')
    table,key,field=('recording_preference','asset_id','excluded') if recording else ('content_preference','content_id','never_schedule')
    with db:
        db.execute(f'INSERT INTO {table}({key},{field},note) VALUES (?,?,?) ON CONFLICT({key}) DO UPDATE SET {field}=excluded.{field},note=excluded.note',
                   (identifier,int(excluded),note))


def quality(db, asset_id, score, assessment):
    if score is not None and (type(score) is not int or not 0<=score<=100):
        raise ValueError('quality score must be 0 through 100 or null')
    with db:
        db.execute('INSERT INTO recording_quality VALUES (?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET score=excluded.score,assessment=excluded.assessment,assessed_at=excluded.assessed_at',
                   (asset_id,score,assessment,utc_now()))


def set_favorite(db,content_id,favorite=True):
    with db:
        db.execute('INSERT INTO content_preference(content_id,favorite) VALUES (?,?) ON CONFLICT(content_id) DO UPDATE SET favorite=excluded.favorite',
                   (content_id,int(favorite)))


def alert(db, ident, *, code, details, source_id=None, asset_id=None, severity='warning'):
    with db:
        db.execute('INSERT INTO quality_alert VALUES (?,?,?,?,?,?,?,NULL)',
                   (ident,source_id,asset_id,code,severity,details,utc_now()))


def record_view(db, ident, segment_id, viewer_id, watched_ms, *, now_ms):
    row=db.execute('SELECT start_ms,end_ms FROM segment WHERE id=?',(segment_id,)).fetchone()
    if row is None or row['start_ms']>=now_ms:
        raise ValueError('cannot record viewing of an unaired segment')
    available=min(now_ms,row['end_ms'])-row['start_ms']
    if type(watched_ms) is not int or not 0<watched_ms<=available:
        raise ValueError('watch duration exceeds aired segment duration')
    with db:
        # Repeated submission of the same event ID must not inflate viewing counts.
        existing=db.execute('SELECT segment_id,viewer_id,watched_ms FROM viewing_event WHERE id=?',(ident,)).fetchone()
        if existing:
            if tuple(existing)!=(segment_id,viewer_id,watched_ms):
                raise ValueError('view event ID already belongs to different data')
            return
        db.execute('INSERT INTO viewing_event VALUES (?,?,?,?,?)',
                   (ident,segment_id,viewer_id,watched_ms,utc_now()))


def channel_lookup(db, market_id, provider_id, day):
    """Resolve local imported history; never fabricate station/affiliation facts."""
    date.fromisoformat(day)
    rows=db.execute('''SELECT s.id,s.name,e.channel AS cable_channel,p.mode,p.theme_tags,
      h.call_sign,h.broadcast_channel,h.evidence_state AS station_evidence,h.provenance AS station_provenance,
      n.name AS network,a.evidence_state AS affiliation_evidence,a.provenance AS affiliation_provenance
      FROM service s JOIN lineup_entry e ON e.service_id=s.id
      JOIN lineup l ON l.id=e.lineup_id JOIN provider pr ON pr.id=l.provider_id
      LEFT JOIN channel_profile p ON p.service_id=s.id
      LEFT JOIN station_history h ON h.service_id=s.id AND h.market_id=pr.market_id AND h.valid_from<=? AND h.valid_until>?
      LEFT JOIN affiliation_history a ON a.service_id=s.id AND a.valid_from<=? AND a.valid_until>?
      LEFT JOIN network n ON n.id=a.network_id
      WHERE pr.market_id=? AND pr.id=? AND l.valid_from<=? AND l.valid_until>?
      ORDER BY length(e.channel),e.channel''',(day,day,day,day,market_id,provider_id,day,day))
    return [dict(row) for row in rows]


class Policy:
    """One catalog snapshot per composed block; published blocks never re-evaluate it."""
    def __init__(self,db):
        self.asset_ids=dict(db.execute('SELECT asset_id,content_id FROM asset_content'))
        self.program_ids=dict(db.execute('SELECT program_id,content_id FROM program_content'))
        self.blocked={r[0] for r in db.execute('SELECT content_id FROM content_preference WHERE never_schedule=1')}
        self.recordings={r[0] for r in db.execute('SELECT asset_id FROM recording_preference WHERE excluded=1')}
        self.parents=dict(db.execute('SELECT id,parent_id FROM content'))
        self.tags={r['id']:{t.casefold() for t in json.loads(r['tags'])} for r in db.execute('SELECT id,tags FROM content')}
        self.windows={}
        for row in db.execute('SELECT * FROM eligibility_window'):
            self.windows.setdefault(row['content_id'],[]).append(dict(row))
        self.affiliations=[dict(r) for r in db.execute('SELECT * FROM affiliation_history')]
        self.markets=[dict(r) for r in db.execute('SELECT e.service_id,p.market_id,l.valid_from,l.valid_until FROM lineup_entry e JOIN lineup l ON l.id=e.lineup_id JOIN provider p ON p.id=l.provider_id')]
        self.profiles={r['service_id']:dict(r) for r in db.execute('SELECT * FROM channel_profile')}
        self.reuse={r['id']:json.loads(r['metadata']).get('reuse_rule') for r in db.execute('SELECT id,metadata FROM asset')}
        self.selections={r['service_id']:json.loads(r['rules']) for r in db.execute('SELECT * FROM selection_rule')}

    def allowed(self,identifier,service,day,*,program=False):
        if not program and identifier in self.recordings:
            return False
        if not program and self.reuse.get(identifier):
            from .ingest import reuse_allowed
            if not reuse_allowed(self.reuse[identifier],day):return False
        content=(self.program_ids if program else self.asset_ids).get(identifier)
        visited=set()
        while content:
            if content in visited:
                return False
            visited.add(content)
            if content in self.blocked:
                return False
            windows=self.windows.get(content,[])
            if windows and not any(self.window_matches(w,service,day) for w in windows):
                return False
            content=self.parents.get(content)
        if program:
            profile=self.profiles.get(service,{})
            if profile.get('mode')=='themed':
                wanted={t.casefold() for t in json.loads(profile['theme_tags'])}
                available=set().union(*(self.tags.get(c,set()) for c in visited))
                if wanted and not wanted.intersection(available):
                    return False
        rules=self.selections.get(service,{})
        available=set().union(*(self.tags.get(c,set()) for c in visited))
        if program:
            if rules.get('tags') and not set(rules['tags']).intersection(available):return False
            if set(rules.get('exclude_tags',[])).intersection(available):return False
            if rules.get('content_ids') and not set(rules['content_ids']).intersection(visited):return False
            if set(rules.get('exclude_content_ids',[])).intersection(visited):return False
        elif rules.get('continuity_tags') and not set(rules['continuity_tags']).intersection(available):return False
        return True

    def window_matches(self,w,service,day):
        months=json.loads(w['months'])
        return (w['valid_from']<=day<w['valid_until']
                and (not months or int(day[5:7]) in months)
                and (w['service_id'] is None or w['service_id']==service)
                and (w['market_id'] is None or any(m['service_id']==service and m['market_id']==w['market_id'] and m['valid_from']<=day<m['valid_until'] for m in self.markets))
                and (w['network_id'] is None or any(a['service_id']==service and a['network_id']==w['network_id'] and a['valid_from']<=day<a['valid_until'] for a in self.affiliations)))


def content_stats(db,content_id,now_ms):
    # Count one episode per broadcast even when it has several act segments.
    broadcasts={r[0] for r in db.execute('SELECT b.id FROM broadcast b JOIN program_content p ON p.program_id=b.program_id WHERE p.content_id=?',(content_id,))}
    segments=list(db.execute('''SELECT s.id,s.start_ms,s.end_ms,s.broadcast_id FROM segment s
        JOIN asset_content a ON a.asset_id=s.asset_id WHERE a.content_id=?''',(content_id,)))
    standalone=[s for s in segments if s['broadcast_id'] not in broadcasts]
    aired=db.execute('''SELECT count(*) FROM broadcast b JOIN program_content p ON p.program_id=b.program_id
                      WHERE p.content_id=? AND b.start_ms<?''',(content_id,now_ms)).fetchone()[0]
    views=db.execute('''SELECT count(*),coalesce(sum(v.watched_ms),0) FROM viewing_event v JOIN segment s ON s.id=v.segment_id
      LEFT JOIN asset_content a ON a.asset_id=s.asset_id JOIN broadcast b ON b.id=s.broadcast_id
      LEFT JOIN program_content p ON p.program_id=b.program_id WHERE a.content_id=? OR p.content_id=?''',(content_id,content_id)).fetchone()
    return {'content_id':content_id,'scheduled_occurrences':len(broadcasts)+len(standalone),
            'aired_occurrences':aired+sum(s['start_ms']<now_ms for s in standalone),
            'viewing_events':views[0],'watched_ms':views[1]}
