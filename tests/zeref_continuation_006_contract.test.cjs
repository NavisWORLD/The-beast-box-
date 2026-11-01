'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const read=p=>fs.readFileSync(p,'utf8');
test('Zeref real native capture keeps canonical QBEAST, original ROM and real key ACKs',()=>{
 const s=read('apps/beastbox-cloud/tests/rawrphos-native-observed-play.cjs');
 assert.match(s,/id:'bb-deada969'/);
 assert.match(s,/source_job:'db4q484vf2bc73cuuuag'/);
 assert.match(s,/NAVISWORLD_NATIVE_TRAINING_CYCLE/);
 assert.match(s,/source:'agent'/);
 assert.match(s,/native_ack_digest/);
 assert.match(s,/teacher_cycle_offset/);
 assert.match(s,/reward_is_not_native_progress:true/);
});
test('Bounded optimizer resumes actual checkpoint and fails closed without fresh observations',()=>{
 const s=read('scripts/zeref_continuation_006.py');
 for(const needle of ['load_training_state=True','opt.load_state_dict(parent["state"]["optimizer"])','LEGACY_UPDATES=64','UPDATES=int(os.environ.get("ZEREF_006_UPDATES",str(SHORT_UPDATES)))','expected_steps(cycle)',
   'source_digest==prior_digest','accepted_as_next_training_parent','teacher_agreement_not_worse',
   'no_new_qpu_job','production_promoted','native_game_progress_demonstrated',
   'CANONICAL_APPROVED_ROOT','canonical_lineage_root_sha256']){
  assert.ok(s.includes(needle),'Missing nonnegotiable proof '+needle);
 }
 assert.doesNotMatch(s,/QiskitRuntimeService|SamplerV2|import azure|run_ibm_qpu/);
});
test('Scheduled Zeref CPU heartbeat keeps one-at-a-time serialized training and never authorizes IBM budget',()=>{
 const s=read('.github/workflows/zeref-continuous-learning-006.yml');
 assert.match(s,/cron: '17 \*\/6 \* \* \*'/);
 assert.match(s,/cancel-in-progress: false/);
 assert.match(s,/zeref-006-accepted-checkpoint-/);
 assert.ok(s.includes('zeref-006-canonical-37ca3f8f'),'Exactly named canonical artifact needed to avoid 100-item GitHub paging loss');
 assert.ok(s.includes('38129248023'),'Bootstrap must use actual original approved 006 AdamW continuation');
 assert.ok(!s.includes('38109635009'),'Must never silently reset Zeref to old 004 CPU checkpoint');
 assert.ok(s.includes('ZEREF_010_VERIFIED_CANONICAL_PARENT'),'Verify parent SHA BEFORE capturing expensive new episodes');
 assert.match(s,/actions\/download-artifact|gh run download/);
 assert.match(s,/python -u scripts\/zeref_continuation_006.py/);
 assert.doesNotMatch(s,/IBM_QUANTUM_TOKEN|BEAST_ZEREF_IBM_ONE_JOB|secrets\.IBM/);
});

test('Observation diagnostics distinguish teacher imitation from verified game progress',()=>{
 const s=read('scripts/zeref_continuation_006.py');
 for(const needle of [
  'native_observation_diagnostics',
  'unique_before_frame_summaries',
  'unique_after_frame_summaries',
  'different_before_after_summaries',
  'scripted_teacher_action_histogram',
  'parent_policy_actions',
  'candidate_policy_actions',
  'dominant_action_fraction',
  'visual_metrics_not_verified_game_movement',
  'policy_diversity_not_quest_progress',
  'ZEREF_006_OBSERVATION_DIAGNOSTICS',
 ])assert.ok(s.includes(needle),'Missing observable policy/raster audit: '+needle);
 assert.match(s,/"native_game_progress_demonstrated":False/);
 assert.match(s,/"teacher_is_scripted_not_human":True/);
});

test('Static native screen no longer creates a RIGHT-only teacher distribution',()=>{
 const cap=read('apps/beastbox-cloud/tests/rawrphos-native-observed-play.cjs');
 const train=read('scripts/zeref_continuation_006.py');
 assert.match(cap,/if\(o\.frameChange<5\)return VISIBLE_KEYS\[\(o\.contrast\+o\.brightness\)%VISIBLE_KEYS\.length\]/);
 assert.doesNotMatch(cap,/episode\*3\+step\+cycle/);
 assert.doesNotMatch(cap,/if\(o\.frameChange<5\)return 'RIGHT'/);
 for(const needle of ['scripted_teacher_action_histogram',
                      'scripted_teacher_dominant_action_fraction',
                      'Object.keys(counts).length>=4','dominantShare<=0.65']){
  assert.ok(cap.includes(needle),'missing native teacher diversity safeguard: '+needle);
 }
 for(const needle of ['actual_actions=Counter(r["action"] for r in rows)',
                      'scripted_teacher_action_histogram',
                      'native_heldout_policy_not_single_action',
                      'candidate_action_diversity_not_navigation_progress']){
  assert.ok(train.includes(needle),'missing research-only action-diversity receipt/gate: '+needle);
 }
 assert.match(train,/"native_game_progress_demonstrated":False/);
 assert.match(train,/"teacher_is_scripted_not_human":True/);
});

test('2026-10-16 fixes: fresh order per attempt, anti-ratchet chat gate, calmer drift, boot-race wait',()=>{
 const t=read('scripts/zeref_continuation_006.py'),w=read('.github/workflows/zeref-continuous-learning-006.yml');
 const cap=read('apps/beastbox-cloud/tests/rawrphos-native-observed-play.cjs'),mix=read('scripts/zeref_chat_corpus.py');
 assert.ok(t.includes('rigetti_order_seed(cycle,source_digest,RUN_ID)'));
 assert.ok(t.includes('"label":"SIMULATED"'));
 assert.ok(t.includes('chat_bar=max(.01,original_chat)'),'fix 002: absolute chat bar vs the pin parent');
 assert.ok(t.includes('LR=float(os.environ.get("ZEREF_006_LR","0.00001"))'));assert.ok(t.includes('math.cos(math.pi*n/UPDATES)'));
 assert.ok(mix.includes('DAD_REPEAT=2'));
 assert.ok(w.includes('ZEREF_006_PUBLIC_REF_DIR: build/public-14k'));
 assert.ok(w.includes('scripts/rawrphos_chat_eval.py build/public-14k'),'14000 public chat test stays the promotion check');
 assert.ok(w.includes('scripts/zeref_teacher_distill.py'));
 assert.ok(cap.includes('await waitForGameplay()'));
});

test('2026-10-17 fix 002: pin parent, promotion bar, Dolly rotation, lessons, best-in-cycle, boot retries',()=>{
 const t=read('scripts/zeref_continuation_006.py'),w=read('.github/workflows/zeref-continuous-learning-006.yml');
 assert.ok(w.includes('RESUME_PUBLIC_PIN_RELEASE='),'parent = public pin release');
 assert.ok(w.includes("ZEREF_PROMOTION_DECISION="),'absolute promotion bar vs current pin');
 assert.ok(w.includes('ZEREF_CHAT_ROTATE_SEED='),'fresh Dolly sample per cycle');
 assert.ok(w.includes('for attempt in 1 2 3 4'),'boot-race retries');
 assert.ok(t.includes('best_in_cycle_step'));
 const d=read('scripts/zeref_teacher_distill.py');assert.ok(d.includes('"SHARED_TEACHER_AUTO"')&&d.includes('"shared-ollama"'));assert.ok(d.includes('MAX_FRACTION=0.15'));
 const c=read('apps/beastbox-cloud/scripts/zeref-cloud-sync.mjs');assert.ok(c.includes("ZEREF_DIR+'/lessons/'"));
});

test('2026-10-17 Alien Injection 001: capped filtered TALK-006 slice in the chat mix; quantum run only seeded/tagged',()=>{
 const mix=read('scripts/zeref_chat_corpus.py');assert.ok(mix.includes('ALIEN_MAX_FRACTION=0.06'));assert.ok(mix.includes('persona_style(a)!=a'));assert.ok(mix.includes('r.get("split")!="train"'));
 const w=read('.github/workflows/zeref-alien-injection-001.yml');assert.ok(w.includes("CHSH_QPU_CAP: '67'"));assert.ok(w.includes('cannot learn text'));assert.ok(w.includes('YES_ONE_FREE_SIMULATOR'));
});
test('fix 003: same chat yardstick as the public pin, character check, warm slice',()=>{
 const t=read('scripts/zeref_continuation_006.py'),mix=read('scripts/zeref_chat_corpus.py'),c=read('scripts/zeref_character_check.py');
 assert.ok(t.includes('original_chat=pair_nll(model,chat_t)'),'pin re-measured with the public-pin formula');
 assert.ok(t.includes('ce=lambda m:pair_nll(m,chat_t)'),'best-in-cycle on the same yardstick');
 assert.ok(t.includes('chat_bar=max(.01,original_chat)'),'no hidden margin');
 assert.ok(t.includes('"character_no_rude_or_unsafe_regression"'));
 assert.ok(c.includes('candidate["rude_or_unsafe"]<=parent["rude_or_unsafe"]'));
 assert.ok(mix.includes('WARM_MAX_FRACTION=0.05')&&mix.includes('CHARACTER_PROMPTS'),'warm slice capped; check prompts held out');
});

test('2026-10-25 multi-candidate rounds keep Gate v2 unchanged and select on set A only',()=>{
 const t=read('scripts/zeref_continuation_006.py'),w=read('.github/workflows/zeref-continuous-learning-006.yml');
 for(const needle of['CAND_SPECS','ZEREF_006_CANDIDATE=','ZEREF_006_CANDIDATE_SELECTED=','chat_fresh_heldout_b_not_worse_than_pin',
   'new_chat_b<=chat_bar_b','CHAT_A_TOLERANCE=0.005','CHAT_B_TOLERANCE=0.005','set B never used to select','WIDE_FROM_CYCLE=45;WIDE_UPDATES=320'])
  assert.ok(t.includes(needle),'missing '+needle);
 assert.ok(!t.includes('64-cycle training budget cap'),'64-cycle cap must stay removed');
 assert.match(w,/ZEREF_006_CANDIDATES: '4'/);
 assert.match(w,/cron: '17 \*\/6 \* \* \*'/);
});
