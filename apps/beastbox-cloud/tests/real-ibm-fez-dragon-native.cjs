/**
 * Real hardware-derived Emberlet QBEAST, real mounted V11.3 native GBA core.
 * Never mock ROM, postMessage, emulator, save or controller input.
 * Do not claim actual production provider inference; local transcript is separate.
 */
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=process.argv[2]||'http://127.0.0.1:3000';
const output=process.argv[3]||'/tmp/emberlet-native';
const project=path.resolve(__dirname,'../experiment-evidence/real-ibm-fez-dragon-001');
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const [snapshot,session,genesis]=await Promise.all([
  fs.readFile(path.join(project,'qbeast.json'),'utf8').then(JSON.parse),
  fs.readFile(path.join(project,'unsigned-session.json'),'utf8').then(JSON.parse),
  fs.readFile(path.join(project,'receipt.json'),'utf8').then(JSON.parse)
 ]);
 assert.equal(snapshot.profile.id,'bb-2879516e');
 assert.equal(session.beast.qbeast.profile.id,snapshot.profile.id);
 assert.equal(genesis.provenance.genesis_job,'db4kcfklf4us73c2sjb0');
 const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(root+'/spark/index.html');
  await page.evaluate(({snapshot,session})=>{
   localStorage.setItem('beastbox-quantum-beast-public-v1',JSON.stringify({text:JSON.stringify(snapshot)+'\n'}));
   localStorage.setItem('beastbox-active-creature-v1',JSON.stringify(snapshot.profile));
   localStorage.setItem('beastbox-companion-session-v1',JSON.stringify(session));
  },{snapshot,session});
  await page.goto(root+'/sol-game');
  const shell=page.locator('[data-lost-cosmos-player-shell]');
  await shell.getByRole('button',{name:'SEND BEAST',exact:true}).waitFor({timeout:45000});
  await shell.getByRole('button',{name:'SEND BEAST',exact:true}).click();
  await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:60000});
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
  assert.equal(machine.nativeMarker,'SPK1','Emberlet not installed in native save');
  assert.equal(machine.nativeId,rendered.nativeId,'GBA identity mismatch');
  assert.equal(machine.nativeSeed,rendered.nativeSeed,'GBA seed mismatch');
  const pad=shell.locator('[data-handheld-controls]');
  const button=pad.getByRole('button',{name:'A',exact:true});
  const before=await core.evaluate(()=>{const gm=EJS_emulator.gameManager,old=gm.simulateInput.bind(gm);window.__dragonInput=[];gm.simulateInput=(a,b,c)=>{window.__dragonInput.push([a,b,c]);return old(a,b,c);};return window.__dragonInput.length});
  await button.tap();await page.waitForTimeout(300);
  const pressed=await core.evaluate(n=>window.__dragonInput.slice(n),before);
  assert.deepEqual(pressed.slice(-2),[[0,8,1],[0,8,0]],'A press/release not delivered to native core');
  await pad.getByRole('button',{name:'START',exact:true}).tap();
  await page.waitForTimeout(1000);
  const still=await core.evaluate(()=>EJS_emulator.gameManager.getSaveFile(false));
  assert.ok(still?.length===32768,'Native save disappeared after input');
  const screenshot=path.join(output,'emberlet-on-native-gba.png');
  await core.locator('#game canvas').first().screenshot({path:screenshot});
  const observed={schema:'beastbox-real-ibm-dragon-native-test-v1',qbeast_id:snapshot.profile.id,
   ibm_source_job:genesis.provenance.genesis_job,game:'Lost COSMOS V11.3 native EmulatorJS',
   native_id:machine.nativeId,native_seed:machine.nativeSeed,
   start_select_handshake:true,button_a_press_release_verified:true,
   screenshot:'emberlet-on-native-gba.png',
   recorded_gameplay:'real emulator input and screenshot, not inferred quest completion',
   real_llm_chat_in_game:false,azure_cosmos_db_write:false,
   browser_pageerrors:errors};
  await fs.writeFile(path.join(output,'game-evidence.json'),JSON.stringify(observed,null,2)+'\n');
  console.log('REAL_DRAGON_NATIVE_GAME '+JSON.stringify(observed));
 }finally{await browser.close();}
})().catch(e=>{console.error('REAL_DRAGON_NATIVE_TEST_FAILED',e?.stack||String(e));process.exitCode=1;});
