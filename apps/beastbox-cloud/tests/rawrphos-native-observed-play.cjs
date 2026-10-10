/* Genuine browser-mounted Lost COSMOS observation/action traces for RAWRPHØS.
 * Runs actual original Game Boy native ROM via EmulatorJS on CI runner.
 * A deterministic SCRIPTED exploration teacher presses legal keys. Its chosen
 * actions are demonstrations, NOT ground-truth navigation or model outputs.
 * Every accepted observation is actually read from the native framebuffer.
 * No raw screenshot, user chat/memory, passwords or emulator SRAM leave runner.
 */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs/promises'),crypto=require('node:crypto');
const root=process.argv[2]||'http://127.0.0.1:3000';
const mirror=process.argv[3]||'http://127.0.0.1:8765';
const output=process.argv[4]||'/tmp/native-observed-guidance';
const sha=v=>crypto.createHash('sha256').update(v).digest('hex');
const actions=['RIGHT','UP','LEFT','DOWN','A','B','RIGHT','RIGHT','UP','LEFT','A','DOWN','RIGHT','B'];
const nativeIndex={UP:4,DOWN:5,LEFT:6,RIGHT:7,A:8,B:0};
const safe=o=>o&&o.status==='observed'&&o.source==='native-emulator-display'
  &&['red','green','blue','mixed'].includes(o.dominant)
  &&['brightness','contrast','frameChange'].every(k=>Number.isInteger(o[k])&&o[k]>=0&&o[k]<=100);
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.BEAST_BROWSER_EXECUTABLE?{executablePath:process.env.BEAST_BROWSER_EXECUTABLE}:{}),
 args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const context=await browser.newContext({viewport:{width:430,height:932},isMobile:true,hasTouch:true,recordVideo:{dir:output,size:{width:430,height:932}}});
 // Mirrors trusted canonical public origin but records the exact native source ref.
 await context.route('https://navisworld.github.io/**',async route=>{
  const target=new URL(route.request().url()),prefix='/Cosmic-synapse-the-living-universe-sim-engine-';
  if(!target.pathname.startsWith(prefix))return route.abort();
  const upstream=await route.fetch({url:mirror+target.pathname.slice(prefix.length)+target.search});
  await route.fulfill({response:upstream});
 });
 const page=await context.newPage(),errors=[],episodes=[],raw=[];
 page.on('pageerror',e=>errors.push(String(e.message).slice(0,200)));
 try{
  await page.goto(root+'/spark/index.html',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,{timeout:45000});
  await page.locator('#lumenwisp').click();
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId==='bb-983f386b',null,{timeout:45000});
  const signed=await page.evaluate(()=>{
   const entry=JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1'));
   const q=JSON.parse(entry.text);return {id:q.profile.id,seed:q.genome?.seed||'',text_sha256:null};
  });
  assert.equal(signed.id,'bb-983f386b','Exact verified new IBM Lumenwisp was not selected');
  await page.goto(root+'/sol-game',{waitUntil:'domcontentloaded'});
  const shell=page.locator('[data-lost-cosmos-player-shell]');
  await shell.getByRole('button',{name:'SEND BEAST',exact:true}).click();
  await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:60000});
  await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));
  assert.ok(core,'Original handheld.html iframe must actually mount');
  await core.waitForFunction(()=>!!window.EJS_emulator?.gameManager?.simulateInput,null,{timeout:90000});
  await core.evaluate(()=>{
   const gm=window.EJS_emulator.gameManager,old=gm.simulateInput.bind(gm);
   window.__nativeDecisionTrace=[];
   gm.simulateInput=(player,index,value)=>{window.__nativeDecisionTrace.push([player,index,value]);return old(player,index,value);};
  });
  async function input(button,hold=145){
   assert.ok(button in nativeIndex);
   const before=await core.evaluate(()=>window.__nativeDecisionTrace.length);
   await page.evaluate(button=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',
      {detail:{button:button.toLowerCase(),down:true,source:'agent'}})),button);
   await delay(hold);
   await page.evaluate(button=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',
      {detail:{button:button.toLowerCase(),down:false,source:'agent'}})),button);
   await core.waitForFunction(n=>window.__nativeDecisionTrace.length>=n+2,before,{timeout:6000});
   const trace=await core.evaluate(n=>window.__nativeDecisionTrace.slice(n),before);
   assert.deepEqual(trace.slice(0,2),[[0,nativeIndex[button],1],[0,nativeIndex[button],0]],'Native controller did not ACK real press/release: '+button);
   return sha(JSON.stringify(trace));
  }
  async function optics(){
   const obs=await core.evaluate(async()=>{
    const {observeNativePixels}=await import('./native-observation.mjs');
    return await observeNativePixels(document);
   });
   if(!safe(obs))throw Error('Actual native pixels not readable; no fabricated observation or training rows');
   return obs;
  }
  async function saveDigest(){
   return core.evaluate(()=>{
    const data=window.EJS_emulator?.gameManager?.getSaveFile?.(false);
    if(!data||data.length<256)return null;
    // Never export save bytes: evidence keeps only SHA-256 via WebCrypto.
    return crypto.subtle.digest('SHA-256',new Uint8Array(data)).then(arr=>
      Array.from(new Uint8Array(arr),v=>v.toString(16).padStart(2,'0')).join(''));
   });
  }
  // A real cartridge may need its own title/start sequence before gameplay.
  await delay(1600);await input('A');await delay(650);
  await page.evaluate(()=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button:'start',down:true,source:'agent'}})));
  await delay(150);
  await page.evaluate(()=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button:'start',down:false,source:'agent'}})));
  await delay(1700);
  const init=await optics();
  assert.ok(init,'Native optical observations must succeed before writing any dataset');
  for(let episode=0;episode<4;episode++){
   const entries=[];
   const beginning=await saveDigest();
   for(let i=0;i<actions.length;i++){
    const policyAction=actions[(i+episode*3)%actions.length];
    const before=await optics();
    const native_ack_digest=await input(policyAction);
    await delay(260);
    const after=await optics();
    entries.push({schema:'beastbox-real-native-emulator-action-v1',
      parent:'Lumenwisp',qbeast_id:signed.id,episode,step:i,
      before,action:policyAction,after,native_ack_digest,
      teacher:'SCRIPTED_ACTION_SEQUENCE_NOT_HUMAN_NOT_MODEL',
      reward_proxy:Math.abs(after.brightness-before.brightness)+Math.abs(after.contrast-before.contrast)+Math.abs(after.frameChange-before.frameChange),
      reward_is_not_native_progress:true});
   }
   const after=await saveDigest();
   episodes.push({episode,beast_id:signed.id,rows:entries.length,save_before_sha256:beginning,save_after_sha256:after,
     raw_sram_not_exported:true});
   raw.push(...entries);
  }
  assert.equal(raw.length,56,'Expected 56 genuine native observation/action pairs');
  assert.ok(raw.every(v=>safe(v.before)&&safe(v.after)&&v.qbeast_id===signed.id&&/^[a-f0-9]{64}$/.test(v.native_ack_digest)));
  assert.ok(new Set(raw.map(v=>JSON.stringify(v.before))).size>=3,'Game observations insufficiently varied; refuse training');
  const jsonl=raw.map(row=>JSON.stringify(row)).join('\n')+'\n';
  await fs.writeFile(output+'/native-observation-actions.jsonl',jsonl);
  const manifest={schema:'beastbox-observed-native-play-v1',source_class:'ORIGINAL_EMULATOR_NATIVE_PIXEL_OBSERVATIONS',
   qbeast_id:signed.id,alias:'Lumenwisp',sampling:'actual original native emulator 32x24 optical numeric features',
   controller:'real native simulatedInput ACK, scripted teacher, no model decisions',
   episodes,events:raw.length,jsonl_sha256:sha(jsonl),
   dataset_has_human_labels:false,goal_reward_observed:false,
   training_is_behavioral_cloning_of_scripted_controller:true,
   native_game_progress_proven:false,
   errors,source_native_ref:process.env.NATIVE_GAME_HEAD||'native main at workflow checkout',
   source_web_ref:process.env.WEB_APP_HEAD||'current PR checkout'};
  await fs.writeFile(output+'/native-evidence-manifest.json',JSON.stringify(manifest,null,2)+'\n');
  assert.equal(errors.length,0,'Browser Javascript error(s): '+errors.join(' | '));
  console.log('ACTUAL_NATIVE_PLAY_OBSERVATIONS='+JSON.stringify({
    qbeast_id:manifest.qbeast_id,episodes:episodes.length,verified_pairs:raw.length,source_sha256:sha(jsonl),
    distinct_pre_frames:new Set(raw.map(v=>JSON.stringify(v.before))).size,progress_proven:false}));
 }catch(e){
  await fs.writeFile(output+'/failed-native-observation.json',JSON.stringify({
   error_type:e?.name||'Error',message:String(e?.message||e).slice(0,500),errors,no_fake_data_created:true},null,2)+'\n');
  console.error(e);process.exitCode=1;
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
