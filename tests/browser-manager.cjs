// This maintenance/legacy check requires an explicit loopback serve --admin instance.
// Run against the generated six-channel demo; restores any edited health settings.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const base=process.env.RETRO_TV_URL||'http://127.0.0.1:8787';let original;
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const data=await (await page.request.get(base+'/api/manager')).json();original=data.health_standards.find(s=>s.id==='theme');
    await page.goto(base+'/server-manager');await page.waitForSelector('.channel-card');
    await page.selectOption('#health-view','historical');
    await page.waitForFunction(()=>document.getElementById('health-standard-form').dataset.view==='historical'&&document.getElementById('health-standard-form').dataset.ready==='true');
    assert.match(await page.locator('#lineup-summary').innerText(),/need more research/);
    await page.selectOption('#plan-service','kids');await page.fill('#plan-date','1995-07-18');await page.click('#assess-button');
    await page.waitForSelector('#assessment:not([hidden])');
    assert.ok(await page.locator('#recommendations a[href*="archive.org"]').count());
    await page.selectOption('#health-view','theme');
    await page.waitForFunction(()=>document.getElementById('health-standard-form').dataset.view==='theme'&&document.getElementById('health-standard-form').dataset.ready==='true');
    await page.locator('.health-settings summary').click();
    await page.fill('[data-standard=min_unique_hours]','0');await page.fill('[data-standard=max_inventory_passes]','1000');await page.fill('[data-standard=ad_minutes_per_day]','0');
    await page.locator('#health-standard-form button').click();
    await page.waitForFunction(()=>document.getElementById('message').textContent.startsWith('Health standard saved'));
    await page.waitForFunction(()=>document.getElementById('lineup-summary').textContent.startsWith('1 of'));
    assert.deepEqual(errors,[]);
    console.log('Manager mode health, research uncertainty, search links and persisted user criteria passed');
  }finally{
    if(original){const context=await browser.newContext();await context.request.post(base+'/api/manager/health-standard',{data:original});await context.close();}
    await browser.close();
  }
})().catch(e=>{console.error(e);process.exitCode=1;});
