// This maintenance/legacy check requires an explicit loopback serve --admin instance.
// Run against a synthetic demo. Adds one explicitly synthetic historical test listing.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
try{const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));const base=process.env.RETRO_TV_URL||'http://127.0.0.1:8787';
await page.goto(base+'/research');await page.waitForFunction(()=>document.getElementById('research-service').options.length>0);
const created=await (await page.request.post(base+'/api/research/create',{data:{service_id:'kids',start_date:'1988-01-02',until_date:'1988-01-03',timezone:'America/New_York',adapter:'mediawiki_daily',url_template:'https://example.org/synthetic-browser-fixture'}})).json();assert.ok(created.id);const id=created.pages[0].id;
const html='<h1>January 2, 1988</h1><table><tr><th>Time</th><th>Show</th><th>Episode</th></tr><tr><td>1:00pm</td><td>SYNTHETIC browser research fixture</td><td>Source annotation</td></tr><tr><td>1:30pm</td><td>Second synthetic fixture</td><td></td></tr><tr><td>2:00pm</td><td>Boundary</td><td></td></tr></table>';
const staged=await (await page.request.post(base+'/api/research/fetch',{data:{page_id:id,html}})).json();assert.equal(staged.pages[0].status,'staged');
await page.click('#refresh');const card=page.locator(`[data-page="${id}"]`);await card.getByRole('button',{name:'Review listings'}).click();await page.waitForSelector('#research-review:not([hidden])');assert.equal(await page.locator('#review-rows tr').count(),2);
await page.locator('#review-rows tr').nth(1).locator('.use-row').uncheck();await page.click('#accept-page');await page.waitForFunction(()=>document.getElementById('research-message').textContent.startsWith('Accepted 1'));
assert.equal(await page.locator('#review-rows .use-row:checked').count(),1);assert.equal(await page.locator('#accept-page').isDisabled(),true);
const report=await (await page.request.post(base+'/api/manager/assess',{data:{service_id:'kids',date:'1988-01-02',mode:'historical'}})).json();assert.ok(report.known_schedule_percent>0);assert.equal(report.exact_schedule_percent,0);
const downloadPromise=page.waitForEvent('download');await page.locator(`[data-batch="${created.id}"]`).getByRole('button',{name:'Export JSON'}).click();const download=await downloadPromise;assert.match(download.suggestedFilename(),/1988-01-02/);
await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));assert.deepEqual(errors,[]);console.log('Research staging, source review, partial acceptance, episode uncertainty, JSON export and mobile layout passed');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
