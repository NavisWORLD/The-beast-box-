/** Public production proof: BOTH measured QBEASTs + native game + live guest inference. */
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const ORIGIN='https://www.beastboxcosmos.xyz';
const OUT=path.resolve('browser-evidence/umbralet-production-live');
const specs=[
 {name:'Umbralet',id:'bb-1e1759f3',selector:'#umbralet',ibm:'db4og3slf4us73c319h0',azure:'d7c48ad5-c442-11f1-ae67-70a8a5253f9c'}
],now=()=>new Date().toISOString();
(async()=>{
 await fs.mkdir(OUT,{recursive:true});
 const all={schema:'beastbox-umbralet-third-real-hardware-production-guest-and-gba-v1',origin:ORIGIN,started:now(),live_ibm_hardware_concurrent:false,azure_qvm_concurrent:false,original_song_sha256:'4410ed871310ae2ce4429c7f525b93105f1a5d4521213fe052f0ecefea9a7e47',original_12d_audio_packet_sha256:'84807db6e44e0bad5b494a6408ec7a0d8390f66399759e439b56f19ac8bb0e99',model:'RAWRPHOS_guest_actual_http_reply',results:[],passed:false};
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  for(const spec of specs){
   const dir=path.join(OUT,spec.name.toLowerCase());await fs.mkdir(dir,{recursive:true});
   const ctx=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,recordVideo:{dir:path.join(dir,'video'),size:{width:390,height:844}}});
   const page=await ctx.newPage(),report={name:spec.name,qbeast_id:spec.id,ibm_source_job:spec.ibm,azure_simulator_job:spec.azure,started:now(),network:[],talk:[],console_errors:[],pass:false};
   all.results.push(report);
   page.on('pageerror',error=>report.console_errors.push(String(error.message)));
   page.on('response',response=>{if(new URL(response.url()).pathname==='/api/guest')report.network.push({time:now(),status:response.status(),path:'/api/guest',method:response.request().method()});});
   try{
    let response=await page.goto(ORIGIN+'/spark/index.html',{waitUntil:'domcontentloaded',timeout:45000});assert.equal(response.status(),200);
    await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,null,{timeout:40000});
    await page.locator(spec.selector).click();
    await page.waitForFunction(id=>document.querySelector('#view')?.dataset.creatureId===id,spec.id,{timeout:30000});
    const first=await page.evaluate(()=>({id:JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.qbeast.profile.id,
      run:JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.genome.inputs.quantum_run}));
    assert.equal(first.id,spec.id);assert.equal(first.run,spec.ibm+':bell-xx');
    await page.locator('#azure-stimulus').click();
    await page.waitForFunction(job=>{try{return JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.qvmStimulus?.job_id===job}catch{return false}},spec.azure,{timeout:30000});
    report.saved_azure_stimulus_verified=true;
    await page.screenshot({path:path.join(dir,'spark.png'),fullPage:true});
    response=await page.goto(ORIGIN+'/sol-game',{waitUntil:'domcontentloaded',timeout:45000});assert.equal(response.status(),200);
    const shell=page.locator('[data-lost-cosmos-player-shell]'),send=shell.getByRole('button',{name:'SEND BEAST',exact:true});
    await send.waitFor({timeout:50000});
    await page.waitForFunction(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent?.trim()==='SEND BEAST');return b&&!b.disabled;},null,{timeout:45000});
    await send.click();await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:35000});
    await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
    const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));assert.ok(core,'Native Game Boy did not mount');
    await core.waitForFunction(()=>window.EJS_emulator?.gameManager?.getSaveFile(false)?.length===32768,null,{timeout:90000});
    report.native_save_bytes=await core.evaluate(()=>EJS_emulator.gameManager.getSaveFile(false).length);
    await shell.locator('[data-handheld-controls]').getByRole('button',{name:'A',exact:true}).tap();
    report.native_mounted=true;await core.locator('#game canvas').first().screenshot({path:path.join(dir,'native-cartridge.png')});
    const panel=page.locator('[data-spark-game-talk]');
    await panel.waitFor({timeout:35000});
    assert.equal(await panel.getAttribute('data-creature-id'),spec.id,'Wrong QBEAST in game dialogue panel');
    await panel.getByRole('button',{name:/TALK TO .*💬/}).click();
    // Optional grounded browser vision: numerical native pixels only, never pretend
    // the tiny model recognized game objects. Record denial/failure accurately.
    try{
     const check=panel.getByLabel('Include fresh native pixel signals with each model message (not screenshots or object recognition)');
     await check.check({timeout:6500});
     report.optical_consent=await check.isChecked();
    }catch(error){report.optical_consent=false;report.optical_error=String(error).slice(0,260);}
    if(report.optical_consent){
     try{
      await panel.getByRole('button',{name:/LOOK AT GAME/}).click();
      report.optical_status=(await panel.locator('p[role="status"]').allTextContents()).filter(Boolean).join(' | ').slice(0,600);
     }catch(error){report.optical_status='Native pixel observation failed: '+String(error).slice(0,160);}
    } else report.optical_status='Explicit native-frame opt-in unavailable. No visual evidence passed to the hosted model.';
    const sayings=[
      'Hello Umbralet. Your seed is from physical IBM circuits programmed with my original song analyzed into 12 COSMOS music channels. What do you actually know about that?',
      'I am pressing A in Lost COSMOS now. What can you genuinely observe in the native game, and what can you not see?',
      'Our uploaded song ran through 48 music windows before IBM hardware measured your seed. What do you want to explore with me?',
      'The song has early and late musical energy changes. How would you react to a new sound, and what is a scripted response versus an observation?',
      'This is our fifth recorded conversation turn together. What should we save to remember your first day inside Lost COSMOS?'
    ];
    for(const text of sayings){
     await panel.getByRole('textbox',{name:/Message to/}).fill(text);
     const pending=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/guest'&&response.request().method()==='POST',{timeout:75000});
     const begun=now();
     await panel.getByRole('button',{name:'SEND TO MODEL',exact:true}).click();
     const http=await pending;
     await page.waitForFunction(()=>!document.querySelector('[data-spark-game-talk] button[type="submit"]')?.textContent?.includes('ANSWERING'),null,{timeout:75000});
     const replies=await panel.locator('[aria-label="This Beast’s recent chat"] p').allTextContents();
     const ui=String(await panel.locator('form + p[role="status"]').textContent()).trim();
     const record={submitted_at:begun,received_at:now(),prompt:text,http_status:http.status(),recorded_reply:replies.at(-1)||'',ui_status:ui,game_running:await shell.getAttribute('data-running')};
     report.talk.push(record);
     assert.equal(http.status(),200);
     assert.ok(record.recorded_reply.startsWith(spec.name+':'),'Model did not reply in this Beast session');
     assert.ok(ui.includes('reply saved'),'Model response did not persist');
     assert.equal(record.game_running,'true');
    }
    await page.screenshot({path:path.join(dir,'live-game-conversation.png'),fullPage:true});
    report.pass=true;
   }catch(e){report.failure=String(e?.stack||e).slice(0,2400);throw e}
   finally{report.finished=now();await fs.writeFile(path.join(dir,'proof.json'),JSON.stringify(report,null,2)+'\n');const video=page.video();await ctx.close();if(video)await video.saveAs(path.join(dir,'live-game.webm'));}
  }
  all.passed=all.results.every(r=>r.pass);
 }catch(e){all.failure=String(e?.stack||e).slice(0,3000);throw e}
 finally{all.finished=now();await fs.writeFile(path.join(OUT,'summary.json'),JSON.stringify(all,null,2)+'\n');await browser.close();console.log('UMBRALET_PRODUCTION_PROOF'.replace(' ','')+' '+JSON.stringify({passed:all.passed,results:all.results.map(r=>({name:r.name,id:r.qbeast_id,turns:r.talk.length,game:r.native_mounted,pass:r.pass,failure:r.failure||null}))}));}
})().catch(e=>{console.error('UMBRALET_PRODUCTION_FAILURE',e?.stack||String(e));process.exitCode=1});
