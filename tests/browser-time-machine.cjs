const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const base=process.env.RETRO_TV_URL||'http://127.0.0.1:8787';
    await page.goto(base+'/block-party');
    await page.waitForFunction(()=>document.getElementById('tm-service').options.length>0);
    await page.selectOption('#tm-service','kids');await page.selectOption('#tm-template','specific');
    await page.click('[data-facet=tags][data-value=cartoon]');await page.fill('#tm-name','Saturday cartoon selection');
    await page.click('#tm-save');await page.waitForFunction(()=>document.getElementById('tm-message').textContent.startsWith('Saved'));
    await page.click('#tm-check');await page.waitForSelector('#tm-preflight:not([hidden])');
    assert.match(await page.locator('#tm-verdict').innerText(),/Test Pattern/);
    await page.click('#tm-launch');await page.waitForURL(/context=/);
    const url=page.url();assert.ok(new URL(url).searchParams.get('context'));
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2&&!document.querySelector('video').paused);
    assert.equal(await page.locator('#context-label').innerText(),'TIME MACHINE');
    assert.match(await page.locator('video').getAttribute('src'),/context=/,'media must use the selected timeline');
    await page.keyboard.press('ArrowRight');await page.keyboard.press('Enter');
    assert.equal(await page.locator('#details').evaluate(e=>e.open),true);
    await page.keyboard.press('Escape');
    const context=new URL(url).searchParams.get('context');
    const first=await page.evaluate(async ctx=>(await fetch('/api/tune?service=kids&context='+ctx)).json(),context);
    await page.waitForTimeout(1100);await page.reload();
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
    const second=await page.evaluate(async ctx=>(await fetch('/api/tune?service=kids&context='+ctx)).json(),context);
    assert.ok(second.now_ms>first.now_ms,'returning must advance rather than restart');
    const checks=await page.evaluate(async ctx=>{
      const guide=await (await fetch('/api/guide?context='+ctx)).json();
      const event=guide.channels[0].entries.find(e=>e.start_ms>guide.now_ms);
      // A future segment ID must never be a seek endpoint. Tune still follows the current clock.
      const current=await (await fetch('/api/tune?service=kids&context='+ctx+'&time=0&offset_ms=0')).json();
      const rejected=await fetch('/api/time-machine/launch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:'surfing',service_id:'kids',destination:'1995-07-18T08:00'})});
      return {span:guide.until_ms-guide.now_ms,current:current.now_ms,clock:guide.now_ms,rejected:rejected.status};
    },context);
    assert.equal(checks.span,72*3600000);assert.ok(checks.current>=checks.clock);assert.equal(checks.rejected,400);
    await page.goto(base+'/manager?context='+context);await page.waitForSelector('#live-stats strong');
    assert.match(await page.locator('header nav a').getAttribute('href'),/context=/);
    await page.goto(base+'/block-party');await page.waitForSelector('#tm-contexts a');
    assert.ok((await page.locator('#tm-contexts a').count())>=1);
    await page.goto(base+'/manager');await page.getByRole('heading',{name:'CHANNEL SURF',exact:true}).click();await page.waitForSelector('.program-cell');
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
    assert.deepEqual(errors,[]);
    console.log('Time Machine selection/save/preflight/playback, scoped manager/media, resume, fixed clock and 72-hour bounds passed');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
