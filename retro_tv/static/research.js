const $=id=>document.getElementById(id);
let catalog,batchState=[],reviewPage,reviewBatch,collecting=false,stopCollection=false;
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function button(text,fn){const e=el('button',text,'secondary');e.type='button';e.onclick=fn;return e;}
function option(select,value,label){const e=el('option',label);e.value=value;select.append(e);}
function message(text,error=false){$('research-message').hidden=false;$('research-message').textContent=text;$('research-message').className=error?'error':'';}
async function request(path,value){const r=await fetch(path,value===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});const result=await r.json();if(!r.ok)throw Error(result.error||r.statusText);return result;}
function safeLink(url){try{const u=new URL(url);return u.protocol==='https:'?u.href:'#';}catch{return '#';}}
async function load(){catalog=await request('/api/research');batchState=catalog.batches;const service=$('research-service').value;$('research-service').replaceChildren();for(const s of catalog.services)option($('research-service'),s.id,s.name);if(service)$('research-service').value=service;render();}
function render(){
  $('research-batches').replaceChildren();if(!batchState.length)$('research-batches').append(el('p','No research periods yet. Create one or sideload collected JSON.','fine'));
  for(const batch of batchState){
    const section=el('article',undefined,'research-batch');section.dataset.batch=batch.id;
    const name=catalog.services.find(s=>s.id===batch.service_id)?.name||batch.service_id;
    section.append(el('h3',`${name} · ${batch.start_date} → ${batch.until_date} (exclusive)`),el('p',`${batch.timezone} · ${batch.adapter.replaceAll('_',' ')} · ${batch.pages.filter(p=>p.status==='accepted').length}/${batch.pages.length} source dates accepted`,'fine'));
    const actions=el('div',undefined,'research-actions'),collect=button('Collect pending dates',()=>collectPeriod(batch));collect.disabled=collecting||batch.adapter==='sideload';actions.append(collect,button('Stop after current date',()=>{stopCollection=true;message('Stopping after the current fetch. Collected dates are saved.');}),button('Export JSON',()=>exportBatch(batch)));section.append(actions);
    const days=el('div',undefined,'research-days');
    for(const page of batch.pages){
      const card=el('article',undefined,`research-day ${page.status}`);card.dataset.page=page.id;
      const acceptedHours=page.accepted_listings.reduce((sum,r)=>sum+r.end_ms-r.start_ms,0)/3600000;card.append(el('strong',page.day),el('p',`${page.status.toUpperCase()} · ${page.candidates.length} bounded source slots`),el('p',`${acceptedHours.toFixed(1)} accepted research hours · other hours remain unknown`,'fine'));
      if(page.error)card.append(el('p',page.error,'error'));
      if(page.fetched_at)card.append(el('p',`Collected ${page.fetched_at}`,'fine'));
      if(page.status==='staged'||page.status==='accepted')card.append(button(page.status==='accepted'?'Inspect accepted evidence':'Review listings',()=>review(batch,page)));
      else if(batch.adapter!=='sideload'){
        const fetch=button(page.status==='failed'?'Retry fetch':'Fetch source',()=>fetchPage(page));fetch.disabled=collecting;card.append(fetch);
        const upload=el('input');upload.type='file';upload.accept='.html,.htm,text/html';upload.hidden=true;
        upload.onchange=async()=>{try{const file=upload.files[0];if(!file)return;await fetchPage(page,await file.text());}catch(e){message(e.message,true);}};
        const saved=button('Use saved HTML',()=>upload.click());saved.disabled=collecting;card.append(saved,upload);
      }
      days.append(card);
    }
    section.append(days);$('research-batches').append(section);
  }
}
async function fetchPage(page,html){try{message(`Collecting ${page.day}…`);const result=await request('/api/research/fetch',{page_id:page.id,...(html===undefined?{}:{html})});const updated=result.pages.find(p=>p.id===page.id);message(updated.status==='failed'?`${page.day}: ${updated.error}`:`${page.day}: ${updated.candidates.length} slots staged for review`,updated.status==='failed');await load();return updated;}catch(e){message(e.message,true);return {status:'failed'};}}
async function collectPeriod(batch){if(collecting)return;collecting=true;stopCollection=false;render();try{for(const page of batch.pages){if(stopCollection)break;if(page.status!=='pending')continue;const result=await fetchPage(page);if(result.status==='failed'){message('Collection stopped at a failed date. Check source access, then retry or sideload; no coverage was claimed.',true);break;}await new Promise(r=>setTimeout(r,1000));}}finally{collecting=false;render();}}
async function exportBatch(batch){try{const result=await request('/api/research/export?batch='+encodeURIComponent(batch.id)),url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download=`tv-master-research-${batch.start_date}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){message(e.message,true);}}
function displayTime(value,zone){return new Date(value).toLocaleString('en-US',{timeZone:zone,month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});}
function review(batch,page){
  reviewPage=page;reviewBatch=batch;$('research-review').hidden=false;$('review-heading').textContent=`${page.day} · ${page.status==='accepted'?'Accepted evidence':'Review source claims'}`;$('review-source').href=safeLink(page.url);
  $('review-provenance').textContent=`${page.url} · collected ${page.fetched_at} · SHA-256 ${page.sha256}`;
  $('review-warnings').replaceChildren(...page.warnings.map(w=>el('p',w)));$('review-rows').replaceChildren();
  for(const [index,row] of page.candidates.entries()){
    const tr=el('tr');tr.dataset.index=index;const use=el('input');use.type='checkbox';use.checked=page.status!=='accepted'||page.accepted_listings.some(a=>a.candidate_index===index);use.className='use-row';use.setAttribute('aria-label',`Use ${row.title}`);
    const td=el('td');td.append(use);tr.append(td);const title=el('td');title.append(el('strong',row.title),el('small',`${displayTime(row.start,batch.timezone)} → ${displayTime(row.end,batch.timezone)}`));tr.append(title,el('td',row.episode_title||'Episode not identified'));
    const identity=el('select');identity.className='content-id';identity.setAttribute('aria-label',`Identity for ${row.title}`);option(identity,'','Unmatched program listing');
    for(const c of catalog.contents)option(identity,c.id,`${c.title}${c.episode_title?' — '+c.episode_title:''} [${c.kind}]`);
    const norm=s=>s.normalize('NFKC').toLowerCase().replace(/[’‘]/g,"'").replace(/\s+/g,' ').trim();
    const matches=catalog.contents.filter(c=>norm(c.title)===norm(row.title)&&(!row.episode_title?c.kind==='program'||c.kind==='series':c.kind==='episode'&&norm(c.episode_title||'')===norm(row.episode_title)));
    if(matches.length===1)identity.value=matches[0].id;
    const evidence=el('select');evidence.className='evidence';evidence.setAttribute('aria-label',`Evidence for ${row.title}`);for(const [v,t] of [['schedule_exact','Program slot established'],['exact','Specific episode established'],['inferred','Inferred'],['seasonal','Seasonal expectation']])option(evidence,v,t);const accepted=page.accepted_listings.find(a=>a.candidate_index===index);if(accepted?.content_id)identity.value=accepted.content_id;evidence.value=accepted?.evidence_state||'schedule_exact';
    const confirm=el('label'),checkbox=el('input');checkbox.type='checkbox';checkbox.className='confirm-episode';checkbox.checked=accepted?.evidence_state==='exact';confirm.className='episode-confirm';confirm.append(checkbox,document.createTextNode(' I verified this exact episode/movie'));
    const cell=el('td');cell.append(identity,evidence,confirm);tr.append(cell);for(const input of tr.querySelectorAll('input,select'))input.disabled=page.status==='accepted';$('review-rows').append(tr);
  }
  $('accept-page').disabled=page.status==='accepted';$('accept-page').textContent=page.status==='accepted'?'Accepted · published guide preserved':'Accept checked listings';$('research-review').scrollIntoView({behavior:'smooth'});
}
$('research-form').onsubmit=async e=>{e.preventDefault();try{await request('/api/research/create',{service_id:$('research-service').value,start_date:$('research-start').value,until_date:$('research-until').value,timezone:$('research-zone').value,adapter:$('research-adapter').value,url_template:$('research-url').value});await load();message('Research period created. Pending dates are unknown until sourced listings are reviewed and accepted.');}catch(e){message(e.message,true);}};
$('review-form').onsubmit=async e=>{e.preventDefault();$('accept-page').disabled=true;try{const selections=[...$('review-rows').querySelectorAll('tr')].filter(tr=>tr.querySelector('.use-row').checked).map(tr=>({index:Number(tr.dataset.index),content_id:tr.querySelector('.content-id').value,evidence_state:tr.querySelector('.evidence').value,episode_confirmed:tr.querySelector('.confirm-episode').checked}));const result=await request('/api/research/accept',{page_id:reviewPage.id,selections});message(result.status);await load();review(result.batch,result.batch.pages.find(p=>p.id===reviewPage.id));}catch(e){message(e.message,true);$('accept-page').disabled=false;}};
$('sideload-button').onclick=()=>$('sideload-file').click();$('sideload-file').onchange=async()=>{try{const file=$('sideload-file').files[0];if(!file)return;const result=await request('/api/research/sideload',JSON.parse(await file.text()));await load();message('Research JSON sideloaded. Review source claims before accepting.');const page=result.pages.find(p=>p.status==='staged');if(page)review(result,page);}catch(e){message(e.message,true);}finally{$('sideload-file').value='';}};
$('refresh').onclick=()=>load().catch(e=>message(e.message,true));load().catch(e=>message(e.message,true));
