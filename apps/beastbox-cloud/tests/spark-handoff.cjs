/* Actual cross-origin parent handoff and vendored native core; no owner/model calls. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs/promises');
const root=process.argv[2]||'http://127.0.0.1:3000',out=process.argv[3]||'/tmp/sol-handoff',localGame=process.argv[4];
(async()=>{
 await fs.mkdir(out,{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true}),page=await context.newPage(),errors=[],wrong=[],modelRequests=[];
 await page.addInitScript(()=>{const buttons=Array.from({length:16},()=>({pressed:false,value:0}));window.__beastBoxFakeGamepad={id:'Beast Box CI standard controller',index:0,connected:true,mapping:'standard',timestamp:0,buttons,axes:[0,0],vibrationActuator:null};Object.defineProperty(navigator,'getGamepads',{configurable:true,value:()=>[window.__beastBoxFakeGamepad]});});
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/SIM_EARTH|Pocket.Reality|standalone\//i.test(r.url()))wrong.push(r.url())});
 page.on('request',r=>{if(r.url().startsWith(root+'/api/guest')||r.url().startsWith(root+'/api/bridge'))modelRequests.push(r.url())});
 if(localGame)await context.route('https://navisworld.github.io/**',async route=>{
  const url=new URL(route.request().url()),prefix='/Cosmic-synapse-the-living-universe-sim-engine-';
  assert.ok(url.pathname.startsWith(prefix));const response=await route.fetch({url:localGame+url.pathname.slice(prefix.length)+url.search});await route.fulfill({response});
 });
 try{
  await page.goto(root+'/spark/index.html');await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
  await page.locator('#generate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Spawned'));
  const snapshot=await page.evaluate(()=>JSON.parse(JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1')).text));
  await page.goto(root+'/beast-cage/go');await page.locator('[data-handheld-controls="game-boy"]').waitFor({state:'visible'});const player=page.locator('[data-lost-cosmos-dock] [data-spark-player]');await player.getByRole('button',{name:'SEND BEAST',exact:true}).click();
  await player.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:60000});
  const gate=player.frameLocator('iframe'),hand=gate.frameLocator('#handheld');
  await player.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
  await hand.locator('#audio').click();await hand.locator('#audio').waitFor({state:'visible'});
  assert.equal(await hand.locator('#audio').getAttribute('aria-pressed'),'true','explicit game-audio consent is reachable in the nested handheld');
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));assert.ok(core);
  await core.evaluate(()=>{const gm=EJS_emulator.gameManager,original=gm.simulateInput.bind(gm);window.__beastBoyInputs=[];gm.simulateInput=(player,index,value)=>{window.__beastBoyInputs.push([player,index,value]);return original(player,index,value);};});
  const deckA=page.locator('[data-handheld-controls="game-boy"]').getByRole('button',{name:'A',exact:true});
  await deckA.tap();await page.waitForTimeout(120);
  assert.deepEqual(await core.evaluate(()=>window.__beastBoyInputs.slice(-2)),[[0,8,1],[0,8,0]],'real mobile Beast Boy A tap reaches the mounted native core');
  const beforeGamepad=await core.evaluate(()=>window.__beastBoyInputs.length);
  await page.evaluate(()=>{const b=window.__beastBoxFakeGamepad.buttons[0];b.pressed=true;b.value=1;window.__beastBoxFakeGamepad.timestamp=performance.now();});
  for(let i=0;i<30&&await core.evaluate(n=>window.__beastBoyInputs.length<=n,beforeGamepad);i++)await page.waitForTimeout(20);
  await page.evaluate(()=>{const b=window.__beastBoxFakeGamepad.buttons[0];b.pressed=false;b.value=0;window.__beastBoxFakeGamepad.timestamp=performance.now();});
  for(let i=0;i<30&&await core.evaluate(n=>window.__beastBoyInputs.length<n+2,beforeGamepad);i++)await page.waitForTimeout(20);
  assert.deepEqual(await core.evaluate(n=>window.__beastBoyInputs.slice(n,n+2),beforeGamepad),[[0,8,1],[0,8,0]],'standard Gamepad API A press/release reaches the same mounted native core');
  const deckInput=async(button,down)=>page.evaluate(({button,down})=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button,down}})),{button,down});
  const beforeBad=await core.evaluate(()=>window.__beastBoyInputs.length);await deckInput('nope',true);await page.waitForTimeout(50);
  assert.equal(await core.evaluate(()=>window.__beastBoyInputs.length),beforeBad,'unknown Beast Boy controls are rejected');
  const verified=await core.evaluate(async snapshot=>{
   const {importPayload}=await import('../spark-beasts/trade.mjs');
   const record=await importPayload(new TextEncoder().encode(JSON.stringify(snapshot))),gm=EJS_emulator.gameManager,save=gm.getSaveFile(false),dv=new DataView(save.buffer,save.byteOffset,save.byteLength);
   return {id:record.publicId,seed:record.profile.gameSeed,nativeId:dv.getUint32(24712,true),nativeSeed:dv.getUint32(24716,true),bytes:save.length,art:String.fromCharCode(...save.subarray(24704,24708))};
  },snapshot);
  assert.equal(verified.id,verified.nativeId);assert.equal(verified.seed,verified.nativeSeed);assert.equal(verified.art,'SPK1');assert.equal(verified.bytes,32768);
  await hand.locator('#game canvas').first().screenshot({path:out+'/native-public-title.png'});
  assert.deepEqual(modelRequests,[],'opening the cartridge never automatically calls a model');
  const talk=player.locator('[data-spark-game-talk]'),before=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));
  await talk.getByRole('button',{name:/^TALK TO /}).click();
  await talk.getByRole('button',{name:'PET',exact:true}).click();
  await talk.locator('[data-game-care]').filter({hasText:'Care XP '+(before.beast.xp+4)}).waitFor();
  // This is an explicit response-contract fixture. Production model inference
  // is checked separately against the live, existing RAWRPHØS guest host.
  let sent;
  await context.route(root+'/api/guest',async route=>{
   sent=route.request().postDataJSON();
   await route.fulfill({json:{provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:'Cartridge chat contract confirmed.'}});
  });
  await talk.getByRole('textbox').fill('Hello from the cartridge');await talk.getByRole('button',{name:'SEND TO MODEL',exact:true}).click();
  await talk.getByRole('status').filter({hasText:'reply saved with this Beast'}).waitFor();
  assert.equal(sent.provider,'rawrphos-local');assert.match(sent.text,/Lost COSMOS/);assert.match(sent.text,/Hello from the cartridge/);
  assert.ok(!sent.text.includes(snapshot.profile.id));assert.ok(!sent.text.includes(snapshot.profile.seed));
  const afterTalk=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));
  assert.deepEqual(afterTalk.beast.qbeast,snapshot);assert.equal(afterTalk.beast.stage,1);assert.equal(afterTalk.beast.xp,before.beast.xp+7);
  assert.equal(afterTalk.chat.at(-1).text,'Cartridge chat contract confirmed.');
  assert.equal(page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html')),core,'chat never remounts the native game');
  await talk.getByRole('button',{name:'CLOSE TALK',exact:true}).click();await talk.getByRole('button',{name:/^TALK TO /}).click();
  assert.equal(page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html')),core);
  await context.route(root+'/api/guest',async route=>route.fulfill({json:{reply:'Unverified fake answer'}}));
  await talk.getByRole('textbox').fill('A second message');await talk.getByRole('button',{name:'SEND TO MODEL',exact:true}).click();
  await talk.getByRole('status').filter({hasText:'no verified text'}).waitFor();
  assert.equal(await talk.getByText('Unverified fake answer',{exact:true}).count(),0);
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.xp),afterTalk.beast.xp);
  await context.route(root+'/api/guest',async route=>{
   await new Promise(resolve=>setTimeout(resolve,500));
   try{await route.fulfill({json:{provider:'rawrphos-local',model:'rawrphos-native',step:14000,guest_stateless:true,reply:'Canceled response must not be remembered.'}});}catch{/* browser canceled the request */}
  });
  await talk.getByRole('textbox').fill('Cancel this request');await talk.getByRole('button',{name:'SEND TO MODEL',exact:true}).click();
  await talk.getByRole('button',{name:'CANCEL',exact:true}).click();await page.waitForTimeout(600);
  assert.equal(await talk.getByText('Canceled response must not be remembered.',{exact:true}).count(),0);
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.xp),afterTalk.beast.xp);
  assert.equal(page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html')),core);
  assert.ok(modelRequests.every(url=>url===root+'/api/guest'));
  await page.screenshot({path:out+'/native-game-cage-talk.png',fullPage:true});
  await page.goto(root+'/beast-cage');await page.waitForFunction(id=>document.querySelector('[data-spark-beast][data-creature-id="'+id+'"]'),snapshot.profile.id);
  const afterNavigation=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));
  assert.deepEqual(afterNavigation.beast.qbeast,snapshot);assert.deepEqual(afterNavigation.chat,afterTalk.chat);assert.equal(afterNavigation.beast.xp,afterTalk.beast.xp);
  assert.deepEqual(wrong,[]);assert.deepEqual(errors,[]);await fs.writeFile(out+'/report.json',JSON.stringify({passed:true,qbeast:snapshot.profile.id,seed:snapshot.profile.seed,verified,realNativeCore:true,noSimEarth:true,gameChatContractFixture:true,gameChatKeepsNativeMounted:true,sharedCageCareAndChat:true,beastBoyControlsHitNativeCore:true,realMobileDeckTap:true,standardGamepadApiFixtureHitsNativeCore:true,gameAudioUnlockVisible:true,noAutomaticModelCalls:true,noOwnerModelCalls:true,consoleErrors:errors},null,2));console.log('PASS: same QBEAST → actual current GBA, Beast Boy controls, guest talk contract, same Cage care/chat and no native remount');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
