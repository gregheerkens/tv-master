const $ = id => document.getElementById(id), video = $('video');
const contextId=new URLSearchParams(location.search).get('context');
function scoped(path){return contextId?path+(path.includes('?')?'&':'?')+'context='+encodeURIComponent(contextId):path;}
if(contextId)document.querySelector('.manager-link').href=scoped('/manager');
const HALF_HOUR = 1800000, WINDOW = 3 * HALF_HOUR;
let data, channel, segment, selectedChannel = 0, cursor = 0, windowStart = 0;
let generation = 0, tuning = false, skew = 0, mode = 'full', futureBrowse = false;
let digits = '', digitTimer, noticeTimer;
function guideScale(){const fit=Math.min(innerWidth/640,innerHeight/480);return fit>=2?Math.floor(fit):fit;}
function sizeStage(){ $('tv-stage').style.transform=`translate(-50%,-50%) scale(${guideScale()})`; }
addEventListener('resize',sizeStage);sizeStage();
const statuses = {ready:'READY', partial:'PARTIAL / UNFILLED', missing:'CONTENT MISSING', offline:'SOURCE FILE OFFLINE', substituted:'EXPLICIT SUBSTITUTE',unknown:'LISTINGS UNKNOWN'};
async function api(path) {
  const response = await fetch(scoped(path)), value = await response.json();
  if (!response.ok) throw Error(value.error || response.statusText);
  return value;
}
function text(tag, value, className) {
  const node = document.createElement(tag); node.textContent = value;
  if (className) node.className = className;
  return node;
}
function time(ms, includeDate = false) {
  return new Date(ms).toLocaleString('en-US', {timeZone:data?.timezone || 'America/New_York',
    ...(includeDate ? {weekday:'short',month:'short',day:'numeric'} : {}), hour:'numeric',minute:'2-digit'});
}
function toast(message) {
  $('notice').textContent = message; $('notice').hidden = false;
  clearTimeout(noticeTimer); noticeTimer = setTimeout(() => $('notice').hidden = true, 4500);
}
function slateBrand(){const img=document.createElement('img');img.src='/assets/brand/logo-monochrome-cream.svg';img.alt='TV MASTER';img.className='slate-brand';return img;}
function slate(title, message) {
  $('slate').hidden = false;
  $('slate').replaceChildren(slateBrand(),text('h2',title),text('p',message));
}
function setMode(next) {
  mode = next; document.body.className = `mode-${mode}`;
  $('watch-hint').hidden = mode !== 'watch';
  if (data) render();
}
function cycleGuide() {
  setMode(mode === 'full' ? 'mini' : mode === 'mini' ? 'watch' : 'full');
}
function selected() {
  const c = data?.channels[selectedChannel];
  return {c,e:c?.entries.find(e => e.start_ms <= cursor && e.end_ms > cursor)};
}
function details() {
  const {c,e} = selected(); if (!c || !e) return;
  $('details-title').textContent = e.title+(e.content?.episode_title?' · '+e.content.episode_title:'');$('details-title').title=e.source_note||'';
  const h = e.health, reason = h.reasons?.join('. ') || 'No known coverage alerts.';
  $('details-body').textContent = `${c.channel} ${c.name} · ${time(e.start_ms,true)} – ${time(e.end_ms)}. ${statuses[h.status]}. ${reason} ${e.start_ms > data.now_ms ? 'This is a future listing. Watching tunes the channel at the current station time.' : 'The broadcast follows the station clock.'}`;
  $('details').showModal(); $('details-watch').focus();
}
function render() {
  if (!data?.channels.length) { $('selected-title').textContent = 'No channels in this dated lineup.'; return; }
  cursor = Math.max(data.now_ms,Math.min(cursor,data.until_ms - 1));
  selectedChannel = Math.max(0,Math.min(selectedChannel,data.channels.length - 1));
  if (cursor < windowStart || cursor >= windowStart + WINDOW) windowStart = Math.floor(cursor / HALF_HOUR) * HALF_HOUR;
  windowStart = Math.max(Math.floor(data.now_ms / HALF_HOUR) * HALF_HOUR,Math.min(windowStart,data.until_ms - WINDOW));
  $('clock').textContent = time(Date.now() + skew,true);
  $('guide-date').textContent = new Date(windowStart).toLocaleDateString('en-US',{timeZone:data.timezone,weekday:'long',month:'long',day:'numeric',year:'numeric'}).toUpperCase();
  $('guide-window').textContent = `72-HOUR GUIDE · ${time(windowStart)}`;
  $('times').replaceChildren(...[0,1,2].map(i => text('span',time(windowStart + i * HALF_HOUR))));
  const visible = mode === 'mini' ? 2 : 4;
  let first = Math.max(0, Math.min(selectedChannel - Math.floor(visible / 2),data.channels.length - visible));
  const rows = data.channels.slice(first,first + visible);
  $('channels').replaceChildren();
  for (const c of rows) {
    const row = document.createElement('div'); row.className = 'guide-row'; row.setAttribute('role','row');
    const station = document.createElement('button'); station.className = 'channel-cell'; station.dataset.service = c.id;
    station.setAttribute('aria-label',`Watch channel ${c.channel} ${c.name} live`);
    station.append(text('span',c.channel,'channel-number'),text('span',c.name,'channel-name'));
    station.onclick = () => { selectedChannel = data.channels.indexOf(c); select(c.id); };
    const track = document.createElement('div'); track.className = 'program-track';
    for (const e of c.entries.filter(e => e.end_ms > windowStart && e.start_ms < windowStart + WINDOW)) {
      const start = Math.max(e.start_ms,windowStart), end = Math.min(e.end_ms,windowStart + WINDOW);
      const button = document.createElement('button');
      const focused = data.channels.indexOf(c) === selectedChannel && e.start_ms <= cursor && e.end_ms > cursor;
      const h = e.health || {status:'missing',reasons:[]};
      button.className = `program-cell ${h.status}${focused ? ' focused' : ''}`;
      button.dataset.broadcast = e.id; button.setAttribute('role','gridcell');
      button.setAttribute('aria-selected',String(focused)); button.tabIndex = focused ? 0 : -1;
      button.style.left = `${(start-windowStart)/WINDOW*100}%`; button.style.width = `${(end-start)/WINDOW*100}%`;
      button.setAttribute('aria-label',`${e.title}, ${time(e.start_ms)} to ${time(e.end_ms)}, ${statuses[h.status]}`);
      button.append(text('span',e.title,'cell-title'));if(e.content?.episode_title)button.append(text('span',e.content.episode_title,'cell-note'));button.title=e.source_note||statuses[h.status];if(e.source_note){const flag=text('span','?','source-flag');flag.title='From an imported listing · '+e.source_note;button.append(flag);}
      button.onclick = () => { selectedChannel = data.channels.indexOf(c); cursor = Math.max(data.now_ms,e.start_ms); futureBrowse = e.start_ms > data.now_ms; render(); e.start_ms > data.now_ms ? details() : select(c.id); };
      track.append(button);
    }
    row.append(station,track); $('channels').append(row);
  }
  const {c,e} = selected();
  if (e) {
    $('selected-channel').textContent = `${c.channel} · ${c.name}`;
    $('selected-title').textContent = e.title;
    $('selected-status').textContent = statuses[e.health.status];
    $('selected-time').textContent = `${time(e.start_ms,true)} – ${time(e.end_ms)}`;
    const h=e.health;
    $('selected-description').textContent = (e.block?.known_points?.length?'Complete block · '+e.block.known_points.map(p=>`${p.title||'Known airing'} at ${time(Date.parse(p.aired_at))}`).join(' · '):'') || e.content?.episode_title || e.content?.description || h.reasons?.join(' · ') || 'Description unavailable.';
    $('selected-evidence').textContent = ''; $('selected-evidence').title=e.source_note||'';
  }
  const line = (Date.now() + skew - windowStart) / WINDOW * 100;
  $('now-line').hidden = line < 0 || line > 100;
  $('now-line').style.left = `calc(var(--channel) + (100% - var(--channel)) * ${line/100})`;
}
async function refresh() {
  try {
    const focused = document.activeElement?.dataset.service;
    const focusGrid = document.activeElement?.dataset.broadcast;
    const previous = data?.channels[selectedChannel]?.id;
    data = await api('/api/guide'); skew = data.now_ms - Date.now();
    if (previous) selectedChannel = Math.max(0,data.channels.findIndex(c=>c.id===previous));
    if (!futureBrowse) cursor = data.now_ms;
    render();
    if(data.context)$('context-label').textContent=data.context.mode==='surfing'?'CHANNEL SURFING':'TIME MACHINE';
    if (focused) [...document.querySelectorAll('[data-service]')].find(b=>b.dataset.service===focused)?.focus({preventScroll:true});
    else if (focusGrid) document.querySelector('.program-cell.focused')?.focus({preventScroll:true});
    if(channel&&!data.channels.some(c=>c.id===channel)){channel=null;video.pause();video.removeAttribute('src');video.load();}
    if (!channel && data.channels.length) select(data.context?.service_id||new URLSearchParams(location.search).get('channel')||data.channels[0].id,false);
  } catch(error) { toast(error.message); }
}
async function select(id,closeGuide=true) {
  if(!data.channels.some(c=>c.id===id)){toast('This channel is not in the active lineup.');return;}
  generation++; channel=id; segment=null; futureBrowse=false; cursor=data.now_ms;
  video.pause();video.removeAttribute('src');video.load();
  const c=data.channels.find(c=>c.id===id); $('playing-channel').textContent=`${c.channel} ${c.name}`;
  if(closeGuide)setMode('watch');
  await tune();
}
async function tune() {
  if(!channel || tuning)return;
  tuning=true;const gen=generation;
  try {
    const s=await api(`/api/tune?service=${encodeURIComponent(channel)}`);
    if(gen!==generation)return;
    const changed=segment?.id!==s.id;segment=s;skew=s.now_ms-Date.now();
    if(s.kind==='slate') {
      video.pause();video.removeAttribute('src');video.load();
      slate(s.title,s.reason || 'No eligible media for this broadcast.');
    } else if(changed) {
      slate('Tuning in…',s.title);video.src=scoped(`/media/${s.id}`);
      video.onloadedmetadata=()=>{
        if(gen!==generation)return;
        video.currentTime=(s.offset_ms+Math.max(0,Date.now()+skew-s.now_ms))/1000;
        video.play().then(()=>{if(s.remote)reportStream(s.id,'online');$('slate').hidden=true;$('resume').hidden=true;}).catch(()=>{$('resume').hidden=false;slate('Press OK to watch.',s.title);});
      };
    } else if(video.readyState>=1) {
      const expected=(s.offset_ms+Math.max(0,Date.now()+skew-s.now_ms))/1000;
      if(Math.abs(video.currentTime-expected)>2)video.currentTime=expected;
    }
  } catch(error) { slate('Broadcast unavailable',error.message); }
  finally {tuning=false;if(gen!==generation)setTimeout(tune,0);}
}
function move(direction) {
  if(!data?.channels.length)return;
  if(mode==='watch')setMode('mini');
  if(direction==='up')selectedChannel=(selectedChannel-1+data.channels.length)%data.channels.length;
  if(direction==='down')selectedChannel=(selectedChannel+1)%data.channels.length;
  if(direction==='right') {const e=selected().e;cursor=Math.min(e?.end_ms || cursor+HALF_HOUR,data.until_ms-1);futureBrowse=true;}
  if(direction==='left') {const e=selected().e;cursor=Math.max(data.now_ms,(e?.start_ms || cursor)-1);futureBrowse=cursor>data.now_ms;}
  render();document.querySelector('.program-cell.focused')?.focus({preventScroll:true});
}
function activate() {
  if(!$('resume').hidden){$('resume').click();return;}
  if(selected().e?.start_ms>data.now_ms)details();else if(selected().c)select(selected().c.id);
}
function numberTune() {
  const c=data?.channels.find(c=>c.channel===digits);
  $('number-entry').hidden=true;
  if(c){selectedChannel=data.channels.indexOf(c);select(c.id);}else toast(`Channel ${digits} is not in this lineup.`);
  digits='';
}
video.onerror=()=>slate('Source unavailable','The server couldn’t open this recording. Try another channel for now.');
video.onended=()=>{slate('The next segment is coming up.','The broadcast follows the station clock.');tune();};
$('resume').onclick=()=>{segment=null;tune();};
$('guide-toggle').onclick=cycleGuide;$('info-toggle').onclick=details;
$('live-button').onclick=()=>{if(selected().c)select(selected().c.id);};
$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>toast('Use your browser or TV full-screen control.'));};
$('details-close').onclick=()=>$('details').close();
$('details-watch').onclick=()=>{$('details').close();select(selected().c.id);};
document.addEventListener('keydown',event=>{
  const key=event.key;
  if($('details').open){if(key==='Escape'||key==='Backspace'){event.preventDefault();$('details').close();}return;}
  if(/^\d$/.test(key)){event.preventDefault();digits=(digits+key).slice(-4);$('number-entry').textContent=digits;$('number-entry').hidden=false;clearTimeout(digitTimer);digitTimer=setTimeout(numberTune,1300);return;}
  if(key==='Enter'&&digits){clearTimeout(digitTimer);numberTune();event.preventDefault();return;}
  const arrows={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right'};
  if(arrows[key]){event.preventDefault();move(arrows[key]);return;}
  if(key==='PageUp'||key==='PageDown'){event.preventDefault();cursor=Math.max(data.now_ms,Math.min(data.until_ms-1,cursor+(key==='PageUp'?-86400000:86400000)));futureBrowse=true;render();return;}
  if(key==='ChannelUp'||key==='ChannelDown'){event.preventDefault();const i=data.channels.findIndex(c=>c.id===channel);select(data.channels[(i+(key==='ChannelUp'?1:-1)+data.channels.length)%data.channels.length].id);return;}
  if(key==='Enter' && (document.activeElement===document.body || document.activeElement===$('channels') || document.activeElement?.dataset.broadcast)){event.preventDefault();activate();return;}
  if(key.toLowerCase()==='g'||key==='Guide'){event.preventDefault();cycleGuide();}
  if(key.toLowerCase()==='i'||key==='Info'){event.preventDefault();details();}
  if(key==='Escape'||key==='Backspace'||key==='BrowserBack'){event.preventDefault();setMode(mode==='full'?'mini':'watch');}
  if(key.toLowerCase()==='f')$('fullscreen').click();
  if(key.toLowerCase()==='m')location.href=scoped('/manager');
  if(key.toLowerCase()==='t')location.href='/time-machine';
  if(key==='MediaPlayPause'||key==='MediaPause'||key==='MediaTrackNext'||key==='MediaTrackPrevious'){event.preventDefault();toast('This broadcast keeps its time. Change channels or rejoin live.');}
});
setInterval(()=>{if(segment&&Date.now()+skew>=segment.end_ms){segment=null;tune();}if(data)$('clock').textContent=time(Date.now()+skew,true);},500);
setInterval(tune,10000);setInterval(refresh,30000);refresh();

document.addEventListener('visibilitychange',()=>{if(document.hidden)video.pause();else if(channel){segment=null;tune();}});

function reportStream(id,status){fetch(scoped('/api/playback-health'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({segment_id:id,status})}).catch(()=>{});}
video.addEventListener('error',()=>{if(segment?.remote)reportStream(segment.id,'offline');});
