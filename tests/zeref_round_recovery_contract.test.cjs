const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const w=fs.readFileSync('.github/workflows/zeref-continuous-learning-006.yml','utf8');
const t=fs.readFileSync('scripts/zeref_continuation_006.py','utf8');
test('bounded multi-variant work has independent interruption scoring and CI headroom',()=>{
 assert.match(w,/timeout-minutes: 340/);
 // 2026-11-18 round-clock fix (deliberate, owner-requested): the single 300-minute training step was split
 // into one step per workload, each with its own 150-minute clock, plus a final scoring step.
 assert.doesNotMatch(w,/timeout-minutes: 300/);
 assert.equal((w.match(/continue-on-error: true\n        timeout-minutes: 150\n        run: build\/zeref-006\/run-phase\.sh (control|candidate [0-3])\n/g)||[]).length,5);
 for(const p of ['control','candidate 0','candidate 1','candidate 2','candidate 3'])assert.ok(w.includes('run: build/zeref-006/run-phase.sh '+p+'\n'),'missing split step '+p);
 assert.match(w,/id: continuation\n[\s\S]*?build\/zeref-006\/run-phase\.sh final/);
 assert.match(w,/ZEREF_006_JOB_DEADLINE_S: '20400'/);
 assert.match(w,/scripts\/zeref_round_heartbeat\.py/);
 assert.match(w,/ZEREF_006_CANDIDATES: '4'/);
 assert.match(w,/ZEREF_006_CANDIDATE_BUDGET_S: '15000'/);
 assert.match(w,/ZEREF_006_TIME_BUDGET_S: '3600'/);
 assert.match(w,/score-interrupted:/);
 assert.match(w,/needs: train-zeref/);
 assert.match(w,/always\(\).*needs.train-zeref.result/);
 assert.match(w,/--score-recovery/);
 assert.match(w,/zeref-006-recovery-/);
 assert.match(w,/Persist final scored evidence/);
});
test('split round: each workload resumes the same parent, best-in-cycle persisted across steps, same selection rule',()=>{
 for(const needle of ['PHASE=os.environ.get("ZEREF_006_PHASE","all")','def split_candidate_step(','def split_final_state(',
   'train_variant(PARENT,tokenizer,pool,cseed,chat_pool,ce,lr=LR*mult,min_frac=floor,recovery_candidate=ci)',
   'if best is None or a_c<best["chat_a_nll"]:','tmp.replace(CYCLE_DIR/"best-state.pt")','ZEREF_006_CANDIDATE_MISSING=',
   'best-in-cycle is not the lowest set-A candidate'])assert.ok(t.includes(needle),'missing '+needle);
 assert.equal((t.match(/print\("ZEREF_006_CANDIDATE="/g)||[]).length,2);
});
test('recovery reuses unchanged scoring, never trains or publishes partial checkpoints',()=>{
 assert.match(t,/def main\(recovery=False\)/);
 assert.match(t,/load_snapshot\(ROOT\)/);
 assert.match(t,/recovery_candidate=ci/);
 assert.match(t,/if accepted and not recovery:/);
 assert.match(t,/recovery-score.json/);
});
test('only training owns the global lineage lock; contract and recovery scoring are independent',()=>{
 assert.doesNotMatch(w,/^concurrency:/m);
 assert.match(w,/    concurrency:\n      group: zeref-006-single-approved-learning-lineage\n      cancel-in-progress: false/);
});
test('browser verification runs on a Playwright-supported pinned runner',()=>{
 const ci=fs.readFileSync('.github/workflows/product-ci.yml','utf8');
 assert.match(ci,/  cosmic-browser:\n    runs-on: ubuntu-24.04/);
});
