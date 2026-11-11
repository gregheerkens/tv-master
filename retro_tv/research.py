"""Bounded daily-page research, offline JSON interchange and explicit acceptance.

No AI, no title guessing and no writes to published programming. HTML from public
sources is untrusted data; only the recognized listing surface is parsed.
"""
import hashlib
import ipaddress
import json
import re
import socket
import uuid
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo

from .records import utc_now
from .manager import timestamp

MAX_BYTES=1500000
MONTHS='January February March April May June July August September October November December'.split()
CLOCK=re.compile(r'^(\d{1,2}):(\d{2})\s*([ap])\.?m\.?$',re.I)
UNKNOWN={'','unknown','tba','tbd','?','n/a'}


def clean(value):
    return re.sub(r'\s+',' ',re.sub(r'\[\d+\]','',value)).strip()


class ListingHTML(HTMLParser):
    """Extract table cells/rowspans, or the Kids Block Blog's post body lines."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables=[];self.depth=0;self.table=None;self.row=None;self.cell=None
        self.ignore=0;self.post_depth=0;self.post=[];self.headings=[];self.heading=None

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('h1','h2','title'):self.heading=''
        if tag in ('script','style'):self.ignore+=1
        if tag=='div':
            if self.post_depth:self.post_depth+=1
            elif 'entry-content' in attrs.get('class','').split():self.post_depth=1
        if self.post_depth and tag in ('br','p','li'):self.post.append('\n')
        if tag=='table':
            if not self.depth:self.table=[]
            self.depth+=1
        if self.depth==1:
            if tag=='tr':self.row=[]
            elif tag in ('td','th') and self.row is not None:
                try:span=int(attrs.get('rowspan','1'));cols=int(attrs.get('colspan','1'))
                except ValueError:span=cols=1
                self.cell={'text':'','span':min(100,max(1,span)),'cols':min(20,max(1,cols))}
            elif tag=='br' and self.cell is not None:self.cell['text']+=' / '

    def handle_endtag(self,tag):
        if tag in ('h1','h2','title') and self.heading is not None:self.headings.append(self.heading);self.heading=None
        if tag in ('script','style'):self.ignore=max(0,self.ignore-1)
        if self.post_depth and tag in ('p','li'):self.post.append('\n')
        if tag=='div' and self.post_depth:self.post_depth-=1
        if self.depth==1:
            if tag in ('td','th') and self.cell is not None:
                self.row.append(self.cell);self.cell=None
            elif tag=='tr' and self.row is not None:
                self.table.append(self.row);self.row=None
        if tag=='table':
            self.depth=max(0,self.depth-1)
            if not self.depth and self.table is not None:self.tables.append(self.table);self.table=None

    def handle_data(self,data):
        if self.ignore:return
        if self.heading is not None:self.heading+=data
        if self.cell is not None and self.depth==1:self.cell['text']+=data
        if self.post_depth:self.post.append(data)


def expand(table):
    carry={};rows=[]
    for source_index,raw in enumerate(table):
        row={i:text for i,(text,left) in carry.items()};next_carry={i:(text,left-1) for i,(text,left) in carry.items() if left>1}
        col=0
        for cell in raw:
            while col in row:col+=1
            for n in range(cell['cols']):
                row[col]=(clean(cell['text']) if n==0 else '',source_index)
                if cell['span']>1:next_carry[col]=(row[col],cell['span']-1)
                col+=1
        rows.append([row.get(i,('',-1)) for i in range(max(row,default=-1)+1)]);carry=next_carry
    return rows


def minutes(value):
    match=CLOCK.fullmatch(clean(value))
    if not match:raise ValueError('unsupported clock '+value)
    h,m,period=match.groups();h=int(h);m=int(m)
    if not 1<=h<=12 or not 0<=m<=59:raise ValueError('invalid clock')
    return (h%12+(12 if period.lower()=='p' else 0))*60+m


def local_stamp(day,minute,zone):
    naive=datetime.combine(day,time.min)+timedelta(minutes=minute)
    stamp=naive.replace(tzinfo=zone)
    # Ambiguous/missing DST hours cannot silently acquire a guessed offset.
    if stamp.utcoffset()!=naive.replace(tzinfo=zone,fold=1).utcoffset():
        raise ValueError('ambiguous or nonexistent DST clock; use explicit-offset JSON')
    return stamp.isoformat()


def parse_html(body,day,timezone,adapter,*,include_tail=False):
    parser=ListingHTML();parser.feed(body);rows=[];warnings=[]
    source_day=date.fromisoformat(day)
    label=f'{MONTHS[source_day.month-1]} {source_day.day}, {source_day.year}'
    if not any(label.casefold() in clean(h).casefold() or day in clean(h) for h in parser.headings):
        raise ValueError('Source heading does not establish the requested date; no coverage claimed')
    if adapter=='mediawiki_daily':
        for table in parser.tables:
            expanded=expand(table)
            for i,row in enumerate(expanded):
                names=[v[0].lower() for v in row]
                if 'time' in names and ('show' in names or 'program' in names):
                    ti=names.index('time');si=names.index('show') if 'show' in names else names.index('program');ei=names.index('episode') if 'episode' in names else None
                    for cells in expanded[i+1:]:
                        if len(cells)>max(ti,si):rows.append((cells[ti][0],cells[si][0],cells[ei][0] if ei is not None and len(cells)>ei else '',(cells[si][1],cells[ei][1] if ei is not None and len(cells)>ei else -1)))
                    break
        if not rows:raise ValueError('No recognizable Time / Show listing table; no coverage claimed')
    elif adapter=='kidsblock_post':
        for line in ''.join(parser.post).splitlines():
            match=re.match(r'^\s*(\d{1,2}:\d{2}\s*[AP]M)\s*(.*)$',line,re.I)
            if not match:continue
            clock,text=match.groups();title,sep,episode=text.partition(':')
            rows.append((clock,title.strip(),episode.strip(' “”:') ,len(rows)))
        if not rows:raise ValueError('No timed listings in entry-content; no coverage claimed')
    else:raise ValueError('unknown source adapter')
    zone=ZoneInfo(timezone);day=date.fromisoformat(day);stamps=[];previous=-1;rollover=0
    for index,(clock,title,episode,group) in enumerate(rows):
        try:minute=minutes(clock)
        except ValueError:
            # A damaged clock can conceal a boundary. Do not bridge across it.
            if title:warnings.append(f'Unparsed clock at source row {index+1}: {clock}');stamps.append(None)
            continue
        if minute<previous:
            if previous>=18*60 and minute<6*60 and not rollover:rollover=1440
            else:raise ValueError('nonmonotonic schedule times; review source manually')
        previous=minute
        try:stamp=local_stamp(day,minute+rollover,zone)
        except ValueError as error:warnings.append(str(error));stamps.append(None);continue
        stamps.append({'row':index,'group':group,'start':stamp,'title':clean(title),'episode_title':clean(episode)})
    # A rowspan can represent one longer airing, not repeated half-hour shows.
    grouped=[]
    for stamp in stamps:
        if stamp and grouped and grouped[-1] and stamp['group']==grouped[-1]['group']:continue
        grouped.append(stamp)
    candidates=[]
    for current,following in zip(grouped,grouped[1:]):
        if not current or not following:continue
        if current['title'].casefold() in UNKNOWN:continue
        duration=timestamp(following['start'])-timestamp(current['start'])
        if not 0<duration<=4*3600000:
            warnings.append(f'Uncertain duration at {current["start"]}; slot omitted');continue
        current={k:v for k,v in current.items() if k!='group'}
        candidates.append({**current,'end':following['start'],'evidence_state':'schedule_exact','content_id':None})
    if include_tail and grouped and grouped[-1] and grouped[-1]['title'].casefold() not in UNKNOWN:
        tail={k:v for k,v in grouped[-1].items() if k!='group'};candidates.append({**tail,'end':None,'pending_boundary':True})
    warnings.append('Imported listings may need a quick check; source details are available on each slot.')
    if not candidates:raise ValueError('No bounded program slots; no coverage claimed')
    return candidates,warnings



def close_tail(tail,following,next_day,timezone):
    """Poll next day first; represent inclusive 23:59 as an exclusive midnight end."""
    from .identities import show_key,episode_key
    midnight=local_stamp(date.fromisoformat(next_day),0,ZoneInfo(timezone))
    first=following[0] if following else None
    if not first or first['start']!=midnight:raise ValueError('The first slot of the next day is not yet known')
    same=first and first['start']==midnight and show_key(first['title'])==show_key(tail['title'])
    if same and tail.get('episode_title') and first.get('episode_title'):
        same=episode_key(tail['episode_title'])==episode_key(first['episode_title'])
    end=first.get('end') if same else midnight
    if not end:raise ValueError('The next-day continuation still has no end boundary')
    result={**tail,'end':end,'boundary_inferred':True,
        'end_basis':'next-day continuation' if same else 'next-day first slot differs; inferred 23:59 inclusive'}
    result.pop('pending_boundary',None)
    if timestamp(end)-timestamp(tail['start'])>12*3600000:raise ValueError('Late slot continuation is too long')
    return result


def public_url(url):
    parts=urlsplit(url)
    if parts.scheme!='https' or not parts.hostname or parts.username or parts.password or parts.port not in (None,443):
        raise ValueError('sources must use public HTTPS URLs without credentials')
    for info in socket.getaddrinfo(parts.hostname,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(info[4][0]).is_global:raise ValueError('private/local source addresses are not supported')
    return url


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        public_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def fetch_html(url):
    public_url(url)
    request=Request(url,headers={'User-Agent':'TV-Master/0.1 (personal historical schedule research)','Accept':'text/html'})
    with build_opener(PublicRedirect()).open(request,timeout=15) as response:
        if response.headers.get_content_type() not in ('text/html','application/xhtml+xml'):raise ValueError('source did not return HTML')
        data=response.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES:raise ValueError('source exceeds 1.5 MB limit')
        return data.decode(response.headers.get_content_charset() or 'utf-8',errors='replace')


def page_url(template,day):
    d=date.fromisoformat(day)
    return template.format(date=day,year=d.year,month=f'{d.month:02}',day=d.day,
        wiki_date=quote(f'{MONTHS[d.month-1]} {d.day}, {d.year}'.replace(' ','_'),safe=''))


def create_batch(db,value):
    service=value['service_id'];start=date.fromisoformat(value['start_date']);until=date.fromisoformat(value['until_date'])
    if not db.execute('SELECT 1 FROM service WHERE id=?',(service,)).fetchone():raise ValueError('unknown service')
    if not 0<(until-start).days<=31:raise ValueError('research 1 to 31 days, with an exclusive end date')
    timezone=value.get('timezone') or db.execute('SELECT timezone FROM state').fetchone()[0];ZoneInfo(timezone)
    adapter=value.get('adapter','mediawiki_daily')
    if adapter not in ('mediawiki_daily','kidsblock_post','sideload'):raise ValueError('unknown source adapter')
    template=value.get('url_template','')
    if adapter!='sideload':
        # Validate structure here, resolve public host only when actually fetching.
        url=page_url(template,str(start));parts=urlsplit(url)
        if parts.scheme!='https' or not parts.hostname or parts.username or parts.password:raise ValueError('provide an HTTPS source URL/template')
    ident=uuid.uuid4().hex
    with db:
        db.execute('INSERT INTO research_batch VALUES (?,?,?,?,?,?,?,?)',(ident,service,str(start),str(until),timezone,adapter,template,utc_now()))
        for offset in range((until-start).days):
            day=str(start+timedelta(days=offset));url=page_url(template,day) if template else ''
            db.execute('INSERT INTO research_page(id,batch_id,day,url,status) VALUES (?,?,?,?,?)',(uuid.uuid4().hex,ident,day,url,'pending'))
    return detail(db,ident)


def detail(db,ident):
    batch=db.execute('SELECT * FROM research_batch WHERE id=?',(ident,)).fetchone()
    if not batch:raise ValueError('unknown research batch')
    pages=[]
    for row in db.execute('SELECT * FROM research_page WHERE batch_id=? ORDER BY day',(ident,)):
        page=dict(row);page.pop('body');boundary=db.execute('SELECT status,next_url,error FROM research_boundary WHERE page_id=?',(page['id'],)).fetchone();page['boundary']=dict(boundary) if boundary else None;page['candidates']=json.loads(page['candidates']);page['warnings']=json.loads(page['warnings']);page['accepted_listings']=[dict(r) for r in db.execute('SELECT r.candidate_index,a.id,a.content_id,a.evidence_state,a.start_ms,a.end_ms FROM research_acceptance r JOIN historical_airing a ON a.id=r.airing_id WHERE r.page_id=?',(page['id'],))];pages.append(page)
    return {**dict(batch),'pages':pages}


def overview(db):
    return {'batches':[detail(db,row[0]) for row in db.execute('SELECT id FROM research_batch ORDER BY created_at DESC LIMIT 30')],
        'services':[dict(row) for row in db.execute('SELECT id,name FROM service ORDER BY name')],
        'contents':[dict(row) for row in db.execute("SELECT id,title,episode_title,kind FROM content WHERE kind IN ('program','episode','movie','series') ORDER BY title")],
        'timezone':db.execute('SELECT timezone FROM state').fetchone()[0]}


def fetch_page(db,value,fetcher=None):
    page=db.execute('SELECT * FROM research_page WHERE id=?',(value['page_id'],)).fetchone()
    if not page:raise ValueError('unknown research page')
    if page['status']=='accepted':return detail(db,page['batch_id'])
    cached=page['status']=='staged'
    if cached and not (value.get('retry_boundary') or value.get('next_html')):return detail(db,page['batch_id'])
    batch=db.execute('SELECT * FROM research_batch WHERE id=?',(page['batch_id'],)).fetchone()
    if batch['adapter']=='sideload':raise ValueError('import a research JSON bundle for a sideload batch')
    try:
        body=value.get('html',page['body'] if cached else None)
        if body is None:body=(fetcher or fetch_html)(page['url'])
        if not isinstance(body,str) or len(body.encode())>MAX_BYTES:raise ValueError('saved HTML must be at most 1.5 MB')
        parsed,warnings=parse_html(body,page['day'],batch['timezone'],batch['adapter'],include_tail=True)
        candidates=[r for r in parsed if r.get('end')]
        tail=next((r for r in parsed if not r.get('end')),None)
        if tail and datetime.fromisoformat(tail['start']).hour>=23:
            next_day=str(date.fromisoformat(page['day'])+timedelta(days=1))
            next_url=value.get('next_day_url') or page_url(batch['url_template'],next_day)
            try:
                next_body=value.get('next_html')
                if next_body is None:
                    if next_url==page['url']:raise ValueError('Next-day URL is needed for this source')
                    next_body=(fetcher or fetch_html)(next_url)
                following,_=parse_html(next_body,next_day,batch['timezone'],batch['adapter'],include_tail=True)
                resolved=close_tail(tail,following,next_day,batch['timezone'])
                candidates.append(resolved)
                with db:db.execute('INSERT OR REPLACE INTO research_boundary VALUES (?,?,?,?,?,?)',(page['id'],json.dumps(tail),next_url,'resolved',None,next_body))
            except (OSError,ValueError) as error:
                warnings.append('Late slot: next-day lookup is pending.')
                with db:db.execute('INSERT OR REPLACE INTO research_boundary VALUES (?,?,?,?,?,?)',(page['id'],json.dumps(tail),next_url,'pending',str(error),None))
        with db:db.execute('UPDATE research_page SET fetched_at=?,sha256=?,body=?,status=\'staged\',error=NULL,candidates=?,warnings=? WHERE id=? AND status IN (\'pending\',\'failed\',\'staged\')',
            (utc_now(),hashlib.sha256(body.encode()).hexdigest(),body,json.dumps(candidates),json.dumps(warnings),page['id']))
    except (OSError,ValueError) as error:
        with db:db.execute("UPDATE research_page SET status='failed',error=? WHERE id=? AND status IN ('pending','failed')",(str(error),page['id']))
    return detail(db,page['batch_id'])


def sideload(db,value):
    """Portable JSON from browsing, another host or an offline scraper, still staged."""
    if not isinstance(value,dict) or value.get('version')!=1:raise ValueError('research bundle version must be 1')
    pages=value['pages'];start=date.fromisoformat(value['start_date']);until=date.fromisoformat(value['until_date'])
    if not isinstance(pages,list) or len(pages)>31:raise ValueError('at most 31 source pages per bundle')
    normalized=[];seen=set()
    for page in pages:
        if not isinstance(page,dict):raise ValueError('source pages must be objects')
        day=page['day']
        if not start<=date.fromisoformat(day)<until or day in seen:raise ValueError('source dates must be unique and inside the requested period')
        seen.add(day);url=page['url'];parts=urlsplit(url)
        if parts.scheme!='https' or not parts.hostname:raise ValueError('each sideload page needs its source HTTPS URL')
        if not page.get('retrieved_at') or not page.get('retrieval_method'):raise ValueError('sideload pages need retrieval date and method')
        candidates=page.get('candidates',[])
        if not isinstance(candidates,list) or len(candidates)>200:raise ValueError('at most 200 candidates per day')
        for row in candidates:
            if not isinstance(row,dict):raise ValueError('listing candidates must be objects')
            a,b=timestamp(row['start']),timestamp(row['end'])
            if not 0<b-a<=4*3600000 or not row.get('title','').strip():raise ValueError('invalid candidate title/duration')
            if row.get('evidence_state','schedule_exact') not in ('exact','schedule_exact','seasonal','inferred'):raise ValueError('invalid evidence state')
            zone=ZoneInfo(value['timezone']);d=datetime.fromtimestamp(a/1000,zone).date()
            if d not in (date.fromisoformat(day),date.fromisoformat(day)+timedelta(days=1)):raise ValueError('candidate outside source day')
        normalized.append((page,candidates))
    # One transaction, including batch creation (create_batch normally commits).
    # Prevalidation above leaves no half imported source on ordinary input errors.
    result=create_batch(db,{**value,'adapter':'sideload','url_template':''})
    try:
        with db:
            for page,candidates in normalized:
                payload=json.dumps(page,sort_keys=True)
                db.execute("UPDATE research_page SET url=?,fetched_at=?,sha256=?,body=?,status='staged',candidates=?,warnings=? WHERE batch_id=? AND day=?",
                    (page['url'],page['retrieved_at'],hashlib.sha256(payload.encode()).hexdigest(),payload,json.dumps(candidates),
                     json.dumps(page.get('warnings',[])+[f'Sideloaded via {page["retrieval_method"]}; verify source claims before accepting.']),result['id'],page['day']))
    except Exception:
        with db:
            db.execute('DELETE FROM research_page WHERE batch_id=?',(result['id'],));db.execute('DELETE FROM research_batch WHERE id=?',(result['id'],))
        raise
    return detail(db,result['id'])


def accept(db,value):
    page=db.execute('SELECT * FROM research_page WHERE id=?',(value['page_id'],)).fetchone()
    if not page:raise ValueError('unknown research page')
    if page['status']=='accepted':return {'status':'Already accepted; no schedule changes','batch':detail(db,page['batch_id'])}
    if page['status']!='staged':raise ValueError('fetch or sideload this page before acceptance')
    batch=db.execute('SELECT * FROM research_batch WHERE id=?',(page['batch_id'],)).fetchone()
    rows=json.loads(page['candidates']);selections=value['selections'];seen=set()
    if not isinstance(selections,list) or not selections:raise ValueError('select at least one bounded listing')
    prepared=[]
    for selection in selections:
        if not isinstance(selection,dict):raise ValueError('listing selections must be objects')
        index=selection['index']
        if type(index) is not int or not 0<=index<len(rows) or index in seen:raise ValueError('invalid or duplicate candidate index')
        seen.add(index);row=rows[index];evidence=selection.get('evidence_state','schedule_exact');content_id=selection.get('content_id') or None
        if evidence not in ('exact','schedule_exact','seasonal','inferred'):raise ValueError('invalid evidence state')
        content=db.execute('SELECT * FROM content WHERE id=?',(content_id,)).fetchone() if content_id else None
        if content_id and (not content or content['kind'] not in ('program','episode','movie','series')):raise ValueError('choose a catalog program identity')
        if evidence=='exact' and (not content or content['kind'] not in ('episode','movie') or selection.get('episode_confirmed') is not True):
            raise ValueError('exact evidence requires an identified catalog episode/movie and explicit confirmation')
        a,b=timestamp(row['start']),timestamp(row['end'])
        key=hashlib.sha256(json.dumps([batch['service_id'],a,b,row['title']],ensure_ascii=False).encode()).hexdigest()[:28]
        provenance={'url':page['url'],'retrieved_at':page['fetched_at'],'sha256':page['sha256'],'research_page':page['id'],
            'source_episode_text':row.get('episode_title',''),'review_note':selection.get('note',''),'needs_check':True,'boundary_source':row.get('boundary_source'),'episode_reference':row.get('episode_reference'),'episode_origin':row.get('episode_origin','listing'),'boundary_inferred':row.get('boundary_inferred',False),'end_basis':row.get('end_basis','next listed start')}
        if content_id is None:content_id='auto:'+str(index)
        prepared.append((index,('research:'+key,batch['service_id'],content_id,row['title'],a,b,evidence,json.dumps(provenance))))
    with db:
        for index,row in prepared:
            if row[2].startswith('auto:'):
                from .identities import resolve
                candidate=rows[index];ident=resolve(db,candidate['title'],candidate.get('episode_title',''))
                row=(*row[:2],ident,*row[3:])
            existing=db.execute('SELECT * FROM historical_airing WHERE id=?',(row[0],)).fetchone()
            if existing:
                if tuple(existing)[1:7]!=row[1:7]:raise ValueError('conflicting accepted listing; existing evidence was preserved')
            else:
                if db.execute('SELECT 1 FROM historical_airing WHERE service_id=? AND start_ms<? AND end_ms>?',(row[1],row[5],row[4])).fetchone():
                    raise ValueError('source overlaps existing accepted evidence; review the conflict before importing')
                db.execute('INSERT INTO historical_airing VALUES (?,?,?,?,?,?,?,?)',row)
            db.execute('INSERT INTO research_acceptance VALUES (?,?,?)',(page['id'],index,row[0]))
        db.execute("UPDATE research_page SET status='accepted',accepted_at=? WHERE id=?",(utc_now(),page['id']))
    return {'status':f'Accepted {len(prepared)} sourced slots; published guide unchanged','batch':detail(db,page['batch_id'])}


def export_bundle(db,ident):
    batch=detail(db,ident)
    return {'version':1,'service_id':batch['service_id'],'start_date':batch['start_date'],'until_date':batch['until_date'],'timezone':batch['timezone'],
        'pages':[{'day':p['day'],'url':p['url'],'retrieved_at':p['fetched_at'],'retrieval_method':'TV Master '+batch['adapter'],
                  'candidates':p['candidates'],'warnings':p['warnings']} for p in batch['pages'] if p['status'] in ('staged','accepted')]}


def enrich_episodes(db,value):
    """Merge supplemental episode references into matching slots, never shift time.

    A date-only premiere lookup is usable when the show has one slot that day;
    multiple possible slots stay unresolved. Such identities carry a small flag.
    """
    from .identities import show_key,resolve
    service=value['service_id'];zone=ZoneInfo(value.get('timezone') or db.execute('SELECT timezone FROM state').fetchone()[0]);updated=0;unresolved=[]
    with db:
        for fact in value['episodes']:
            if not fact.get('url') or not fact.get('episode_title'):raise ValueError('Episode references need a title and source URL')
            if fact.get('start'):
                matches=list(db.execute('SELECT * FROM historical_airing WHERE service_id=? AND start_ms=?',(service,timestamp(fact['start']))))
            else:
                day=date.fromisoformat(fact['date']);a=local_stamp(day,0,zone);b=local_stamp(day+timedelta(days=1),0,zone)
                matches=list(db.execute('SELECT * FROM historical_airing WHERE service_id=? AND start_ms>=? AND start_ms<?',(service,timestamp(a),timestamp(b))))
            matches=[r for r in matches if show_key(r['title'])==show_key(fact['title'])]
            if len(matches)!=1:unresolved.append(fact);continue
            row=matches[0];provenance=json.loads(row['provenance']);provenance=provenance if isinstance(provenance,dict) else {'original':provenance}
            current=provenance.get('source_episode_text')
            from .identities import episode_key
            if current and episode_key(current)!=episode_key(fact['episode_title']):unresolved.append(fact);continue
            ident=resolve(db,row['title'],fact['episode_title'])
            provenance.update(source_episode_text=fact['episode_title'],episode_reference=fact['url'],needs_check=True,
                episode_origin='additional listing' if fact.get('start') else 'premiere-date lookup; one matching slot')
            db.execute('UPDATE historical_airing SET content_id=?,provenance=? WHERE id=?',(ident,json.dumps(provenance),row['id']));updated+=1
    return {'status':f'Added {updated} episode titles','unresolved':unresolved}
