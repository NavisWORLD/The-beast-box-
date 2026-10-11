/* EXPERIMENT 009: actual original Lost COSMOS native cartridge, not a mock.
 * Compare WAIT / constant RIGHT / deterministic RANDOM / scripted teacher /
 * frozen RAWRPHOS / trained Zeref RAWRPHOS from fresh independent episodes.
 * Every recorded optical before/after is from the actual GBA emulator.
 * Screen changes are NOT earned progress or semantic vision.
 */
'use strict';
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const {SHA,ACT,parseModel,optic,teacher,seededRandom,opticsSignature,summarizeArm}=require('../../../scripts/zeref_native_rollout_policy_005.cjs');
const {decode,change}=require('../../../scripts/zeref_native_progress_008.cjs');
const root=process.argv[2]||'http://127.0.0.1:3000';
const mirror=process.argv[3]||'http://127.0.0.1:8765';
const out=process.argv[4]||'/tmp/zeref-real-policy-arena-009';
const inference='http://127.0.0.1:8778';
const QBEAST='bb-deada969', GENOME='8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed';
const JOB='db4q484vf2bc73cuuuag';
const MODEL_HASHES={original:'4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5',candidate:'37ca3f8fc9cdc0e78175508fc816ed02d5a12da1f3b106505715b7366fde5a48'};
const SMOKE=process.env.ZEREF_009_SAVE_SMOKE==='1';
const POLICIES=SMOKE?['WAIT','RIGHT']:['WAIT','RIGHT','RANDOM','SCRIPT','original','candidate'];
const EPISODES=SMOKE?1:3, STEPS=SMOKE?8:20;
const INPUT={UP:4,DOWN:5,LEFT:6,RIGHT:7,A:8,B:0,START:3};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const hex=x=>SHA(x);
const output=(path,val)=>fs.writeFile(out+'/'+path,JSON.stringify(val,null,2)+'\n');
const policyOrder=(()=>{
 const rng=seededRandom(20261011),a=[];
 for(let ep=0;ep<EPISODES;ep++){
  const q=[...POLICIES];
  for(let i=q.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[q[i],q[j]]=[q[j],q[i]];}
  for(const p of q)a.push({policy:p,episode:ep});
 }
 return a;
})();
async function infer(kind,observation,episode,step){
 const response=await fetch(inference+'/infer',{method:'POST',
  headers:{'Content-Type':'application/json'},
  body:JSON.stringify({model:kind,observation,qbeast_id:QBEAST,step:episode*STEPS+step}),
  signal:AbortSignal.timeout(30000)});
 const payload=await response.json();
 if(!response.ok)throw Error('Pinned model endpoint rejected: '+JSON.stringify(payload).slice(0,200));
 assert.equal(payload.checkpoint_sha256,MODEL_HASHES[kind]);
 assert.equal(payload.response_source,'ACTUAL_CPU_MODEL_INFERENCE');
 return payload;
}
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const all=[],data={WAIT:[],RIGHT:[],RANDOM:[],SCRIPT:[],original:[],candidate:[]};
 const errors=[];
 try{
  const health=await (await fetch(inference+'/health',{signal:AbortSignal.timeout(10000)})).json();
  assert.equal(health.ready,true,'Both real model weights must load before native trial');
  assert.deepEqual(health.models,MODEL_HASHES,'Original and candidate weights do not match pinned training receipt');
  await output('preregistered-controls.json',{schema:'beastbox-zeref-native-policy-arena-009',qbeast_id:QBEAST,
   original_ibm_job:JOB,original_ibm_genome_seed:GENOME,model_checkpoints:MODEL_HASHES,
   actual_committed_sram_is_observed_only_if_checksum_valid:true,
   source_native_ref:process.env.NATIVE_GAME_HEAD||null,source_web_ref:process.env.WEB_APP_HEAD||null,
   policy_order:policyOrder,episodes_each:EPISODES,steps_each:STEPS,
   start:'fresh browser context per episode, exact Zeref selection, same native cartridge initial A+START sequence',
   progress_metrics_observable:'committed game save only; null if never saved',
   warning:'Optical novelty / framebuffer changes are not navigation rewards, area exploration, dialogue or advancement.'});
  let runIndex=0;
  for(const {policy,episode} of policyOrder){
   runIndex++;
   const captureVideo=episode===0;
   const context=await browser.newContext({
    viewport:{width:430,height:932},isMobile:true,hasTouch:true,
    ...(captureVideo?{recordVideo:{dir:out,size:{width:430,height:932}}}:{})
   });
   await context.route('https://navisworld.github.io/**',async route=>{
    const upstream=new URL(route.request().url()),prefix='/Cosmic-synapse-the-living-universe-sim-engine-';
    if(!upstream.pathname.startsWith(prefix))return route.abort();
    const response=await route.fetch({url:mirror+upstream.pathname.slice(prefix.length)+upstream.search});
    await route.fulfill({response});
   });
   const page=await context.newPage();
   const pageErrors=[];
   page.on('pageerror',err=>pageErrors.push(String(err.message).slice(0,200)));
   const started=Date.now();
   try{
    await page.goto(root+'/spark/index.html',{waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,{timeout:45000});
    await page.locator('#zeref').click();
    await page.waitForFunction(expected=>document.querySelector('#view')?.dataset.creatureId===expected,QBEAST,{timeout:45000});
    const signed=await page.evaluate(()=>{
     const holder=JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1')||'null');
     if(!holder?.text)return null;
     const q=JSON.parse(holder.text);
     return {id:q.profile?.id,seed:q.profile?.seed,format:q.format};
    });
    assert.deepEqual(signed,{id:QBEAST,seed:GENOME,format:'QBEAST1'});
    await page.goto(root+'/sol-game',{waitUntil:'domcontentloaded',timeout:45000});
    const shell=page.locator('[data-lost-cosmos-player-shell]');
    await shell.getByRole('button',{name:'SEND BEAST',exact:true}).click();
    await shell.getByRole('status').filter({hasText:'same Beast verified'}).waitFor({timeout:60000});
    await shell.getByRole('button',{name:'START LOST COSMOS',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.running==='true',null,{timeout:90000});
    const core=page.frames().find(f=>f.url().includes('/sol-spark-gate/handheld.html'));
    assert.ok(core,'Actual native Game Boy iframe failed to mount');
    await core.waitForFunction(()=>!!window.EJS_emulator?.gameManager?.simulateInput,null,{timeout:90000});
    await core.evaluate(()=>{
     const gm=window.EJS_emulator.gameManager,original=gm.simulateInput.bind(gm);
     window.__zeref009Ack=[];
     gm.simulateInput=(player,key,down)=>{window.__zeref009Ack.push([player,key,down]);return original(player,key,down);};
    });
    async function input(key,hold=145){
     if(key==='WAIT'){await delay(hold);return null;}
     assert.ok(Object.hasOwn(INPUT,key),'Unknown native action');
     const before=await core.evaluate(()=>window.__zeref009Ack.length);
     await page.evaluate(button=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',
      {detail:{button:button.toLowerCase(),down:true,source:'agent'}})),key);
     await delay(hold);
     await page.evaluate(button=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',
      {detail:{button:button.toLowerCase(),down:false,source:'agent'}})),key);
     await core.waitForFunction(n=>window.__zeref009Ack.length>=n+2,before,{timeout:8000});
     const trace=await core.evaluate(n=>window.__zeref009Ack.slice(n),before);
     assert.deepEqual(trace.slice(0,2),[[0,INPUT[key],1],[0,INPUT[key],0]],'Actual native press/release not acknowledged: '+key);
     return hex(JSON.stringify(trace));
    }
    async function observation(){
     const o=await core.evaluate(async()=>{
      const {observeNativePixels}=await import('./native-observation.mjs');
      return await observeNativePixels(document);
     });
     assert.ok(optic(o),'Native framebuffer features unavailable; no synthetic substitutions');
     return o;
    }
    async function saveDigest(){
     return core.evaluate(async()=>{
      const raw=window.EJS_emulator?.gameManager?.getSaveFile?.(false);
      if(!raw||raw.length<256)return null;
      const digest=await crypto.subtle.digest('SHA-256',new Uint8Array(raw));
      return Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
     });
    }
    async function progressSnapshot(){
     // Same original EmulatorJS SRAM export used for player battery saves.
     // Transfer only the 7,296-byte native public game-save region to this
     // local CI process; NEVER archive raw bytes or share with the model.
     const saved=await core.evaluate(()=>{
      const b=window.EJS_emulator?.gameManager?.getSaveFile?.(false);
      if(!b||b.length<7296)return null;
      return Array.from(new Uint8Array(b).subarray(0,7296));
     });
     return decode(saved);
    }
    // Identical initial title-entry sequence for every independent episode.
    await delay(1600);await input('A');await delay(650);
    await page.evaluate(()=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button:'start',down:true,source:'agent'}})));
    await delay(150);
    await page.evaluate(()=>window.dispatchEvent(new CustomEvent('beastbox:gba-input',{detail:{button:'start',down:false,source:'agent'}})));
    await delay(1700);
    const first=await observation(),begin=await saveDigest();
    const firstSavedProgress=await progressSnapshot();
    const rows=[],random=seededRandom(20261011+episode);
    for(let step=0;step<STEPS;step++){
     const before=await observation();
     const native_progress_before=await progressSnapshot();
     const scripted_target=teacher(before,episode,step);
     const is_model=policy==='original'||policy==='candidate';
     let action='WAIT',model_reply=null,model_error=null,prompt_sha256=null;
     if(policy==='RIGHT')action='RIGHT';
     else if(policy==='RANDOM')action=ACT[Math.floor(random()*ACT.length)];
     else if(policy==='SCRIPT')action=scripted_target;
     else if(is_model){
      try{
       const result=await infer(policy,before,episode,step);
       model_reply=result.literal_reply;prompt_sha256=result.prompt_sha256;
       action=parseModel(model_reply)||'WAIT';
      }catch(err){model_error=String(err.message).slice(0,220);errors.push(policy+': '+model_error);}
     }
     const ack=await input(action);await delay(260);
     const after=await observation();
     const native_progress_after=await progressSnapshot();
     const native_saved_progress_change=change(native_progress_before,native_progress_after);
     rows.push({schema:'beastbox-zeref-real-native-rollout-step-009',policy,episode,step,qbeast_id:QBEAST,
       native_progress_before,native_progress_after,native_saved_progress_change,
       progress_source:'CHECKSUM_VERIFIED_ACTUAL_GBA_SRAM_IF_AVAILABLE_NOT_LIVE_COORDINATES',
       before,action,after,native_ack_digest:ack,is_model,
       model_literal_reply:model_reply,model_error,model_prompt_sha256:prompt_sha256,
       model_valid_action:is_model?parseModel(model_reply)!==null:null,
       scripted_target,source:'ORIGINAL_GBA_EMULATOR_FRAMEBUFFER_AND_REAL_CONTROLLER_ACK',
       optical_frame_change_is_not_game_reward:true,earned_reward:null,dialogue_advancement:null,
       real_area_discovered:null});
    }
    // These keys are a NEUTRAL, explicitly logged native game menu audit,
    // applied identically after every policy's own action window. Original C
    // Source-verified V11.3 menu, NOT the pre-V11 legacy setting_sel menu:
    // native START -> RIGHT -> UP selects SYSTEM (pause page 9), then A.
    // content_v11_menus.h::v11_update_pause starts v11_sel=0 (AUDIO).
    // DOWN x3 selects SAVE GAME (v11_sel=3), A opens SAVE SLOT page 44.
    // A saves an empty slot; if occupied, A arms overwrite and next A saves.
    // One final A dismisses confirmation. These keys are neutral audit
    // actions AFTER the policy window and are NEVER model commands.
    // Crucially: UP from v11_sel=0 wraps to index 12/SFX and toggles sound,
    // which was OBSERVED in the failed real browser recording 38157714812.
    // No direct SRAM writes, native game cheats or emulator API mutation.
    const nativeSaveMenuKeys=['START','RIGHT','UP','A','DOWN','DOWN','DOWN','A','A','A','A'];
    const saveMenuAcks=[];
    for(const key of nativeSaveMenuKeys)saveMenuAcks.push(await input(key));
    await delay(250);
    const committedAfterNativeMenu=await progressSnapshot();
    const committedSavedDelta=change(firstSavedProgress,committedAfterNativeMenu);
    await input('B');await input('B');
    const end=await saveDigest();
    assert.equal(rows.length,STEPS);
    if(pageErrors.length)throw Error('Actual browser reported exception(s): '+pageErrors.join(' | '));
    const episodeRecord={policy,episode,qbeast_id:QBEAST,rows,
     first_optical_signature:opticsSignature(first),
     initial_native_saved_progress_status:firstSavedProgress.status,
     original_native_save_menu_keys:nativeSaveMenuKeys,
     original_native_save_menu_acks:saveMenuAcks,
     committed_start_native_snapshot:firstSavedProgress,
     committed_end_native_snapshot:committedAfterNativeMenu,
     post_policy_committed_delta:committedSavedDelta,
     real_saved_coordinate_manhattan_pixels:
       committedSavedDelta.status==='checksum_verified_committed_save_comparison'?
       Math.abs(committedAfterNativeMenu.committed_location.x-firstSavedProgress.committed_location.x)+
       Math.abs(committedAfterNativeMenu.committed_location.y-firstSavedProgress.committed_location.y):null,
     native_sram_start_sha256:begin,native_sram_end_sha256:end,
     startup_protocol:'fresh browser context, Spark Zeref, SEND BEAST, native A+START',
     actual_native_progress_proven:false,elapsed_ms:Date.now()-started};
    data[policy].push(episodeRecord);
    all.push(...rows);
    console.log('ZEREF_009_NATIVE_EPISODE='+JSON.stringify({policy,episode,steps:rows.length,
     optics:summarizeArm([episodeRecord]).unique_observed_optical_signatures,
     model_valid:rows.filter(r=>r.is_model&&r.model_valid_action).length,
     committed_after_neutral_save:committedSavedDelta.status,
     saved_manhattan_px:episodeRecord.real_saved_coordinate_manhattan_pixels,
     source_id:QBEAST,objective_progress_measured:committedSavedDelta.status==='checksum_verified_committed_save_comparison'}));
    await output('partial-results.json',{completed_episodes:runIndex,policy_episodes:Object.fromEntries(POLICIES.map(p=>[p,data[p].length])),errors});
   }finally{
    await context.close();
   }
  }
  for(const p of POLICIES)assert.equal(data[p].length,EPISODES,'Policy has missing native game episodes: '+p);
  const digest=all.map(r=>JSON.stringify(r)).join('\n')+'\n';
  await fs.writeFile(out+'/real-native-policy-rollouts.jsonl',digest);
  const summaries=Object.fromEntries(POLICIES.map(p=>[p,summarizeArm(data[p])]));
  assert.equal(all.length,POLICIES.length*EPISODES*STEPS);
  if(!SMOKE){
   assert.equal(summaries.candidate.model_valid_actions+summaries.candidate.model_invalid_or_unavailable,EPISODES*STEPS);
   assert.equal(summaries.original.model_valid_actions+summaries.original.model_invalid_or_unavailable,EPISODES*STEPS);
  }else{
   // The original native save menu MUST yield real displacement under RIGHT,
   // not just optical changes. Reject any smoke whose purported movement did
   // not alter checksum-valid committed coordinates.
   const w=data.WAIT[0],r=data.RIGHT[0];
   assert.equal(w.post_policy_committed_delta.status,'checksum_verified_committed_save_comparison','No valid neutral WAIT save');
   assert.equal(r.post_policy_committed_delta.status,'checksum_verified_committed_save_comparison','No valid neutral RIGHT save');
   assert.equal(w.real_saved_coordinate_manhattan_pixels,0,'Uncontrolled movement in WAIT baseline');
   assert.ok(r.real_saved_coordinate_manhattan_pixels>0,'RIGHT motion not actually committed by original native Save Game menu');
   console.log('ZEREF_009_NEUTRAL_NATIVE_SAVE_SMOKE='+JSON.stringify({
    wait_px:w.real_saved_coordinate_manhattan_pixels,
    right_px:r.real_saved_coordinate_manhattan_pixels,
    wait_location:w.committed_end_native_snapshot.committed_location,
    right_location:r.committed_end_native_snapshot.committed_location,
    not_a_game_reward:true}));
  }
  const savedByArm=Object.fromEntries(POLICIES.map(p=>{
   const rows=data[p].flatMap(e=>e.rows),confirmed=rows.map(r=>r.native_saved_progress_change)
     .filter(r=>r.status==='checksum_verified_committed_save_comparison');
   const committed=data[p].map(e=>e.post_policy_committed_delta)
     .filter(x=>x.status==='checksum_verified_committed_save_comparison');
   const displacement=data[p].map(e=>e.real_saved_coordinate_manhattan_pixels).filter(Number.isFinite);
   return [p,{checksummed_saved_state_pairs:confirmed.length,
    during_action_window_new_saved_objective_events:confirmed.reduce((a,b)=>a+b.new_saved_progression_events,0),
    neutral_save_menu_verified_episodes:committed.length,
    after_neutral_save_new_game_objective_events:committed.reduce((a,b)=>a+b.new_saved_progression_events,0),
    post_policy_saved_position_changed_episodes:committed.filter(x=>x.saved_location_changed).length,
    total_committed_saved_coordinate_displacement_px:displacement.reduce((a,b)=>a+b,0),
    individual_committed_displacement_px:displacement,
    unavailable_saved_state_steps:rows.length-confirmed.length}];
  }));
  const report={schema:'beastbox-zeref-native-controlled-rollouts-009',
    source_class:'REAL_NATIVE_GBA_EMULATOR_CONTROLLER_ACKS_AND_NEUTRAL_SOURCE_GAME_SAVE_MENU',
    qbeast_id:QBEAST,source_ibm_job_id:JOB,source_seed:GENOME,
    baseline_original_weights_sha256:MODEL_HASHES.original,candidate_weights_sha256:MODEL_HASHES.candidate,
    policies:POLICIES,episodes_per_policy:EPISODES,steps_per_episode:STEPS,
    saved_native_objective_by_arm:savedByArm,
    neutral_original_native_ui_save_at_end_of_every_episode:true,
    neutral_ui_commands_not_part_of_model_or_script_policy:true,
    progress_metric_kind:'source_validated_committed_LCV5_save_with_optional_LC11_LCB8_CRC',
    game_objective_outperformance_proven:false,
    missing_valid_save_is_not_zero_reward:true,
    actual_live_player_position_observable:false,
    raw_native_action_rows:all.length,real_observation_count:all.length*2,
    source_frame_sha256:SHA(digest),each_arm:summaries,episodes:data,
    model_replies_are_real_cpu_inference:true,no_live_production_model_promotion:true,
    new_ibm_hardware_jobs_in_this_run:0,quantum_trained_weights:false,
    objective_events_observed_only_from_checksum_valid_native_save:true,
    semantic_dialogue_progress_still_uninstrumented:true,
    unsaved_live_coordinates_not_measured:true,
    no_claim_of_intelligent_exploration_or_learned_game_success:true,
    errors,run_timestamp:new Date().toISOString()};
  await output('report.json',report);
  console.log('ZEREF_009_ACTUAL_NATIVE_COMPARISON='+JSON.stringify({policies:POLICIES,episodes:EPISODES,
   candidate:summaries.candidate,original:summaries.original,wait:summaries.WAIT,source_sha256:report.source_frame_sha256,
   saved_progress_by_arm:savedByArm,real_game_progress_measurable:Object.values(savedByArm).some(v=>v.checksummed_saved_state_pairs>0)}));
 }catch(err){
  await output('failure.json',{message:String(err.message).slice(0,600),name:err.name,
   completed_episodes:Object.fromEntries(POLICIES.map(p=>[p,data[p].length])),
   errors,no_fabricated_partial_success:true});
  throw err;
 }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
