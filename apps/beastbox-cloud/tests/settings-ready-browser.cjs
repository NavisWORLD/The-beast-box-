/** Real SSR/hydration regression. Hold real Next chunks; never replace them. */
const assert=require('node:assert/strict');
const {chromium,webkit}=require('playwright');
const expect=require('playwright/test').expect.configure({timeout:20000});
const origin=process.argv[2]||'http://127.0.0.1:3000';
(async()=>{
 const engine=process.env.BEAST_TEST_BROWSER==='webkit'?webkit:chromium;
 const browser=await engine.launch({headless:true,...(process.env.BEAST_BROWSER_EXECUTABLE?{executablePath:process.env.BEAST_BROWSER_EXECUTABLE}:{}),...(engine===chromium?{args:['--no-sandbox','--disable-dev-shm-usage']}: {})});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  let release;const gate=new Promise(resolve=>release=resolve);
  await page.route('**/_next/static/**/*.js*',async route=>{await gate;await route.fallback();});
  await page.goto(origin+'/settings',{waitUntil:'commit'});
  const quality=page.getByLabel('3D rendering quality');
  await expect(quality).toBeVisible();await expect(quality).toBeDisabled();
  const scenery=page.getByRole('switch',{name:'Three.js pocket scenery'});await expect(scenery).toBeDisabled();
  release();await expect(quality).toBeEnabled();await quality.selectOption('low');
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-pocket-3d-settings-v1')).quality),'low');
  await page.reload();await expect(quality).toBeEnabled();await expect(quality).toHaveValue('low');
  console.log('PASS: genuine unwired SSR controls disabled; hydrated quality selection survives reload');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
