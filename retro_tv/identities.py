"""Punctuation-resilient episode identities; aliases remain explicit catalog facts."""
import hashlib
import json
import re
import unicodedata


def key(text):
    text=unicodedata.normalize('NFKD',text or '').casefold().replace('&',' and ')
    text=re.sub(r'\[(?:new|confirmed|premiere|repeat|\d+)\]','',text)
    return ''.join(c for c in text if c.isalnum())


def show_key(text):
    value=key(text)
    aliases={'marytylermoore':'themarytylermooreshow','jimhensonsmuppetbabies':'muppetbabies'}
    return aliases.get(value,value)


def episode_key(text):
    # Slash and semicolon are equivalent segment separators; segment order matters.
    return key(re.sub(r'\s*(?:/|;|\s\+\s)\s*',' ',text or ''))


def numbers(text):
    found=list(re.finditer(r'\b(?:S(\d+)\s*E(\d+)|(\d+)x(\d+))\b',text,re.I))
    if len(found)!=1:return None
    m=found[0];return (int(m[1] or m[3]),int(m[2] or m[4]))


def match(db,title,episode=''):
    show=show_key(title);ep=episode_key(episode);number=numbers(episode)
    matches=[]
    for row in db.execute("SELECT * FROM content WHERE kind IN ('program','series','episode','movie')"):
        titles={show_key(row['title'])}
        if row['parent_id']:
            parent=db.execute('SELECT title FROM content WHERE id=?',(row['parent_id'],)).fetchone()
            if parent:titles.add(show_key(parent[0]))
        aliases=db.execute('SELECT title,episode_title FROM content_alias WHERE content_id=?',(row['id'],)).fetchall()
        titles.update(show_key(a['title']) for a in aliases)
        if show not in titles:continue
        episodes={episode_key(row['episode_title'])}|{episode_key(a['episode_title']) for a in aliases if a['episode_title']}
        if ep:
            if row['kind']=='episode' and (ep in episodes or (number is not None and number==(row['season_number'],row['episode_number']))):matches.append(row['id'])
        elif row['kind'] in ('program','series','movie'):matches.append(row['id'])
    return matches[0] if len(matches)==1 else None


def resolve(db,title,episode=''):
    found=match(db,title,episode)
    if found:return found
    # Keep the source's episode title even when season/episode numbering is absent.
    parent=match(db,title) or 'listed-show:'+hashlib.sha256(show_key(title).encode()).hexdigest()[:24]
    db.execute("INSERT OR IGNORE INTO content(id,kind,title) VALUES (?,'series',?)",(parent,title))
    if not episode.strip():return parent
    ident='listed-episode:'+hashlib.sha256((show_key(title)+':'+episode_key(episode)).encode()).hexdigest()[:24]
    number=numbers(episode)
    db.execute('''INSERT OR IGNORE INTO content(id,kind,title,parent_id,episode_title,season_number,episode_number,episode_metadata)
        VALUES (?,'episode',?,?,?,?,?,?)''',(ident,title,parent,episode,
        number[0] if number else None,number[1] if number else None,json.dumps({'origin':'listing','needs_check':True})))
    return ident


def backfill_listed_episodes(db):
    """Upgrade old annotation-only imports without touching any published row."""
    for row in db.execute('SELECT * FROM historical_airing').fetchall():
        provenance=json.loads(row['provenance'])
        if not isinstance(provenance,dict):continue
        episode=provenance.get('source_episode_text','')
        if not episode:continue
        current=db.execute('SELECT kind FROM content WHERE id=?',(row['content_id'],)).fetchone()
        if current and current['kind']=='episode':continue
        ident=resolve(db,row['title'],episode)
        db.execute('UPDATE historical_airing SET content_id=? WHERE id=?',(ident,row['id']))
