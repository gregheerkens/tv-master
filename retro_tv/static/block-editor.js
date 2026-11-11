const $=id=>document.getElementById(id);
let airings=[],zone='America/New_York';
function msg(text){$('message').hidden=false;$('message').textContent=text;}
function paintAirings(){
  const select=$('block-airing');select.replaceChildren(new Option('Enter the airing below…',''));
  for(const a of airings.filter(a=>a.service_id===$('block-service').value))select.append(new Option(a.title+' · '+new Date(a.start_ms).toISOString(),a.id));
}
fetch('/api/blocks/options').then(r=>r.json()).then(d=>{
  airings=d.airings;zone=d.timezone;
  for(const c of d.services)$('block-service').append(new Option(c.name,c.id));
  paintAirings();
}).catch(e=>msg(e.message));
$('block-service').onchange=paintAirings;
$('block-airing').onchange=()=>{
  const a=airings.find(a=>a.id===$('block-airing').value);
  if(a){$('block-show').value=a.title;$('block-aired').value=new Date(a.start_ms).toISOString();preview();}
};
$('block-kind').onchange=()=>{
  $('block-duration').required=$('block-kind').value==='remote';
  $('block-source').placeholder=$('block-kind').value==='remote'?'https://archive.org/download/item/recording.mp4':'/media/recordings/fox-kids.mp4';
};
$('block-form').onsubmit=async e=>{
  e.preventDefault();$('block-save').disabled=true;
  try{
    const seasonal=$('block-seasonal').checked;
    const data={complete_block:$('block-complete').checked,tags:$('block-tags').value.split(',').map(t=>t.trim()).filter(Boolean),
      title:$('block-title').value,service_id:$('block-service').value,
      source_in_ms:Math.round(Number($('block-in').value)*60000),source_out_ms:Math.round(Number($('block-out').value)*60000),
      anchor:{airing_id:$('block-airing').value||undefined,title:$('block-show').value,aired_at:$('block-aired').value,source_offset_ms:Math.round(Number($('block-anchor').value)*60000)},
      seasonal,holiday:seasonal?$('block-holiday').value:null,holiday_year:seasonal?Number($('block-holiday-year').value):null};
    if($('block-kind').value==='remote'){
      data.url=$('block-source').value;data.duration_ms=Math.round(Number($('block-duration').value)*60000);data.allow_remote=$('block-remote').checked;
    }else data.path=$('block-source').value;
    const r=await fetch('/api/blocks/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),d=await r.json();
    if(!r.ok)throw Error(d.error);
    msg(`${d.status} ${new Date(d.start_ms).toISOString()} → ${new Date(d.end_ms).toISOString()}`);
  }catch(e){msg(e.message);}finally{$('block-save').disabled=false;}
};

function preview(){
  const anchor=Date.parse($('block-aired').value),inside=Number($('block-anchor').value)*60000,a=Number($('block-in').value)*60000,b=Number($('block-out').value)*60000;
  if(!Number.isFinite(anchor)||inside<a||inside>=b||b<=a){$('block-preview').textContent='Enter a known airing inside a valid recording bracket.';return;}
  const start=anchor-(inside-a),end=start+b-a,format=t=>new Date(t).toLocaleString('en-US',{timeZone:zone});
  $('block-preview').textContent=`Broadcast bracket: ${format(start)} → ${format(end)} (${zone}) · ${(b-a)/60000} minutes, kept intact.`;
}
$('block-form').addEventListener('input',preview);
