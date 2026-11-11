const $=id=>document.getElementById(id);
let dashboard, report, lastRequest, allGaps=false, loadGeneration=0, assessGeneration=0;
const contextId=new URLSearchParams(location.search).get('context');
function scoped(path){if(!contextId)return path;const url=new URL(path,location.origin);url.searchParams.set('context',contextId);return url.pathname+url.search+url.hash;}
if(contextId)for(const a of document.querySelectorAll('a[href="/"]'))a.href=scoped('/');
function node(tag,content,cls){const e=document.createElement(tag);if(content!==undefined)e.textContent=content;if(cls)e.className=cls;return e;}
function button(label,action){const b=node('button',label);b.type='button';b.onclick=action;return b;}
async function request(path,value){const r=await fetch(scoped(path),value===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});const data=await r.json();if(!r.ok)throw Error(data.error||r.statusText);return data;}
function message(value,error=false){$('message').textContent=value;$('message').className=error?'error':'';$('message').hidden=false;}
function badge(value){return node('span',value.replaceAll('_',' '),`badge ${value}`);}
function hours(ms){return `${(ms/3600000).toFixed(1)}h`;}
function dateTime(ms){return new Date(ms).toLocaleString('en-US',{timeZone:dashboard?.timezone||'America/New_York',weekday:'short',hour:'numeric',minute:'2-digit'});}
function option(select,value,label){const e=node('option',label);e.value=value;select.append(e);}
async function load(){
  const generation=++loadGeneration;
  $('health-standard-form').dataset.ready='false';for(const input of document.querySelectorAll('[data-standard]'))input.disabled=true;$('health-standard-form').querySelector('button').disabled=true;
  try{
    const params=new URLSearchParams({standard:$('health-view').value,days:$('plan-days').value});if($('plan-date').value)params.set('date',$('plan-date').value);const received=await request('/api/manager?'+params);if(generation!==loadGeneration)return;dashboard=received;const selected=$('plan-service').value;
    const saved=$('health-view').value;$('health-view').replaceChildren();for(const standard of dashboard.health_standards)option($('health-view'),standard.id,standard.name);$('health-view').value=saved;
    for(const input of document.querySelectorAll('[data-standard]')){const value=dashboard.health_standard.settings[input.dataset.standard];if(input.type==='checkbox')input.checked=value;else input.value=value;input.disabled=['min_history_percent','min_exact_percent'].includes(input.dataset.standard)&&dashboard.health_standard.mode!=='historical';}
    $('health-standard-form').dataset.ready='true';$('health-standard-form').dataset.view=dashboard.health_standard.id;$('health-standard-form').querySelector('button').disabled=false;
    $('health-scope').textContent=dashboard.health_standard.mode==='channel'?'LIVE · NEXT 72 HOURS':`ASSESSMENT · ${dashboard.assessment_date} · ${dashboard.assessment_days} DAYS`;
    const lineup=dashboard.lineup_health;$('lineup-summary').textContent=`${lineup.healthy_channels} of ${lineup.channel_count} channels meet this standard · ${lineup.unknown_channels} need more research · target: ${lineup.target_channels} healthy channels`;if(!lineup.channel_count&&dashboard.health_standard.mode==='historical')$('lineup-summary').textContent='No dated lineup is established for this period. Individual service listings can still be assessed below.';
    $('channel-health').replaceChildren();
    for(const c of dashboard.channels){
      const card=node('article',undefined,`channel-card ${c.playable_percent<20?'bad':c.playable_percent<99?'warn':''}`);
      const progress=node('div',undefined,'progress'),bar=node('span');bar.style.width=`${Math.min(100,c.playable_percent)}%`;progress.append(bar);
      card.append(node('h3',c.name),badge(c.assessment_health.status),node('strong',`${c.assessed_playable_percent}%`),node('p',`${hours(c.assessed_program_ms)} program footage · ${hours(c.assessed_continuity_ms)} ads / continuity\n${c.assessed_gap_blocks} blocks need attention · ${c.quality_alerts} segment alerts`),progress,button('Inspect this channel →',()=>{$('plan-service').value=c.id;$('plan-mode').value='channel';modeChanged();$('planner').scrollIntoView({behavior:'smooth'});}));
      $('channel-health').append(card);
    }
    $('plan-service').replaceChildren();for(const c of dashboard.inventory.channels)option($('plan-service'),c.id,c.name);
    if(selected)$('plan-service').value=selected;
    if(!$('plan-date').value){const d=new Intl.DateTimeFormat('en-CA',{timeZone:dashboard.timezone||'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(dashboard.now_ms));$('plan-date').value=d;}
    $('locate-content').replaceChildren();
    for(const c of dashboard.inventory.contents.filter(c=>c.kind!=='series'))option($('locate-content'),c.id,`${c.title}${c.episode_title?' — '+c.episode_title:''} [${c.kind}]`);
    $('override-program').replaceChildren();for(const p of dashboard.inventory.programs)option($('override-program'),p.id,p.title);
    renderLibrary();
  }catch(error){message(error.message,true);}
}
function modeChanged(){$('plan-tags').closest('label').hidden=$('plan-mode').value!=='theme';$('plan-tags').required=false;}
function locate(content){
  if(content)$('locate-content').value=content;
  $('locate-from').value=$('plan-date').value;
  const date=new Date($('plan-date').value+'T12:00:00Z');date.setUTCDate(date.getUTCDate()+Number($('plan-days').value));$('locate-until').value=date.toISOString().slice(0,10);
  $('locate-dialog').showModal();$('locate-folder').focus();
}
function override(airing){$('override-airing').value=airing;$('override-dialog').showModal();$('override-program').focus();}
function renderLibrary(){
  const query=$('library-search').value.toLowerCase();$('asset-rows').replaceChildren();
  const assets=dashboard.inventory.assets.filter(a=>`${a.title} ${a.kind} ${a.source_id}`.toLowerCase().includes(query));
  for(const a of assets){
    const row=node('tr'),name=node('td',a.title);name.append(node('small',a.id));
    const kind=node('td',`${a.kind} · ${(a.duration_ms/60000).toFixed(1)} min`),status=node('td');status.append(badge(a.excluded?'excluded':a.file_available?'ready':'offline'));
    const actions=node('td'),group=node('div',undefined,'table-actions');
    if(!a.file_available)group.append(button('Find original file',()=>{$('repair-source').value=a.source_id;$('repair-path').value='';$('repair-dialog').showModal();$('repair-path').focus();}));
    group.append(button('Locate another copy',()=>locate(a.content_id)));actions.append(group);row.append(name,kind,status,actions);$('asset-rows').append(row);
  }
  if(!assets.length){const row=node('tr'),cell=node('td','No matching recordings. Ingest a prepared library to begin.');cell.colSpan=4;row.append(cell);$('asset-rows').append(row);}
}
function renderReport(){
  $('assessment').hidden=false;
  const known=report.known_schedule_percent;
  let verdict=report.mode==='theme'?`${report.unique_programs} eligible content identities match this concept. `:report.mode==='historical'?'Historical reconstruction assessment. ':'Channel-rule assessment. ';
  if(report.historically_complete)verdict+='The imported exact schedule and required media are covered.';
  else if(report.mode==='historical'&&known<100)verdict+=`${known}% of the requested time has imported schedule evidence; the remaining history is unknown.`;
  else verdict+=`${report.playable_percent}% of this plan is playable footage. Slates and unavailable files are counted as gaps.`;
  $('verdict').textContent=verdict+' Health: '+report.health.status.replaceAll('_',' ')+' under '+report.health.standard_name+'.';
  $('metrics').replaceChildren();
  for(const [value,label] of [[`${report.playable_percent}%`,'Playable footage'],[hours(report.unique_program_ms),'Unique program inventory'],[known===null?'—':`${known}%`,'Known historical schedule'],[`${report.repeat_passes_needed}×`,'Inventory passes needed']]){const card=node('div',undefined,'metric');card.append(node('strong',value),node('span',label));$('metrics').append(card);}
  $('daily').replaceChildren();for(const d of report.daily){const card=node('div',undefined,'day-card');card.append(node('strong',d.date),node('p',`${d.playable_percent}% playable · ${d.gap_blocks} blocks with gaps`));$('daily').append(card);}
  $('recommendations').replaceChildren();
  for(const r of report.recommendations||[]){const card=node('article',undefined,'recommendation');card.append(node('small',r.kind.replaceAll('_',' ').toUpperCase()),node('h3',r.title),node('p',r.detail));const actions=node('div',undefined,'recommendation-actions');for(const action of r.actions){const a=node('a',action.label);a.href=action.url.startsWith('/')?scoped(action.url):action.url;if(!action.url.startsWith('/')){a.target='_blank';a.rel='noopener noreferrer';}actions.append(a);}card.append(actions);$('recommendations').append(card);}
  if(report.search_note)$('recommendations').append(node('p',report.search_note,'fine'));
  $('requirements').replaceChildren();
  for(const r of report.requirements.filter(r=>r.status==='missing')){
    const card=node('div',undefined,'requirement-card'),details=node('div');details.append(node('strong',`Known missing ${r.kind}: ${r.note||r.airing_title}`),node('p',`${(r.duration_ms/60000).toFixed(1)} min required · ${(r.available_ms/60000).toFixed(1)} min eligible inventory · ${r.airing_title}`));
    card.append(details,button('Locate matching media',()=>locate(r.content_id)));$('requirements').append(card);
  }
  $('gap-rows').replaceChildren();
  for(const gap of (allGaps?report.gaps:report.gaps.slice(0,10))){
    const row=node('tr'),when=node('td',`${dateTime(gap.start_ms)}–${dateTime(gap.end_ms)}`),piece=node('td',gap.title);piece.append(node('small',gap.reasons.join(' · ')));
    const status=node('td');status.append(badge(gap.status));
    const actions=node('td'),group=node('div',undefined,'table-actions');
    const airing=report.history.find(a=>a.id===gap.airing_id);
    group.append(button('Locate media',()=>locate(airing?.content_id)));
    if(gap.airing_id)group.append(button('Explicit substitute',()=>override(gap.airing_id)));
    actions.append(group);row.append(when,piece,status,actions);$('gap-rows').append(row);
  }
  $('show-gaps').hidden=report.gaps.length<=10; $('show-gaps').textContent=allGaps?'Show fewer gaps':`Show all ${report.gaps.length} gaps`;
  if(!report.gaps.length){const row=node('tr'),cell=node('td','No playback gaps in this assessment. Check evidence coverage and repeat pressure before calling it historically complete.');cell.colSpan=4;row.append(cell);$('gap-rows').append(row);}
}
async function assess(){
  const generation=++assessGeneration;
  $('assess-button').disabled=true;$('assess-button').textContent='Checking the archive…';
  try{const mode=$('plan-mode').value;const chosen=dashboard.health_standards.find(s=>s.id===$('health-view').value);lastRequest={standard_id:chosen?.mode===mode?chosen.id:mode,mode,service_id:$('plan-service').value,date:$('plan-date').value,days:Number($('plan-days').value),tags:$('plan-mode').value==='theme'?$('plan-tags').value.split(',').map(s=>s.trim()).filter(Boolean):[]};const received=await request('/api/manager/assess',lastRequest);if(generation!==assessGeneration)return;report=received;renderReport();}
  catch(error){message(error.message,true);}finally{$('assess-button').disabled=false;$('assess-button').textContent='Check the archive →';}
}
async function complete(path,value,dialog){try{const result=await request(path,value);$(dialog).close();message(result.status);await load();if(lastRequest)await assess();}catch(error){message(error.message,true);const e=document.querySelector(`#${dialog} .form-error`);if(e)e.remove();const p=node('p',error.message,'form-error');$(dialog).append(p);}}
$('plan-form').onsubmit=async e=>{e.preventDefault();await assess();await load();};$('plan-mode').onchange=modeChanged;$('library-search').oninput=renderLibrary;
$('locate-form').onsubmit=e=>{e.preventDefault();complete('/api/manager/attach',{content_id:$('locate-content').value,folder:$('locate-folder').value,file:$('locate-file').value,valid_from:$('locate-from').value,valid_until:$('locate-until').value},'locate-dialog');};
$('repair-form').onsubmit=e=>{e.preventDefault();complete('/api/manager/repair',{source_id:$('repair-source').value,path:$('repair-path').value},'repair-dialog');};
$('override-form').onsubmit=e=>{e.preventDefault();complete('/api/manager/override',{airing_id:$('override-airing').value,program_id:$('override-program').value,note:$('override-note').value},'override-dialog');};
for(const b of document.querySelectorAll('.close-dialog'))b.onclick=()=>b.closest('dialog').close();
$('import-button').onclick=()=>$('plan-file').click();$('plan-file').onchange=async()=>{const file=$('plan-file').files[0];if(!file)return;try{const data=JSON.parse(await file.text()),result=await request('/api/manager/import-plan',data);message(result.status);await load();if(lastRequest)await assess();}catch(error){message(error.message,true);}finally{$('plan-file').value='';}};
$('health-view').onchange=async()=>{const standard=dashboard.health_standards.find(s=>s.id===$('health-view').value);if(standard){$('plan-mode').value=standard.mode;modeChanged();}await load();if(lastRequest)await assess();};
$('health-standard-form').onsubmit=async e=>{e.preventDefault();try{const standard=dashboard.health_standard,settings={};for(const input of document.querySelectorAll('[data-standard]'))settings[input.dataset.standard]=input.type==='checkbox'?input.checked:Number(input.value);const r=await request('/api/manager/health-standard',{id:standard.id,name:standard.name,mode:standard.mode,settings});message(r.status);await load();if(lastRequest)await assess();}catch(error){message(error.message,true);}};
$('show-gaps').onclick=()=>{allGaps=!allGaps;renderReport();};
modeChanged();load();
