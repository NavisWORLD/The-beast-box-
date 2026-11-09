const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const w=fs.readFileSync('.github/workflows/zeref-continuous-learning-006.yml','utf8');
const t=fs.readFileSync('scripts/zeref_continuation_006.py','utf8');
test('bounded multi-variant work has independent interruption scoring and CI headroom',()=>{
 assert.match(w,/timeout-minutes: 280/);
 assert.match(w,/timeout-minutes: 240/);
 assert.match(w,/ZEREF_006_CANDIDATES: '4'/);
 assert.match(w,/ZEREF_006_CANDIDATE_BUDGET_S: '12000'/);
 assert.match(w,/ZEREF_006_TIME_BUDGET_S: '2700'/);
 assert.match(w,/score-interrupted:/);
 assert.match(w,/needs: train-zeref/);
 assert.match(w,/always\(\).*needs.train-zeref.result/);
 assert.match(w,/--score-recovery/);
 assert.match(w,/zeref-006-recovery-/);
 assert.match(w,/Persist final scored evidence/);
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
