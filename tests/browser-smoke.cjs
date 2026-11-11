// This maintenance/legacy check requires an explicit loopback serve --admin instance.
// Run against a synthetic demo: RETRO_TV_URL=http://127.0.0.1:8787 node tests/browser-smoke.cjs
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const root=process.env.RETRO_TV_URL||'http://127.0.0.1:8787';
    await page.goto(root);await page.waitForSelector('.program-cell');
    await page.locator('[data-service="kids"]').click();
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2 && !document.querySelector('video').paused);
    await page.keyboard.press('g');
    assert.equal(await page.locator('body').getAttribute('class'),'mode-full');
    const pip=await page.locator('#watch').boundingBox();assert.ok(pip.width<700&&pip.height<400);
    const playingBefore=await page.locator('#playing-channel').innerText();
    await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowDown');
    assert.equal(await page.locator('#playing-channel').innerText(),playingBefore,'browsing must not retune');
    await page.keyboard.press('Enter');assert.equal(await page.locator('#details').evaluate(e=>e.open),true);
    await page.keyboard.press('Escape');await page.keyboard.press('g');
    assert.equal(await page.locator('body').getAttribute('class'),'mode-mini');
    const overlay=await page.locator('#guide-shell').boundingBox();assert.ok(overlay.y>500&&overlay.height<360);
    assert.equal(await page.locator('video').evaluate(v=>v.paused),false,'switching guide modes must not pause');
    await page.keyboard.press('g');assert.equal(await page.locator('body').getAttribute('class'),'mode-watch');
    await page.keyboard.press('2');await page.keyboard.press('Enter');
    await page.waitForFunction(()=>document.getElementById('playing-channel').textContent.startsWith('2 '));
    await page.goto(root+'/server-manager');await page.waitForSelector('.channel-card');
    await page.selectOption('#plan-mode','historical');await page.selectOption('#plan-days','3');
    await page.locator('#assess-button').click();await page.waitForSelector('#assessment:not([hidden])');
    assert.equal(await page.locator('.day-card').count(),3);
    assert.match(await page.locator('#verdict').innerText(),/unknown/);
    await page.locator('#gap-rows button').first().click();assert.equal(await page.locator('#locate-dialog').evaluate(e=>e.open),true);
    await page.locator('#locate-dialog .close-dialog').click();
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'manager should fit mobile viewport');
    await page.goto(root);await page.waitForSelector('.program-cell');
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'guide should fit mobile viewport');
    assert.deepEqual(errors,[]);
    console.log('PIP, bottom-third, continuous playback, D-pad, future info, numeric tuning, 3-day manager and responsive layouts passed');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
