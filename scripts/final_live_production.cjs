/**
 * Real hardware-derived Marrakesh QBEAST, real mounted V11.3 native GBA core.
 * Never mock ROM, postMessage, emulator, save or controller input.
 * Calls the actual production guest model through the real game UI; no route mocks.
 */
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=process.argv[2]||'https://www.beastboxcosmos.xyz';
assert.equal(root,'https://www.beastboxcosmos.xyz','Live acceptance must use the actual production origin');
const output=process.argv[3]||'/tmp/marrakesh-dragon-native';
const project=process.argv[4]?path.resolve(process.argv[4]):path.resolve(__dirname,'../apps/beastbox-cloud/experiment-evidence/final-live-umbrascale-001');
const expectedIdentity=process.argv[5]||'bb-8546076e';
const expectedJob=process.argv[6]||'db4m3bslf4us73c2ui9g';
const sourcePath=process.argv[7]||'/spark/ibm-final-live-reality-probe-20261009.json';
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
  // Hold trusted touch input across actual GBA frames; a one-frame tap can
  // reach the controller bridge without being sampled by the title screen.
  const touch=await context.newCDPSession(page);
  const hold=async(name,ms=220)=>{
   const node=pad.getByRole('button',{name,exact:true});await node.scrollIntoViewIfNeeded();
   const box=await node.boundingBox();assert.ok(box);
   await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x+box.width/2,y:box.y+box.height/2,id:1}]});
   await page.waitForTimeout(ms);
   await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
   await page.waitForTimeout(350);
  };
  const initialized=await core.evaluate(()=>{const gm=EJS_emulator.gameManager;gm.saveSaveFiles();const bytes=gm.getSaveFile(false);return bytes&&String.fromCharCode(...bytes.subarray(1024,1028))==='LCR1';});
  if(!initialized){await hold('A');await page.waitForTimeout(600);await hold('Start');}
  await core.waitForFunction(()=>{
   const gm=EJS_emulator.gameManager;gm.saveSaveFiles();const bytes=gm.getSaveFile(false);
   return bytes&&String.fromCharCode(...bytes.subarray(1024,1028))==='LCR1';
  },null,{timeout:90000});
  await page.waitForTimeout(3000);
  await core.locator('#game canvas').first().screenshot({path:path.join(output,'umbrascale-overworld-before.png')});
  const movement=[];
  for(const name of ['Right','Down','Left','Up']){
   const began=new Date().toISOString();await hold(name,450);movement.push({button:name,hold_ms:450,started_utc:began,completed_utc:new Date().toISOString()});
  }
  await core.locator('#game canvas').first().screenshot({path:path.join(output,'umbrascale-overworld-after.png')});
  const screenshot=path.join(output,'umbrascale-live-native.png');
  await core.locator('#game canvas').first().screenshot({path:screenshot});
  const handshake=process.env.BEAST_LIVE_QPU_HANDSHAKE_DIR;
  const qpuStatus=async()=>handshake?JSON.parse(await fs.readFile(path.join(handshake,'qpu-status.json'),'utf8')):null;
  if(handshake){
   await fs.mkdir(handshake,{recursive:true});
   await fs.writeFile(path.join(handshake,'browser-ready.json'),JSON.stringify({utc:new Date().toISOString(),qbeast_id:snapshot.profile.id,native_id:machine.nativeId,actual_native_boot:true}));
   const deadline=Date.now()+10*60*1000;
   while(true){
    let status=null;try{status=await qpuStatus();}catch{}
    if(status?.status==='RUNNING')break;
    if(status&&['DONE','ERROR','CANCELLED','FAILED'].includes(status.status))throw Error('Hardware probe became terminal before live conversation; overlap is not claimed');
    if(Date.now()>deadline)throw Error('No RUNNING IBM job observed before deadline');
    await page.waitForTimeout(200);
   }
  }
  const panel=shell.locator('[data-spark-game-talk]');
  await panel.getByRole('button',{name:/^TALK TO /}).click();
  await panel.getByRole('checkbox',{name:/Include fresh native pixel signals/}).check();
  const liveConversation=[],frameObservations=[];
  for(const [i,message] of [
   'Hello Umbrascale. Your genome came from IBM Fez measurements and a 512-shot Azure simulation. We are running a new IBM probe while you play. What do you notice?',
   'We pressed A and Start in the actual GBA cartridge. Your identity is still bb-8546076e. The screen signals are brightness and color measurements. How are you feeling?',
   'Your assay explored 46 times and listened 24 times; energy reached zero. Your identity and traces are saved. Would you like to rest here?'
  ].entries()){
   await panel.getByRole('button',{name:/LOOK AT GAME/}).click();
   await page.waitForTimeout(300);
   const frameText=await panel.getByRole('status').allTextContents();frameObservations.push({utc:new Date().toISOString(),actual_ui:frameText.filter(x=>/Observed game pixels|readable native frame/.test(x))});
   await fs.writeFile(path.join(output,'frame-observations.json'),JSON.stringify(frameObservations,null,2)+'\n');
   const beforeQpu=await qpuStatus();
   const started=new Date().toISOString();
   await panel.getByRole('textbox').fill(message);
   const responsePromise=page.waitForResponse(r=>r.url()===root+'/api/guest'&&r.request().method()==='POST',{timeout:70000});
   await panel.getByRole('button',{name:'SEND TO MODEL',exact:true}).click();
   const response=await responsePromise,payload=await response.json();
   await fs.writeFile(path.join(output,'model-response-'+i+'.json'),JSON.stringify({http_status:response.status(),observed_utc:new Date().toISOString(),payload},null,2)+'\n');
   assert.equal(response.status(),200,'Actual guest inference failed');
   assert.equal(payload.provider,'rawrphos-local');assert.equal(payload.model,'rawrphos-native');assert.equal(payload.step,14000);assert.equal(payload.guest_stateless,true);assert.ok(payload.reply?.trim());
   await page.waitForFunction(reply=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')||'null')?.chat?.some(x=>x.role!=='you'&&x.text===reply),payload.reply.trim(),{timeout:15000});
   const ended=new Date().toISOString(),afterQpu=await qpuStatus();
   liveConversation.push({turn:i,started_utc:started,completed_utc:ended,observer_input:message,actual_model_reply:payload.reply,provider:payload.provider,model:payload.model,step:payload.step,checkpoint_sha256:payload.checkpoint_sha256,guest_stateless:payload.guest_stateless,qpu_before:beforeQpu,qpu_after:afterQpu,request_started_during_qpu_running:beforeQpu?.status==='RUNNING'});
   await fs.writeFile(path.join(output,'live-conversation.json'),JSON.stringify(liveConversation,null,2)+'\n');
   assert.equal(page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html')),core,'Actual conversation remounted the native game');
   await pad.getByRole('button',{name:'A',exact:true}).tap();
  }
  if(handshake)assert.ok(liveConversation.some(turn=>turn.request_started_during_qpu_running),'No actual conversation request overlapped RUNNING IBM job');
  await page.screenshot({path:path.join(output,'umbrascale-live-conversation.png'),fullPage:true});
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));
  assert.equal(saved.beast.qbeast.profile.id,snapshot.profile.id);
  assert.equal(saved.beast.qvmStimulus.job_id,'32d6fc6c-c42d-11f1-ae67-000d3ad41960','Fresh Azure stimulus marker disappeared');
  await fs.writeFile(path.join(output,'post-live-session.json'),JSON.stringify(saved,null,2)+'\n');
  const battery=await core.evaluate(()=>{const gm=EJS_emulator.gameManager;gm.saveSaveFiles();return Array.from(gm.getSaveFile(false));});
  assert.equal(battery.length,32768);
  assert.equal(new DataView(Uint8Array.from(battery).buffer).getUint32(24712,true),rendered.nativeId,'Live gameplay changed the measured companion identity');
  await fs.writeFile(path.join(output,'umbrascale-live-native.sav'),Buffer.from(battery));
  const observed={schema:'beastbox-final-live-production-dragon-test-v1',qbeast_id:snapshot.profile.id,
   ibm_source_job:genesis.provenance.genesis_job,game:'Lost COSMOS V11.3 native EmulatorJS',
   native_id:machine.nativeId,native_seed:machine.nativeSeed,
   start_select_handshake:true,button_a_press_release_verified:true,native_roster_initialized:true,observed_movement_inputs:movement,
   screenshot:'umbrascale-live-native.png',video:'native-gameplay.webm',
   native_save_marker:machine.nativeMarker,native_save_bytes:machine.length,actual_a_input:pressed.slice(-2),
   recorded_gameplay:'real emulator input and screenshot, not inferred quest completion',
   real_llm_chat_in_game:true,azure_cosmos_db_write:false,conversation:liveConversation,game_frame_observations:frameObservations,
   browser_pageerrors:errors};
  await fs.writeFile(path.join(output,'game-evidence.json'),JSON.stringify(observed,null,2)+'\n');
  console.log('FINAL_LIVE_PRODUCTION_GAME '+JSON.stringify(observed));
 }finally{const video=page.video();await context.close();if(video)await video.saveAs(path.join(output,'native-gameplay.webm'));await browser.close();}
})().catch(e=>{console.error('FINAL_LIVE_PRODUCTION_FAILED',e?.stack||String(e));process.exitCode=1;});
