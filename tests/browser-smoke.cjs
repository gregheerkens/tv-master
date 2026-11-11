// Optional: run against `python -m retro_tv serve` after creating the demo.
// Requires Playwright and Chromium installed outside the application runtime.
const {chromium}=require('playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.RETRO_TV_URL||'http://127.0.0.1:8787');
    await page.waitForSelector('[data-service]');
    await page.locator('[data-service="kids"]').click();
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
    await page.waitForTimeout(500);
    const result=await page.evaluate(()=>({channels:document.querySelectorAll('[data-service]').length,playing:!document.querySelector('video').paused,slateHidden:document.getElementById('slate').hidden}));
    if(errors.length||result.channels!==2||!result.playing||!result.slateHidden)throw Error(JSON.stringify({errors,result}));
    await page.keyboard.press('ArrowDown');
    const focused=await page.locator(':focus').getAttribute('data-service');
    if(focused!=='late')throw Error('remote focus did not move to next channel');
    console.log('Browser playback and remote focus passed');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
