/* Run against the coordinated production preview. Guest/loopback failures are
 * injected; this acceptance test does not claim live model installation. */
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium,webkit}=require('playwright');
const browserEngine=process.env.BEAST_TEST_BROWSER==='webkit'?'webkit':'chromium';
const expect=require('playwright/test').expect.configure({timeout:20000});

const origin=process.env.BEAST_BROWSER_ORIGIN||process.argv[2]||'http://127.0.0.1:3000';
const key='beastbox-companion-session-v1';
const rooms=['/','/spark/index.html','/beast-cage','/sol-game','/brain-bay','/research','/settings'];
async function readSession(page){return page.evaluate(k=>JSON.parse(localStorage.getItem(k)||'null'),key);}
async function openSharedChat(page){
 await page.locator('button[data-critical-control][aria-controls="beast-chat-overlay"]').click();
 const dialog=page.locator('[data-companion-chat-overlay]');
 await expect(dialog).toBeVisible();
 return dialog;
}
function invariant(session){
 return {id:session.beast.qbeast.profile.id,qbeast:session.beast.qbeast,genome:session.beast.genome,xp:session.beast.xp,bond:session.beast.bond,stage:session.beast.stage,mind:session.mind};
}
async function checkRooms(page){
 const nav=page.getByRole('navigation',{name:'Universe rooms'});
 await expect(nav).toBeVisible();
 const hrefs=await nav.getByRole('link').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('href')));
 assert.deepEqual(hrefs,rooms);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Page must fit the viewport');
}

(async()=>{
 const browser=await (browserEngine==='webkit'?webkit:chromium).launch({headless:true,...(process.env.BEAST_BROWSER_EXECUTABLE?{executablePath:process.env.BEAST_BROWSER_EXECUTABLE}:{}),args:browserEngine==='chromium'?['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader']:[]});
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'no-preference'});
 let sensorCalls=0;
 await context.exposeFunction('__noteSensorRequest',()=>{sensorCalls++;});
 await context.addInitScript(()=>{
  if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>{await window.__noteSensorRequest();throw Error('Unexpected sensor permission request');};
 });
 const page=await context.newPage(),errors=[],privateCalls=[],guestCalls=[],loopbackCalls=[],cloudConfigurationReads=[];
 const anonymousCloudMetadata=await context.request.get(origin+'/api/cosmos/private/session');
 if(anonymousCloudMetadata.status()===200){const metadata=await anonymousCloudMetadata.json();assert.notEqual(metadata.authorized,true);assert.equal(metadata.owner,undefined);assert.equal(metadata.record,undefined);assert.equal(metadata.conversations,undefined);assert.equal(anonymousCloudMetadata.headers()['set-cookie'],undefined);}
 const rscTrace=[];
 page.on('pageerror',error=>errors.push({message:error.message,stack:error.stack,page:page.url(),rscTrace:rscTrace.slice(-12)}));
 page.on('requestfailed',request=>{if(new URL(request.url()).searchParams.has('_rsc'))rscTrace.push({event:'failed',url:request.url(),page:page.url(),error:request.failure()?.errorText});});
 page.on('requestfinished',request=>{if(new URL(request.url()).searchParams.has('_rsc'))rscTrace.push({event:'finished',url:request.url(),page:page.url()});});
 page.on('request',request=>{
  const url=new URL(request.url());
  if(url.searchParams.has('_rsc'))rscTrace.push({event:'started',url:request.url(),page:page.url()});
  if(url.origin===new URL(origin).origin&&url.pathname==='/api/cosmos/private/session'&&request.method()==='GET'){cloudConfigurationReads.push(request.method());return;}
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
  // No saved Beast: open the actual shared chat first; passive page load must not infer.
  let dialog=await openSharedChat(page);
  // Compact modal deliberately hides the longer explanatory subtitle. It is
  // preserved for screen readers and the visible identity heading is checked below.
  await expect(dialog.getByText(/Showing Zeref, the site Beast/)).toHaveCount(1);
  await expect(dialog.getByRole('heading',{name:'Talk to Zeref'})).toBeVisible();
  await expect(dialog.getByText(/Brain: RAWRPHØS guest/)).toBeVisible();
  assert.equal(guestCalls.length,0);assert.equal(loopbackCalls.length,0);
  const visibleNavCount=await page.getByRole('navigation',{name:'Universe rooms'}).count();
  if(visibleNavCount){
   const debug=await page.evaluate(()=>{
    const nav=document.querySelector('nav[aria-label="Universe rooms"]');
    const dialog=document.querySelector('[data-companion-chat-overlay]');
    const chain=[];for(let node=nav;node&&chain.length<10;node=node.parentElement)chain.push({tag:node.tagName,id:node.id,inert:node.inert,ariaHidden:node.getAttribute('aria-hidden')});
    return {width:innerWidth,mobile:matchMedia('(max-width:700px)').matches,fullscreen:document.fullscreenElement?.tagName||null,modal:dialog?.getAttribute('aria-modal'),dialogHidden:dialog?.hidden,hostCount:document.querySelectorAll('[data-companion-chat-host]').length,body:Array.from(document.body.children).map(x=>({tag:x.tagName,id:x.id,inert:x.inert,chatHost:x.hasAttribute('data-companion-chat-host')})),chain};
   });
   throw new Error('Mobile chat exposes background navigation: '+JSON.stringify(debug));
  }
  await dialog.getByRole('button',{name:'Close chat',exact:true}).click();await expect(dialog).toBeHidden();
  await checkRooms(page);
  const launcher=page.locator('button[data-critical-control][aria-controls="beast-chat-overlay"]');
  await expect(launcher).toBeFocused();
  dialog=await openSharedChat(page);
  for(let i=0;i<14;i++){await page.keyboard.press('Tab');assert.equal(await dialog.evaluate(node=>node.contains(document.activeElement)),true,'mobile focus stays inside the dialog');}
  await page.goBack();await expect(dialog).toBeHidden();await checkRooms(page);await expect(launcher).toBeFocused();
  dialog=await openSharedChat(page);
  // Representative keyboard geometry, not a physical iPhone keyboard test.
  await page.evaluate(()=>{Object.defineProperty(visualViewport,'height',{configurable:true,value:300});Object.defineProperty(visualViewport,'offsetTop',{configurable:true,value:90});visualViewport.dispatchEvent(new Event('resize'));});
  await expect.poll(()=>dialog.locator('form').evaluate(node=>{const r=node.getBoundingClientRect();return r.top>=90&&r.bottom<=390;})).toBe(true);
  assert.ok(await dialog.locator('[aria-label^="Conversation with"]').evaluate(node=>node.getBoundingClientRect().height)>=40,'keyboard leaves scrollable conversation space');
  if(process.env.BEAST_EVIDENCE_DIR){await fs.mkdir(process.env.BEAST_EVIDENCE_DIR,{recursive:true});await page.screenshot({path:path.join(process.env.BEAST_EVIDENCE_DIR,'react-keyboard-390.png')});}
  await page.evaluate(()=>{delete visualViewport.height;delete visualViewport.offsetTop;visualViewport.dispatchEvent(new Event('resize'));});
  await page.keyboard.press('Escape');await expect(dialog).toBeHidden();await expect(launcher).toBeFocused();
  // Browser Fullscreen API transitions must relocate the same live popup host.
  // Page fullscreen includes its real chat launcher. Player-owned fullscreen
  // is exercised separately through the actual Game Boy controls.
  await page.locator('html').evaluate(node=>node.requestFullscreen());
  dialog=await openSharedChat(page);
  await expect.poll(()=>dialog.evaluate(node=>!!document.fullscreenElement?.contains(node)&&!node.closest('[inert]'))).toBe(true);
  await page.evaluate(()=>document.exitFullscreen());await expect(dialog).toBeVisible();
  await expect(page.getByRole('navigation',{name:'Universe rooms'})).toHaveCount(0);
  assert.equal(await dialog.evaluate(node=>!!node.closest('[inert]')),false);
  await page.keyboard.press('Escape');await expect(dialog).toBeHidden();await expect(launcher).toBeFocused();

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
  dialog=await openSharedChat(page);
  const before=await readSession(page);
  assert.equal(before.beast.qbeast.profile.id,selectedId);
  const beastName=(await dialog.locator('[data-talk-state] h2').textContent()).replace(/^Talk to /,'');
  assert.ok(beastName&&beastName!=='Zeref'&&!/Finding/.test(beastName),'Talk panel must speak as the saved Beast: '+beastName);

  // Guest host failure: honest offline state, no reply text, no growth from a failed request.
  await dialog.getByLabel(/^Message to /).fill('quiet star');
  await dialog.getByRole('button',{name:'Send',exact:true}).click();
  await expect(dialog.locator('[data-talk-state="offline"]')).toBeVisible();
  await expect(dialog.getByText('Model offline: no reply was received')).toBeVisible();
  assert.equal(guestCalls.length,1);
  assert.deepEqual(Object.keys(guestCalls[0]).sort(),['provider','text']);
  assert.equal(guestCalls[0].provider,'rawrphos-local');
  assert.ok(guestCalls[0].text.includes('You are '+beastName),'identity frame');
  assert.ok(guestCalls[0].text.endsWith('Keeper: quiet star\n'+beastName+':'),'keeper words kept verbatim');
  assert.deepEqual(invariant(await readSession(page)),invariant(before),'failed requests never change the Beast');

  // Local Ollama: explicit choice, persona as system text, honest connection help.
  await dialog.getByRole('button',{name:'Change brain'}).click();
  // Selecting the exact native radio is required: a generic label click can
  // hit nested descriptive text and leave the provider unchanged.
  const ollamaChoice=dialog.locator('input[type="radio"][value="local-ollama"]');
  await ollamaChoice.click();
  const selection=await dialog.evaluate(node=>({
   route:node.querySelector('[data-talk-route]')?.getAttribute('data-talk-route'),
   radios:[...node.querySelectorAll('input[name="talk-brain"]')].map(input=>({value:input.value,checked:input.checked})),
   stored:localStorage.getItem('beastbox-talk-prefs-v1'),
   providerOptionsVisible:!!node.querySelector('input[placeholder*="glacecoil"]')
  }));
  assert.equal(selection.route,'local-ollama','Controlled radio choice must persist in the actual chat panel: '+JSON.stringify(selection));
  await expect(ollamaChoice).toBeChecked();
  await expect(dialog.getByLabel('Model tag')).toBeVisible();
  await dialog.getByLabel('Model tag').fill('tiny:latest');
  assert.equal(loopbackCalls.length,0,'Selecting a brain must not send a message');
  await page.reload();
  dialog=await openSharedChat(page);
  await expect(dialog.getByText(/Brain: My local Ollama/)).toBeVisible();
  await dialog.getByLabel(/^Message to /).fill('quiet star');
  await dialog.getByRole('button',{name:'Send',exact:true}).click();
  await expect(dialog.locator('[data-talk-state="offline"]')).toBeVisible();
  await expect(dialog.getByText(/OLLAMA_ORIGINS=/).first()).toBeVisible();
  assert.equal(loopbackCalls.length,1);
  assert.equal(loopbackCalls[0].model,'tiny:latest');
  assert.equal(loopbackCalls[0].messages[0].role,'system');
  assert.ok(loopbackCalls[0].messages[0].content.includes('You are '+beastName));
  assert.deepEqual(loopbackCalls[0].messages.at(-1),{role:'user',content:'quiet star'});
  assert.deepEqual((await readSession(page)).beast.qbeast,before.beast.qbeast);

  await dialog.getByRole('button',{name:'Close chat'}).click();
  await expect(dialog).toBeHidden();
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
  assert.ok(cloudConfigurationReads.every(method=>method==='GET'),'Passive optional cloud configuration checks must never issue ownership credentials or write private data');
  const publicPrivateRequests=privateCalls.length;
  await page.goto(origin+'/workspace#brain-bay');
  await expect(page.getByLabel('OWNER PASSWORD')).toBeVisible();
  await expect(page.getByRole('button',{name:/Unlock workstation/})).toBeVisible();
  assert.equal(sensorCalls,0);
  assert.equal(rscTrace.filter(row=>row.event==='started'&&new URL(row.url).pathname==='/sol-game').length,0,'An unstarted Game Boy never speculatively loads its route while the visitor talks elsewhere');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,browserEngine,physicalDevice:false,widths:[320,375,390,430,1280],guestFailureRequests:guestCalls.length,explicitLoopbackRequests:loopbackCalls.length,publicPrivateRequests,ownerLoginRequests:privateCalls,liveInferenceVerified:false}));
 }finally{await context.close();await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
