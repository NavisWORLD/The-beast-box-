/**
 * Real hardware-derived Marrakesh QBEAST, real mounted V11.3 native GBA core.
 * Never mock ROM, postMessage, emulator, save or controller input.
 * Do not claim actual production provider inference; local transcript is separate.
 */
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=process.argv[2]||'http://127.0.0.1:3000';
const output=process.argv[3]||'/tmp/marrakesh-dragon-native';
const project=process.argv[4]?path.resolve(process.argv[4]):path.resolve(__dirname,'../experiment-evidence/real-ibm-marrakesh-dragon-001');
const expectedIdentity=process.argv[5]||'bb-82fbc8ff';
const expectedJob=process.argv[6]||'db4l2uclf4us73c2td10';
const sourcePath=process.argv[7]||'/spark/ibm-marrakesh-reality-probe-20261009.json';
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const [snapshot,session,genesis]=await Promise.all([
  fs.readFile(path.join(project,'qbeast.json'),'utf8').then(JSON.parse),
  fs.readFile(path.join(project,'unsigned-session.json'),'utf8').then(JSON.parse),
  fs.readFile(path.join(project,'receipt.json'),'utf8').then(JSON.parse)
 ]);
 assert.equal(snapshot.profile.id,expectedIdentity,'Dragon must keep its measured-genesis identity');
 assert.equal(snapshot.profile.id,genesis.qbeast.id,'New dragon QBEAST contract mismatch');
 assert.equal(session.beast.qbeast.profile.id,snapshot.profile.id);
 assert.equal(genesis.provenance.genesis_job,expectedJob);
 const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,recordVideo:{dir:path.join(output,'video'),size:{width:390,height:844}}});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(root+'/spark/index.html');
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,null,{timeout:30000});
  // Exercise the real selector rather than bypassing cross-tab/save authority.
  await page.evaluate(async ({snapshot,session})=>{
   const {selectSpark,saveSparkSession,withSparkLock}=await import('/spark/identity.mjs');
   const {importSession}=await import('/spark/shared/session.mjs');
   await withSparkLock(()=>{selectSpark(localStorage,session.beast.genome,{snapshot});saveSparkSession(localStorage,importSession(session));});
  },{snapshot,session});
  const seedResponse=await page.request.get(root+sourcePath);
  assert.equal(seedResponse.status(),200,'IBM Marrakesh public seed registry is missing');
  const realSource=await seedResponse.json();
  assert.equal(realSource.runs?.[0]?.j,expectedJob,'Public IBM job mismatch');
  await page.goto(root+'/sol-game');
  const shell=page.locator('[data-lost-cosmos-player-shell]');
  const sendButton=shell.getByRole('button',{name:'SEND BEAST',exact:true});
  await sendButton.waitFor({timeout:45000});
  try{
   await page.waitForFunction(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent?.trim()==='SEND BEAST');return b&&!b.disabled;},null,{timeout:20000});
  }catch(error){
   const diag=await page.evaluate(()=>({status:[...document.querySelectorAll('[role="status"]')].map(x=>x.textContent?.slice(0,200)),
    persisted:!!localStorage.getItem('beastbox-companion-session-v1'),selected:!!localStorage.getItem('beastbox-quantum-beast-public-v1')}));
   throw new Error('Marrakesh dragon refused by device recovery: '+JSON.stringify(diag)+' '+String(error));
  }
  await sendButton.click();
  try{
   await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:25000});
  }catch(e){
   const diag=await page.evaluate(()=>({
    playerStatus:[...document.querySelectorAll('[data-lost-cosmos-player-shell] [role="status"]')].map(x=>x.textContent?.slice(0,350)),
    creatureId:document.querySelector('[data-lost-cosmos-player-shell]')?.getAttribute('data-creature-id'),
    savedId:JSON.parse(localStorage.getItem('beastbox-companion-session-v1')||'null')?.beast?.qbeast?.profile?.id,
    frameCount:document.querySelectorAll('[data-lost-cosmos-player-shell] iframe').length
   }));
   throw Error('Native Beast admission failed: '+JSON.stringify({diag,frameUrls:page.frames().map(f=>f.url()).slice(0,4),errors})+' '+String(e));
  }
  await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));
  assert.ok(core,'real Game Boy core not mounted');
  await core.waitForFunction(()=>window.EJS_emulator?.gameManager?.getSaveFile(false)?.length===32768,null,{timeout:90000});
  const machine=await core.evaluate(async()=>{
   const gm=EJS_emulator.gameManager;
   const {importPayload}=await import('../spark-beasts/trade.mjs');
   const text=localStorage.getItem('beastbox-quantum-beast-public-v1');
   void text;
   const save=gm.getSaveFile(false),view=new DataView(save.buffer,save.byteOffset,save.byteLength);
   return {nativeId:view.getUint32(24712,true),nativeSeed:view.getUint32(24716,true),
    nativeMarker:String.fromCharCode(...save.subarray(24704,24708)),length:save.length};
  });
  // Native GBA includes an encoded 32-bit public ID, not the full QBEAST label.
  const rendered=await core.evaluate(async snapshot=>{
   const {importPayload}=await import('../spark-beasts/trade.mjs');
   const result=await importPayload(new TextEncoder().encode(JSON.stringify(snapshot)));
   return {nativeId:result.publicId,nativeSeed:result.profile.gameSeed};
  },snapshot);
  assert.equal(machine.nativeMarker,'SPK1','Marrakesh dragon not installed in native save');
  assert.equal(machine.nativeId,rendered.nativeId,'GBA identity mismatch');
  assert.equal(machine.nativeSeed,rendered.nativeSeed,'GBA seed mismatch');
  const pad=shell.locator('[data-handheld-controls]');
  const button=pad.getByRole('button',{name:'A',exact:true});
  const before=await core.evaluate(()=>{const gm=EJS_emulator.gameManager,old=gm.simulateInput.bind(gm);window.__dragonInput=[];gm.simulateInput=(a,b,c)=>{window.__dragonInput.push([a,b,c]);return old(a,b,c);};return window.__dragonInput.length});
  await button.tap();await page.waitForTimeout(300);
  const pressed=await core.evaluate(n=>window.__dragonInput.slice(n),before);
  assert.deepEqual(pressed.slice(-2),[[0,8,1],[0,8,0]],'A press/release not delivered to native core');
  await pad.getByRole('button',{name:'Start',exact:true}).tap();
  await page.waitForTimeout(1000);
  const still=await core.evaluate(()=>EJS_emulator.gameManager.getSaveFile(false));
  assert.ok(still?.length===32768,'Native save disappeared after input');
  const screenshot=path.join(output,'marrakesh-dragon-on-native-gba.png');
  await core.locator('#game canvas').first().screenshot({path:screenshot});
  const observed={schema:'beastbox-marrakesh-real-ibm-dragon-native-test-v1',qbeast_id:snapshot.profile.id,
   ibm_source_job:genesis.provenance.genesis_job,game:'Lost COSMOS V11.3 native EmulatorJS',
   native_id:machine.nativeId,native_seed:machine.nativeSeed,
   start_select_handshake:true,button_a_press_release_verified:true,
   screenshot:'marrakesh-dragon-on-native-gba.png',video:'native-gameplay.webm',
   native_save_marker:machine.nativeMarker,native_save_bytes:machine.length,actual_a_input:pressed.slice(-2),
   recorded_gameplay:'real emulator input and screenshot, not inferred quest completion',
   real_llm_chat_in_game:false,azure_cosmos_db_write:false,
   browser_pageerrors:errors};
  await fs.writeFile(path.join(output,'game-evidence.json'),JSON.stringify(observed,null,2)+'\n');
  console.log('MARRAKESH_DRAGON_NATIVE_GAME '+JSON.stringify(observed));
 }finally{const video=page.video();await context.close();if(video)await video.saveAs(path.join(output,'native-gameplay.webm'));await browser.close();}
})().catch(e=>{console.error('MARRAKESH_DRAGON_NATIVE_TEST_FAILED',e?.stack||String(e));process.exitCode=1;});
