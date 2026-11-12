const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});try{
const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));const base=process.env.RETRO_TV_URL||'http://127.0.0.1:8787';
await p.goto(base+'/block-party');await p.waitForSelector('[data-facet]');
const options=await(await p.request.get(base+'/api/time-machine/options')).json();
for(const key of ['tags','years','months','networks'])assert.equal(await p.locator(`[data-facet=${key}]`).count(),options.block_facets[key].length);
assert.deepEqual(await p.locator('#bp-duration option').evaluateAll(es=>es.map(e=>Number(e.value))),[15,30,60,90]);
const chips=p.locator('[data-facet=tags]');await chips.nth(0).click();if(await chips.count()>1)await chips.nth(1).click();assert.equal(await p.locator('[data-facet=tags][aria-pressed=true]').count(),Math.min(2,await chips.count()));
await p.locator('#bp-clear').click();assert.equal(await p.locator('[aria-pressed=true]').count(),0);
await p.locator('[data-facet=tags][data-value=cartoon]').focus();await p.keyboard.press('Enter');assert.equal(await p.locator('[data-facet=tags][data-value=cartoon]').getAttribute('aria-pressed'),'true');await p.keyboard.press('ArrowRight');assert.notEqual(await p.evaluate(()=>document.activeElement.dataset.value),'cartoon');
await p.fill('#bp-search','July');assert.equal(await p.locator('[data-facet]:visible').count(),1);await p.fill('#bp-search','');
await p.selectOption('#bp-duration','60');await p.uncheck('#bp-commercials');await p.uncheck('#bp-bumpers');await p.fill('#tm-name','Browser custom block');await p.click('#tm-save');await p.waitForFunction(()=>document.getElementById('tm-message').textContent.startsWith('Saved'));
assert.equal(await p.inputValue('#bp-duration'),'60');assert.equal(await p.isChecked('#bp-commercials'),false);assert.equal(await p.locator('[data-facet=tags][data-value=cartoon]').getAttribute('aria-pressed'),'true');
const saved=await(await p.request.get(base+'/api/time-machine/options')).json(),recipe=saved.recipes.find(r=>r.name==='Browser custom block');assert.equal(recipe.rules.block_minutes,60);assert.equal(recipe.rules.include_commercials,false);assert.equal(recipe.rules.include_bumpers,false);
await p.selectOption('#tm-service','kids');await p.fill('#tm-date','1995-07-18');await p.fill('#tm-time','16:47');await p.click('#tm-check');await p.waitForSelector('#tm-preflight:not([hidden])');assert.equal(await p.isDisabled('#tm-launch'),false);await p.check('#bp-bumpers');assert.equal(await p.isDisabled('#tm-launch'),true);
await p.locator('#bp-builder').screenshot({path:process.env.TV_MASTER_BLOCK_SCREENSHOT||'/tmp/tv-master-block-builder.png'});
await p.setViewportSize({width:390,height:844});assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.goto(base+'/time-machine');await p.waitForFunction(()=>document.getElementById('tm-service').options.length>0);assert.equal(await p.isVisible('#bp-builder'),false);assert.equal(await p.isVisible('#tm-tags'),true);assert.deepEqual(errors,[]);console.log('Block Party facets, inclusive multi-select, remote keys, optional tags, fixed durations, continuity toggles, save/restore, preflight invalidation and mobile layout passed');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
