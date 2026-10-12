/* Run against the coordinated production preview. Guest/loopback failures are
 * injected; this acceptance test does not claim live model installation. */
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('playwright');
const expect=require('playwright/test').expect.configure({timeout:20000});

const origin=process.env.BEAST_BROWSER_ORIGIN||process.argv[2]||'http://127.0.0.1:3000';
const key='beastbox-companion-session-v1';
const rooms=['/','/spark/index.html','/beast-cage','/sol-game','/brain-bay','/research','/settings'];
async function readSession(page){return page.evaluate(k=>JSON.parse(localStorage.getItem(k)||'null'),key);}
function invariant(session){
 return {id:session.beast.qbeast.profile.id,qbeast:session.beast.qbeast,genome:session.beast.genome,xp:session.beast.xp,bond:session.beast.bond,stage:session.beast.stage,mind:session.mind};
}
async function checkRooms(page){
 const nav=page.getByRole('navigation',{name:'Universe rooms'});
 const hrefs=await nav.getByRole('link').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('href')));
 assert.deepEqual(hrefs,rooms);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Page must fit the viewport');
}

(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BEAST_BROWSER_EXECUTABLE?{executablePath:process.env.BEAST_BROWSER_EXECUTABLE}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'no-preference'});
 let sensorCalls=0;
 await context.exposeFunction('__noteSensorRequest',()=>{sensorCalls++;});
 await context.addInitScript(()=>{
  if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{await window.__noteSensorRequest();throw Error('Unexpected sensor permission request');};
 });
 const page=await context.newPage(),errors=[],privateCalls=[],guestCalls=[],loopbackCalls=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{
  const url=new URL(request.url());
  if(url.origin===new URL(origin).origin&&url.pathname.startsWith('/api/')&&!['/api/guest','/api/talk'].includes(url.pathname))privateCalls.push(url.pathname);
 });
 await page.route('**/api/guest',async route=>{
  guestCalls.push(JSON.parse(route.request().postData()||'null'));
  await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Guest model host is not configured'})});
 });
 await page.route('http://127.0.0.1:11434/**',async route=>{
  loopbackCalls.push(JSON.parse(route.request().postData()||'null'));
  await route.abort('connectionrefused');
 });
 try{
  await page.goto(origin+'/brain-bay');
  await expect(page.getByRole('heading',{name:/Swap the brain/})).toBeVisible();
  // No saved Beast: the shared talk panel speaks as Zeref, and nothing is sent until the visitor presses Send.
  await expect(page.getByText('Zeref is answering until you meet your own Beast')).toBeVisible();
  await expect(page.getByRole('heading',{name:'Talk to Zeref'})).toBeVisible();
  await expect(page.getByText(/Brain: RAWRPHØS guest/)).toBeVisible();
  assert.equal(guestCalls.length,0);assert.equal(loopbackCalls.length,0);
  await checkRooms(page);

  // Use the actual public generator/identity modules and shared storage path.
  const selectedId=await page.evaluate(async()=>{
   const [{loadSparkRuns},{buildGenome},{selectSpark,withSparkLock}]=await Promise.all([import('/spark/runs.mjs'),import('/spark/genome.mjs'),import('/spark/identity.mjs')]);
   const runs=await loadSparkRuns({includeQvm:true});
   const gen=buildGenome({focus:50,calm:70,spark:30},runs[0]);
   const selected=await withSparkLock(()=>selectSpark(localStorage,gen));
   window.dispatchEvent(new Event('beastbox:spark-selected'));
   return selected.beast.qbeast.profile.id;
  });
  await page.reload();
  await expect(page.getByRole('img',{name:/your selected Beast/})).toBeVisible();
  const before=await readSession(page);
  assert.equal(before.beast.qbeast.profile.id,selectedId);
  const beastName=(await page.locator('[data-talk-state] h2').textContent()).replace(/^Talk to /,'');
  assert.ok(beastName&&beastName!=='Zeref'&&!/Finding/.test(beastName),'Talk panel must speak as the saved Beast: '+beastName);

  // Guest host failure: honest offline state, no reply text, no growth from a failed request.
  await page.getByLabel(/^Message to /).fill('quiet star');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.locator('[data-talk-state="offline"]')).toBeVisible();
  await expect(page.getByText('Model offline: no reply was received')).toBeVisible();
  assert.equal(guestCalls.length,1);
  assert.deepEqual(Object.keys(guestCalls[0]).sort(),['provider','text']);
  assert.equal(guestCalls[0].provider,'rawrphos-local');
  assert.ok(guestCalls[0].text.includes('You are '+beastName),'identity frame');
  assert.ok(guestCalls[0].text.endsWith('Keeper: quiet star\n'+beastName+':'),'keeper words kept verbatim');
  assert.deepEqual(invariant(await readSession(page)),invariant(before),'failed requests never change the Beast');

  // Local Ollama: explicit choice, persona as system text, honest connection help.
  await page.getByRole('button',{name:'Change brain'}).click();
  await page.locator('label').filter({hasText:'My local Ollama'}).click();
  await page.getByLabel('Model tag').fill('tiny:latest');
  assert.equal(loopbackCalls.length,0,'Selecting a brain must not send a message');
  await page.reload();
  await expect(page.getByText(/Brain: My local Ollama/)).toBeVisible();
  await page.getByLabel(/^Message to /).fill('quiet star');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.locator('[data-talk-state="offline"]')).toBeVisible();
  await expect(page.getByText(/OLLAMA_ORIGINS=/).first()).toBeVisible();
  assert.equal(loopbackCalls.length,1);
  assert.equal(loopbackCalls[0].model,'tiny:latest');
  assert.equal(loopbackCalls[0].messages[0].role,'system');
  assert.ok(loopbackCalls[0].messages[0].content.includes('You are '+beastName));
  assert.deepEqual(loopbackCalls[0].messages.at(-1),{role:'user',content:'quiet star'});
  assert.deepEqual((await readSession(page)).beast.qbeast,before.beast.qbeast);

  await page.getByRole('navigation',{name:'Universe rooms'}).getByRole('link',{name:'SETTINGS',exact:true}).click();
  await expect(page.getByRole('heading',{name:/A little quieter/})).toBeVisible();
  const mute=page.getByRole('switch',{name:'Mute website sound'});
  await expect(mute).toHaveAttribute('aria-checked','false');
  await mute.click();
  await expect(mute).toHaveAttribute('aria-checked','true');
  await expect(page.locator('[data-site-sound]')).toHaveAttribute('data-site-sound','off');
  const music=page.getByRole('switch',{name:'Background music'});
  await expect(music).toHaveAttribute('aria-checked','true');
  await music.click();
  const volume=page.getByLabel('Website volume');
  await volume.evaluate(input=>{
   Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'23');
   input.dispatchEvent(new Event('input',{bubbles:true}));
   input.dispatchEvent(new Event('change',{bubbles:true}));
  });
  const prefs=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-music-v1')));
  assert.equal(prefs.musicOn,false);assert.equal(prefs.volume,.23);
  assert.equal(await page.evaluate(()=>localStorage.getItem('beastbox-site-sound-v1')),'off');
  const reduce=page.getByRole('switch',{name:'Reduce motion'});
  await reduce.click();
  await expect(reduce).toHaveAttribute('aria-checked','true');
  assert.equal(await page.evaluate(()=>localStorage.getItem('beastbox-reduced-motion-v1')),'true');
  await expect(page.locator('main')).toHaveAttribute('data-reduced-motion','true');
  await page.reload();
  await expect(page.getByRole('switch',{name:'Reduce motion'})).toHaveAttribute('aria-checked','true');
  await expect(page.getByRole('switch',{name:'Background music'})).toHaveAttribute('aria-checked','false');
  await expect(page.getByRole('switch',{name:'Mute website sound'})).toHaveAttribute('aria-checked','true');
  await expect(page.getByLabel('Website volume')).toHaveValue('23');
  assert.equal((await readSession(page)).beast.qbeast.profile.id,selectedId);
  await page.getByRole('switch',{name:'Reduce motion'}).click();
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.getByRole('switch',{name:'Reduce motion'})).toBeDisabled();
  await expect(page.getByRole('switch',{name:'Reduce motion'})).toHaveAttribute('aria-checked','true');
  await page.emulateMedia({reducedMotion:'no-preference'});

  for(const pathname of ['/settings','/brain-bay']){
   await page.goto(origin+pathname);
   await expect(page.getByRole('navigation',{name:'Universe rooms'})).toBeVisible();
   for(const width of [320,375,390,430,1280]){
    await page.setViewportSize({width,height:844});
    await checkRooms(page);
   }
   if(process.env.BEAST_EVIDENCE_DIR){
    await fs.mkdir(process.env.BEAST_EVIDENCE_DIR,{recursive:true});
    for(const width of [390,1280]){
     await page.setViewportSize({width,height:844});
     await page.screenshot({path:path.join(process.env.BEAST_EVIDENCE_DIR,`${pathname.slice(1)}-${width}.png`),fullPage:true});
    }
   }
  }
  assert.deepEqual(privateCalls,[],'Public rooms must not call private APIs');
  const publicPrivateRequests=privateCalls.length;
  await page.goto(origin+'/workspace#brain-bay');
  await expect(page.getByLabel('OWNER PASSWORD')).toBeVisible();
  await expect(page.getByRole('button',{name:/Unlock workstation/})).toBeVisible();
  assert.equal(sensorCalls,0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,widths:[320,375,390,430,1280],guestFailureRequests:guestCalls.length,explicitLoopbackRequests:loopbackCalls.length,publicPrivateRequests,ownerLoginRequests:privateCalls,liveInferenceVerified:false}));
 }finally{await context.close();await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
