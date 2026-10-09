/** Actual production browser: retained QBEAST, native save, game controls, guest inference. */
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root='https://www.beastboxcosmos.xyz',dir=path.resolve('browser-evidence/final-umbrascale-production');
const project=path.resolve('experiment-evidence/final-live-umbrascale-001'),clock=()=>new Date().toISOString();
const prompts=[
'Hi Umbrascale. You came from recorded IBM quantum measurements. What shall we explore together?',
'While we play Lost COSMOS, tell me what you can actually observe and what you cannot know.',
'We pressed A and Start on the real game. Give me a short suggestion for our next move.'
];
(async()=>{
 await fs.mkdir(dir,{recursive:true});
 const [snapshot,session,genesis]=await Promise.all(['qbeast.json','unsigned-session.json','receipt.json'].map(async p=>JSON.parse(await fs.readFile(path.join(project,p),'utf8'))));
 assert.equal(snapshot.profile.id,'bb-8546076e');assert.equal(genesis.qbeast.id,snapshot.profile.id);
 assert.equal(genesis.provenance.genesis_job,'db4m3bslf4us73c2ui9g');
 const result={schema:'beastbox-production-umbrascale-chat-v1',started:clock(),origin:root,qbeast_id:snapshot.profile.id,ibm_source_job:genesis.provenance.genesis_job,
 hardware_status:'COMPLETED BEFORE THIS BROWSER RUN - NO CONCURRENT QPU JOB',azure_source_job:'32d6fc6c-c42d-11f1-ae67-000d3ad41960',kind:'Actual public production browser + genuine guest response + native controls',turns:[],network:[],errors:[],native:null,passed:false};
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const ctx=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,recordVideo:{dir:path.join(dir,'video'),size:{width:390,height:844}}});
 const page=await ctx.newPage();
 page.on('pageerror',e=>result.errors.push({time:clock(),message:String(e.message).slice(0,300)}));
 page.on('response',r=>{if(new URL(r.url()).pathname==='/api/guest')result.network.push({time:clock(),status:r.status(),path:'/api/guest',method:r.request().method()});});
 try{
  const spark=await page.goto(root+'/spark/index.html',{waitUntil:'domcontentloaded',timeout:45000});
  assert.equal(spark.status(),200);await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,null,{timeout:45000});
  await page.evaluate(async ({snapshot,session})=>{
   const {selectSpark,saveSparkSession,withSparkLock}=await import('/spark/identity.mjs');
   const {importSession}=await import('/spark/shared/session.mjs');
   await withSparkLock(()=>{selectSpark(localStorage,session.beast.genome,{snapshot});saveSparkSession(localStorage,importSession(session));});
  },{snapshot,session});
  const source=await page.request.get(root+'/spark/ibm-final-live-reality-probe-20261009.json');
  assert.equal(source.status(),200);assert.equal((await source.json()).runs?.[0]?.j,genesis.provenance.genesis_job);
  const game=await page.goto(root+'/sol-game',{waitUntil:'domcontentloaded',timeout:45000});
  assert.equal(game.status(),200);
  const shell=page.locator('[data-lost-cosmos-player-shell]');
  const send=shell.getByRole('button',{name:'SEND BEAST',exact:true});await send.waitFor({timeout:50000});
  await page.waitForFunction(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent?.trim()==='SEND BEAST');return b&&!b.disabled;},null,{timeout:40000});
  await send.click();await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:40000});
  await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));assert.ok(core,'Native GBA core not mounted');
  await core.waitForFunction(()=>window.EJS_emulator?.gameManager?.getSaveFile(false)?.length===32768,null,{timeout:90000});
  await core.evaluate(()=>{const gm=EJS_emulator.gameManager,old=gm.simulateInput.bind(gm);window.__trace=[];gm.simulateInput=(...a)=>{window.__trace.push(a);return old(...a);};});
  const pad=shell.locator('[data-handheld-controls]');
  await pad.getByRole('button',{name:'A',exact:true}).tap();
  await pad.getByRole('button',{name:'Start',exact:true}).tap();
  const native=await core.evaluate(()=>({save_bytes:EJS_emulator.gameManager.getSaveFile(false).length,pressed:window.__trace}));
  assert.deepEqual(native.pressed.slice(0,2),[[0,8,1],[0,8,0]]);
  assert.equal(native.save_bytes,32768);result.native=native;
  await core.locator('#game canvas').first().screenshot({path:path.join(dir,'native-canvas.png')});
  const panel=page.locator('[data-spark-game-talk]');
  await panel.waitFor({timeout:30000});assert.equal(await panel.getAttribute('data-creature-id'),snapshot.profile.id);
  await panel.getByRole('button',{name:/TALK TO .*💬/}).click();
  const opticalOptIn=panel.getByLabel('Include fresh native pixel signals');
  try { await opticalOptIn.check({timeout:6000}); }
  catch(error) { result.vision_opt_in_failure=String(error).slice(0,300); }
  result.opted_in_native_pixel_signals=await opticalOptIn.isChecked().catch(()=>false);
  if(result.opted_in_native_pixel_signals){
   await panel.getByRole('button',{name:/LOOK AT GAME/}).click();
   result.game_vision_status=String(await panel.locator('p[role="status"]').first().textContent()).slice(0,220);
  } else result.game_vision_status='Native pixel opt-in failed; no game image signal supplied';
  for(const saying of prompts){
   await panel.getByRole('textbox',{name:/Message to/}).fill(saying);
   const res=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/guest'&&r.request().method()==='POST',{timeout:70000});
   const begin=clock();await panel.getByRole('button',{name:'SEND TO MODEL',exact:true}).click();
   const answer=await res;
   await page.waitForFunction(()=>!document.querySelector('[data-spark-game-talk] button[type="submit"]')?.textContent?.includes('ANSWERING'),null,{timeout:70000});
   const turns=await panel.locator('[aria-label="This Beast’s recent chat"] p').allTextContents();
   const uiStatus=String(await panel.locator('form + p[role="status"]').textContent()).trim();
   const reply=turns.at(-1)||'';
   const measured={begin,end:clock(),question:saying,status:answer.status(),model_reply:reply,ui_status:uiStatus,game_still_running:await shell.getAttribute('data-running')};
   result.turns.push(measured);
   if(!answer.ok()||!reply.startsWith('Umbrascale:')||!uiStatus.includes('reply saved'))throw Error('Live guest turn did not verify: '+JSON.stringify(measured));
  }
  await page.screenshot({path:path.join(dir,'production-conversation.png'),fullPage:true});
  result.passed=true;
 }catch(e){result.failure=String(e?.stack||e).slice(0,2500);throw e;}
 finally{
  result.finished=clock();await fs.writeFile(path.join(dir,'proof.json'),JSON.stringify(result,null,2)+'\n');
  const video=page.video();await ctx.close();if(video)await video.saveAs(path.join(dir,'production-game.webm'));await browser.close();
  console.log('PRODUCTION_UMBRASCALE_PROOF '+JSON.stringify({passed:result.passed,turns:result.turns.length,game:result.native,network:result.network,failure:result.failure||null}));
 }
})().catch(e=>{console.error('PRODUCTION_UMBRASCALE_ERROR',e?.stack||String(e));process.exitCode=1;});
