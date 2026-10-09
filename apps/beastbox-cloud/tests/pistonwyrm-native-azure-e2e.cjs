/** Real native emulator and real one-shot Azure QVM stimulus; no mock model or cartridge. */
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const base=process.argv[2]||'http://127.0.0.1:3000',dir=path.resolve(process.argv[3]||'browser-evidence/pistonwyrm-integration');
const job='71cf7c02-c435-11f1-ae67-7ced8d52b5e1',id='bb-d41e5bd4';
(async()=>{
 await fs.mkdir(dir,{recursive:true});
 const result={schema:'beastbox-pistonwyrm-native-qvm-e2e-v1',origin:base,identity:id,azure_job:job,source:'RECORDED_SIMULATOR',tests:[],pageerrors:[],success:false};
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const ctx=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,recordVideo:{dir:path.join(dir,'video'),size:{width:390,height:844}}});
 const page=await ctx.newPage();page.on('pageerror',e=>result.pageerrors.push(String(e.message)));
 try{
  let response=await page.goto(base+'/spark/index.html');assert.equal(response.status(),200);
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,null,{timeout:40000});
  await page.locator('#pistonwyrm').click();
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId==='bb-d41e5bd4',null,{timeout:30000});
  result.tests.push('Real Spark page generated pinned new IBM Fez Pistonwyrm identity');
  await page.locator('#azure-stimulus').click();
  await page.waitForFunction(j=>{try{return JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.qvmStimulus?.job_id===j}catch{return false}},job,{timeout:30000});
  const first=await page.evaluate(()=>{const s=JSON.parse(localStorage.getItem('beastbox-companion-session-v1'));return {qbeast:s.beast.qbeast.profile.id,marker:s.beast.qvmStimulus,behavior:s.beast.behavior}});
  assert.equal(first.qbeast,id);assert.equal(first.marker.job_id,job);
  result.tests.push('True 512-shot recorded Azure QVM stimulus entered same creature behavior once');
  await page.locator('#azure-stimulus').click();
  await page.getByText(/Already experienced by/i).first().waitFor({timeout:10000});
  const after=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.behavior);
  assert.equal(after.tick,first.behavior.tick,'Duplicate QVM stimulus changed the behavior tick');
  result.one_shot_behavior_tick=after.tick;
  result.tests.push('Azure duplicate signal refused additional behavior advancement');
  await page.screenshot({path:path.join(dir,'real-pistonwyrm-on-spark.png'),fullPage:true});
  // The native emulator is hosted from the separate Cosmic Synapse GitHub Pages
  // repository. Refuse to claim integration before its immutable recorded-run
  // admission table is actually published. Do not bypass verification.
  const cartridgeSource='https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/spark-beasts/data/ibm-pistonwyrm-20261009-supplement.json';
  let nativeSourceReady=false;
  for(let attempt=0;attempt<60;attempt++){
   try{
    const fetched=await page.request.get(cartridgeSource,{timeout:12000});
    if(fetched.ok()){
     const data=await fetched.json();
     if(data.job_id==='db4n37g4qg6s73c2de00'&&data.counts_digest_sha256==='d084218f57511e33070fbbf82a055d74bf77636b6c07eaa82bd6f1d1208a18d9'){
      nativeSourceReady=true;break;
     }
    }
   }catch{/* deployment propagation can lag */}
   await page.waitForTimeout(5000);
  }
  assert.ok(nativeSourceReady,'Real GitHub Pages native cartridge table has not deployed verified Pistonwyrm IBM source');
  result.tests.push('Actual GitHub Pages native cartridge source table recognizes pinned IBM digest');
  response=await page.goto(base+'/sol-game');assert.equal(response.status(),200);
  const shell=page.locator('[data-lost-cosmos-player-shell]');
  const send=shell.getByRole('button',{name:'SEND BEAST',exact:true});
  await send.waitFor({timeout:45000});
  await page.waitForFunction(()=>{let b=[...document.querySelectorAll('button')].find(x=>x.textContent?.trim()==='SEND BEAST');return b&&!b.disabled;},null,{timeout:30000});
  await send.click();
  try{await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:30000});}
  catch(e){
   const statuses=await shell.getByRole('status').allTextContents();
   throw Error('Native cartridge denied the measured dragon: '+JSON.stringify({statuses,sourceReady:nativeSourceReady})+' '+String(e));
  }
  await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
  const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));assert.ok(core,'real GBA not mounted');
  await core.waitForFunction(()=>window.EJS_emulator?.gameManager?.getSaveFile(false)?.length===32768,null,{timeout:90000});
  await core.evaluate(()=>{const gm=EJS_emulator.gameManager,old=gm.simulateInput.bind(gm);window.__pistonInput=[];gm.simulateInput=(...a)=>{window.__pistonInput.push(a);return old(...a);};});
  const pad=shell.locator('[data-handheld-controls]');
  await pad.getByRole('button',{name:'A',exact:true}).tap();
  await pad.getByRole('button',{name:'Start',exact:true}).tap();
  const native=await core.evaluate(()=>({save:EJS_emulator.gameManager.getSaveFile(false).length,input:window.__pistonInput}));
  assert.equal(native.save,32768);assert.deepEqual(native.input.slice(0,2),[[0,8,1],[0,8,0]]);
  result.native=native;result.tests.push('Real Lost COSMOS emulator mounted same Pistonwyrm; 32,768 byte save and actual A/Start input');
  await core.locator('#game canvas').first().screenshot({path:path.join(dir,'real-pistonwyrm-native-game.png')});
  result.success=true;
 }catch(e){result.failure=String(e?.stack||e).slice(0,2600);throw e}
 finally{
  result.finished=new Date().toISOString();
  await fs.writeFile(path.join(dir,'proof.json'),JSON.stringify(result,null,2)+'\n');
  const video=page.video();await ctx.close();if(video)await video.saveAs(path.join(dir,'real-gameplay.webm'));await browser.close();
  console.log('PISTONWYRM_NATIVE_GAME_PROOF '+JSON.stringify({success:result.success,tests:result.tests,game:result.native||null,failure:result.failure||null}));
 }
})().catch(e=>{console.error('PISTONWYRM_GAME_FAILED',e?.stack||String(e));process.exitCode=1});
