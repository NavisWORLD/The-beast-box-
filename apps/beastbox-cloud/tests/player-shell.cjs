/* Real mounted cartridge continuity. Optional local mirror retains the public origin. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises');
const digest=bytes=>require('node:crypto').createHash('sha256').update(Buffer.from(bytes)).digest('hex');
const root=process.argv[2]||'http://127.0.0.1:3000',out=process.argv[3]||'/tmp/player-shell',mirror=process.argv[4];
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 if(mirror)await context.route('https://navisworld.github.io/**',async route=>{
  const url=new URL(route.request().url()),prefix='/Cosmic-synapse-the-living-universe-sim-engine-';
  assert.ok(url.pathname.startsWith(prefix));const response=await route.fetch({url:mirror+url.pathname.slice(prefix.length)+url.search});await route.fulfill({response});
 });
 await context.addInitScript(()=>{
  const buttons=Array.from({length:16},()=>({pressed:false,value:0}));window.__testPad={id:'Standard Gamepad API fixture',index:0,connected:true,mapping:'standard',timestamp:0,buttons,axes:[0,0]};
  Object.defineProperty(navigator,'getGamepads',{configurable:true,value:()=>[window.__testPad]});
  window.__shellMessages=[];window.addEventListener('message',event=>{if(event.origin==='https://navisworld.github.io'&&event.data?.type?.startsWith('sol-spark-'))window.__shellMessages.push(event.data);});
  window.__focusInputTrace=[];
  for(const type of ['focusin','focusout','keydown','keyup','beastbox:gba-input','beastbox:gba-release']){
   window.addEventListener(type,event=>{window.__focusInputTrace.push({type:event.type,target:event.target?.tagName,key:event.key,trusted:event.isTrusted,detail:event.detail});window.__focusInputTrace=window.__focusInputTrace.slice(-80);},true);
  }
 });
 const page=await context.newPage(),errors=[],romRequests=[];
 page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(request.url().includes('/rom/lost-cosmos.gba'))romRequests.push(request.url());});
 try{
  await page.goto(root+'/sol-game');
  const freshShell=page.locator('[data-lost-cosmos-player-shell]');
  await freshShell.getByRole('link',{name:'Choose your Spark Beast',exact:true}).waitFor({timeout:5000});
  assert.equal(await freshShell.getByRole('button',{name:'SEND BEAST',exact:true}).isDisabled(),true,'fresh visitors choose their Beast before sending it');
  assert.equal(await page.locator('iframe').count(),0,'choosing a Beast does not boot another cartridge');
  await freshShell.getByRole('link',{name:'Choose your Spark Beast',exact:true}).click();await page.waitForURL(root+'/spark/index.html');
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
  await page.locator('#generate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Spawned'));
  const qbeast=await page.evaluate(()=>JSON.parse(JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1')).text));
  await page.goto(root+'/sol-game');
  // RED: current main has no dedicated shell/fullscreen action.
  const shell=page.locator('[data-lost-cosmos-player-shell]');
  await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).waitFor({timeout:5000});
  let releaseLoader;const loaderGate=new Promise(resolve=>{releaseLoader=resolve;});
  const loaderPattern='**/arcade/sol-spark-gate/handheld.mjs?**';
  await context.route(loaderPattern,async route=>{await loaderGate;await route.fallback();});
  await shell.getByRole('button',{name:'SEND BEAST',exact:true}).click();
  await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:60000});
  const releasePattern='**/arcade/lost-cosmos/rom/release.json';
  await context.route(releasePattern,route=>route.fulfill({status:503,body:'forced startup failure fixture'}));
  await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  releaseLoader();
  await shell.getByRole('status').filter({hasText:'Lost COSMOS could not start'}).waitFor();
  await context.unroute(loaderPattern);
  await context.unroute(releasePattern);
  await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
  const iframe=await shell.locator('iframe').elementHandle();
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));
  assert.ok(core,'one native cartridge is mounted');
  assert.equal(await core.evaluate(()=>!!EJS_emulator.elements.menuToggle),true,'touch fixture exposes the actual emulator menu toggle');
  assert.equal(await core.evaluate(()=>['menu','menuToggle'].every(key=>!EJS_emulator.elements[key]||getComputedStyle(EJS_emulator.elements[key]).display==='none')),true,'embedded cartridge leaves controls and fullscreen ownership to the player shell');
  await core.evaluate(()=>{window.__originalCore=EJS_emulator;const gm=EJS_emulator.gameManager,sim=gm.simulateInput.bind(gm);window.__shellInputs=[];gm.simulateInput=(p,i,v)=>{window.__shellInputs.push([p,i,v]);return sim(p,i,v);};});
  const identity=await core.evaluate(()=>Array.from(EJS_emulator.gameManager.getSaveFile(false).subarray(24704,24832)));
  const continuity=async label=>{
   assert.equal(await shell.locator('iframe').evaluate((node,original)=>node===original,iframe),true,label+' keeps the iframe node');
   assert.equal(page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html')),core,label+' keeps the native frame');
   assert.equal(await core.evaluate(()=>EJS_emulator===window.__originalCore),true,label+' keeps the native emulator');
   assert.deepEqual(await core.evaluate(()=>Array.from(EJS_emulator.gameManager.getSaveFile(false).subarray(24704,24832))),identity,label+' keeps native identity/art');
   assert.deepEqual(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.qbeast),qbeast,label+' keeps QBEAST');
  };
  const control=(name)=>shell.locator('[data-handheld-controls]').getByRole('button',{name,exact:true});
  const touch=await context.newCDPSession(page);
  const press=async name=>{const b=await control(name).boundingBox();assert.ok(b);await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:b.x+b.width/2,y:b.y+b.height/2,id:1}]});await page.waitForTimeout(150);await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await page.waitForTimeout(650);};
  // The real native title flow creates its own roster; no invented game progress.
  await page.waitForTimeout(1800);await press('A');await page.waitForTimeout(900);await press('Start');
  await core.waitForFunction(()=>{const gm=EJS_emulator.gameManager;gm.saveSaveFiles();const bytes=gm.getSaveFile(false);return bytes&&String.fromCharCode(...bytes.subarray(1024,1028))==='LCR1';},null,{timeout:90000});
  const nativeProgress=await core.evaluate(()=>Array.from(EJS_emulator.gameManager.getSaveFile(false).subarray(1024,1276)));
  await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).click();
  await page.waitForFunction(()=>['fullscreen','immersive'].includes(document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode));
  const mode=await shell.getAttribute('data-player-mode');
  assert.equal(await page.evaluate(()=>!!document.fullscreenElement),mode==='fullscreen','mode reports actual Fullscreen API reality');
  assert.equal(await page.evaluate(()=>!document.fullscreenElement||document.fullscreenElement.matches('[data-lost-cosmos-player-shell]')),true,'game AND controls belong to the fullscreen element');
  await continuity('expanded');
  // Fullscreen owns both native pixels and the real model chat. Do not hide
  // the composer behind the emulator or unmount it when docking the player.
  await shell.getByRole('button',{name:/^TALK TO /}).click();
  const gameComposer=shell.locator('textarea');
  const draft='Same Beast, same story through the Game Boy.';
  await gameComposer.fill(draft);
  await gameComposer.scrollIntoViewIfNeeded();
  assert.equal(await gameComposer.evaluate(node=>{const rect=node.getBoundingClientRect();return rect.top>=0&&rect.bottom<=innerHeight+2;}),true,'fullscreen conversation composer is viewport-reachable');
  await shell.getByRole('button',{name:'MINIMIZE',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='minimized');
  await continuity('chat minimized');
  await shell.getByRole('button',{name:'RESTORE GAME',exact:true}).click();
  await continuity('chat restored');
  assert.equal(await gameComposer.inputValue(),draft,'minimize/restore keeps the same unsent message and chat instance');
  await shell.getByRole('button',{name:'CLOSE TALK',exact:true}).click();
  const resize=async(width,height)=>{
   if(await page.evaluate(()=>!!document.fullscreenElement))await page.evaluate(()=>document.exitFullscreen());
   else if(await shell.getAttribute('data-player-mode')==='immersive')await shell.getByRole('button',{name:'RETURN',exact:true}).click();
   await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='normal');
   await page.setViewportSize({width,height});
  };
  const widths=[];
  for(const [width,height] of [[320,720],[375,812],[390,844],[430,932],[1440,900]]){
   await resize(width,height);
   await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).click();await page.waitForFunction(()=>document.fullscreenElement?.matches('[data-lost-cosmos-player-shell]'));
   const layout=await shell.evaluate(node=>{
    const box=node.getBoundingClientRect(),controls=[...node.querySelectorAll('[data-handheld-controls] button')].map(button=>{const r=button.getBoundingClientRect();return {label:button.getAttribute('aria-label'),x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};});
    return {width:document.documentElement.clientWidth,overflow:document.documentElement.scrollWidth,shell:{x:box.x,y:box.y,right:box.right,bottom:box.bottom},controls};
   });
   assert.ok(layout.overflow<=layout.width+1,width+' has no horizontal overflow');
   for(const button of layout.controls){assert.ok(button.x>=0&&button.right<=width+1&&button.y>=0&&button.bottom<=height+1,width+' '+button.label+' stays reachable');assert.ok(button.width>=44&&button.height>=44,width+' '+button.label+' touch target');}
   await continuity(width+'px');await page.screenshot({path:out+'/expanded-'+width+'.png'});widths.push(width);
   await shell.getByRole('button',{name:'MINIMIZE',exact:true}).click();
   await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='minimized');
   const dockClear=await page.evaluate(()=>{
    const player=document.querySelector('[data-lost-cosmos-player-shell]').getBoundingClientRect(),support=document.querySelector('.cosmic-support-launcher')?.getBoundingClientRect();
    return !support||player.right<=support.left||player.left>=support.right||player.bottom<=support.top||player.top>=support.bottom;
   });
   assert.equal(dockClear,true,width+'px game dock does not cover the existing support Beast');
   if(width===320)await page.screenshot({path:out+'/minimized-320.png'});
   await shell.getByRole('button',{name:'RESTORE GAME',exact:true}).click();await continuity(width+'px minimized/restore');
  }
  await resize(390,844);await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).click();await page.waitForFunction(()=>document.fullscreenElement?.matches('[data-lost-cosmos-player-shell]'));
  for(const [name,index] of [['Up',4],['Down',5],['Left',6],['Right',7],['A',8],['B',0],['Start',3],['Select',2]]){
   const before=await core.evaluate(()=>window.__shellInputs.length);await control(name).tap();await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);
   assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+2),before),[[0,index,1],[0,index,0]],name+' expanded touch reaches native core');
   assert.equal(await page.evaluate(name=>window.__shellMessages.filter(event=>event.type==='sol-spark-input-ack'&&event.button===name.toLowerCase()).at(-1)?.applied,name),true,name+' native input acknowledged');
  }
  await page.keyboard.press('Escape');
  let escapeWorked=false;try{await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='normal',null,{timeout:2500});escapeWorked=true;}catch{
   await page.evaluate(()=>document.exitFullscreen());await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='normal');
  }
  await continuity('browser exit');
  await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).click();await page.waitForFunction(()=>document.fullscreenElement?.matches('[data-lost-cosmos-player-shell]'));
  await shell.getByRole('button',{name:'MINIMIZE',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='minimized');await continuity('minimized');
  await shell.getByRole('button',{name:'RESTORE GAME',exact:true}).click();await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='normal');await continuity('restored');
  // Real keyboard events drive the existing normalized bridge.
  await page.locator('[data-lost-cosmos-player-shell] strong').click();
  let before=await core.evaluate(()=>window.__shellInputs.length);await page.keyboard.press('ArrowRight');await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);
  assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+2),before),[[0,7,1],[0,7,0]],'keyboard reaches native core after restore');
  before=await core.evaluate(()=>window.__shellInputs.length);await page.keyboard.down('z');await control('A').tap();await page.keyboard.up('z');await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);
  assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n),before),[[0,8,1],[0,8,0]],'touch release never cancels a keyboard-held A');
  await shell.getByRole('button',{name:/^TALK TO /}).click();
  // Focus a real, keyboard-accessible player target. A nonfocusable <strong>
  // does not reliably reclaim focus after using Talk in all browser engines.
  await shell.focus();
  assert.equal(await shell.evaluate(node=>document.activeElement===node),true,'Game Boy can reclaim keyboard focus from chat controls');
  before=await core.evaluate(()=>window.__shellInputs.length);
  await page.keyboard.down('ArrowLeft');
  await core.waitForFunction(n=>window.__shellInputs.length>=n+1,before);
  assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+1),before),[[0,6,1]],'the held Left press reaches native core before focus transfer');
  await shell.locator('textarea').focus();
  // Release must reach the native core as soon as an editor takes focus.
  // Never depend on an eventual keyup being delivered to the original target.
  try{await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);}catch(error){
   console.log('FOCUS_RELEASE_DIAGNOSTIC '+JSON.stringify({page:await page.evaluate(()=>({active:document.activeElement?.outerHTML?.slice(0,300),hasFocus:document.hasFocus(),trace:window.__focusInputTrace})),native:await core.evaluate(()=>window.__shellInputs.slice(-16))}));throw error;
  }
  await page.keyboard.up('ArrowLeft');
  assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n),before),[[0,6,1],[0,6,0]],'focus transfer releases held native Left exactly once, even after keyboard up');
  await shell.getByRole('button',{name:'CLOSE TALK',exact:true}).click();
  // A controlled standard Gamepad API fixture; this is not a physical-controller receipt.
  before=await core.evaluate(()=>window.__shellInputs.length);await page.evaluate(()=>{window.__testPad.buttons[0]={pressed:true,value:1};});await core.waitForFunction(n=>window.__shellInputs.length>n,before);
  await page.evaluate(()=>{window.__testPad.buttons[0]={pressed:false,value:0};});await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);
  assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+2),before),[[0,8,1],[0,8,0]],'standard Gamepad mapping reaches the same native core');
  // Pointer capture, leaving the control, cancellation and orientation all release the native key.
  const a=control('A'),box=await a.boundingBox();
  before=await core.evaluate(()=>window.__shellInputs.length);await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(1,1);await page.mouse.up();await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);
  assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+2),before),[[0,8,1],[0,8,0]],'leaving captured button releases it once');
  for(const event of ['pointercancel','orientationchange']){
   before=await core.evaluate(()=>window.__shellInputs.length);await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await core.waitForFunction(n=>window.__shellInputs.length>n,before);
   if(event==='pointercancel')await a.dispatchEvent(event,{pointerId:1});else await page.evaluate(()=>window.dispatchEvent(new Event('orientationchange')));
   await page.mouse.up();await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+2),before),[[0,8,1],[0,8,0]],event+' releases the native button once');
  }
  // Deliberately rejected API boundary proves the actual CSS fallback remains playable.
  const oldScroll=await page.evaluate(()=>({body:document.body.style.overflow,html:document.documentElement.style.overflow}));
  await shell.evaluate(node=>{node.requestFullscreen=()=>Promise.reject(new Error('fullscreen unavailable test fixture'));});
  await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).click();await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='immersive');
  assert.equal(await page.evaluate(()=>document.fullscreenElement),null);assert.equal(await page.evaluate(()=>document.body.style.overflow),'hidden');
  before=await core.evaluate(()=>window.__shellInputs.length);await control('B').tap();await core.waitForFunction(n=>window.__shellInputs.length>=n+2,before);assert.deepEqual(await core.evaluate(n=>window.__shellInputs.slice(n,n+2),before),[[0,0,1],[0,0,0]],'immersive touch controls reach native core');
  await page.screenshot({path:out+'/immersive-390.png'});await shell.getByRole('button',{name:'MINIMIZE',exact:true}).click();await continuity('fallback minimized');
  assert.deepEqual(await page.evaluate(()=>({body:document.body.style.overflow,html:document.documentElement.style.overflow})),oldScroll,'fallback releases page scroll lock');
  await shell.getByRole('button',{name:'RESTORE GAME',exact:true}).click();await shell.evaluate(node=>{delete node.requestFullscreen;});await continuity('fallback restored');
  // Keep the exact native SRAM stable only for this byte comparison, then resume gameplay.
  const battery=await core.evaluate(()=>{EJS_emulator.pause();const gm=EJS_emulator.gameManager;gm.saveSaveFiles();return Array.from(gm.getSaveFile(false));});
  await shell.getByRole('button',{name:'FULL SCREEN',exact:true}).click();await shell.getByRole('button',{name:'MINIMIZE',exact:true}).click();await shell.getByRole('button',{name:'RESTORE GAME',exact:true}).click();
  assert.equal(digest(await core.evaluate(()=>{const gm=EJS_emulator.gameManager;gm.saveSaveFiles();return Array.from(gm.getSaveFile(false));})),digest(battery),'layout transitions preserve every native battery byte at a fixed CPU checkpoint');
  await shell.getByRole('button',{name:'SAVE JOURNEY',exact:true}).click();await shell.getByRole('status').filter({hasText:'journey saved to the same Beast'}).waitFor({timeout:15000});
  const returned=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));
  assert.equal(returned.beast.localGrowth.status,'unsigned-local');assert.deepEqual(returned.beast.qbeast,qbeast);
  assert.equal(digest(Buffer.from(returned.beast.game.native_save,'base64')),digest(battery),'same Beast receives actual native battery after resize/minimize/restore');
  const applied=returned.beast.localGrowth.applied.length;
  await shell.getByRole('button',{name:'SAVE JOURNEY',exact:true}).click();await shell.getByRole('status').filter({hasText:'journey saved to the same Beast'}).waitFor();
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.localGrowth.applied.length),applied,'identical native return is replay protected');
  await core.evaluate(()=>EJS_emulator.play());
  // Client-side browsing must not remount the persistent dock's native iframe.
  await shell.getByRole('link',{name:'BEAST BOX ↗',exact:true}).click();await page.waitForURL(root+'/beast-cage');await continuity('browse Beast Box');
  await page.getByRole('link',{name:'Home',exact:true}).click();await page.waitForURL(root+'/');await continuity('browse homepage');
  for(const width of [320,375,390,430]){
   await page.setViewportSize({width,height:844});
   const clear=await page.evaluate(()=>{const node=document.querySelector('[data-lost-cosmos-player-shell]'),game=node.getBoundingClientRect(),support=document.querySelector('.cosmic-support-launcher').getBoundingClientRect();return {pass:game.right<=support.left||game.left>=support.right||game.bottom<=support.top||game.top>=support.bottom,game:game.toJSON(),support:support.toJSON(),bottom:getComputedStyle(node).bottom,viewport:innerWidth};});
   if(width===320)await page.screenshot({path:out+'/minimized-home-320.png'});
   assert.equal(clear.pass,true,width+'px minimized cartridge keeps the existing support Beast reachable: '+JSON.stringify(clear));
  }
  await page.setViewportSize({width:390,height:844});
  await shell.getByRole('button',{name:'RESTORE GAME',exact:true}).click();await continuity('restore while browsing');
  await page.screenshot({path:out+'/restored-390.png'});
  assert.equal(romRequests.length,1,'one verified ROM fetch across every transition');assert.deepEqual(errors,[]);
  await fs.writeFile(out+'/report.json',JSON.stringify({passed:true,mode,escapeWorked,widths,qbeast_id:qbeast.profile.id,sameIframe:true,sameNativeCore:true,sameNativeIdentity:true,allEightExpandedTouchControls:true,startupFailureVisible:true,nativeInputAcknowledgement:true,keyboard:true,standardGamepadFixture:true,pointerRelease:true,overlappingInputSources:true,keyboardFocusRelease:true,immersiveFallback:true,scrollLockRestored:true,exactBatteryAtFixedCpuCheckpoint:true,nativeReturn:true,replayProtection:true,signedQbeastUnchanged:true,clientNavigation:true,romRequests:romRequests.length,consoleErrors:errors},null,2));
  console.log('PASS: mounted native cartridge survives fullscreen → minimize → restore with all eight controls');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
