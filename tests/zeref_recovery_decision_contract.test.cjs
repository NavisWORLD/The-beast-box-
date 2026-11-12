// The interrupted-round recovery job reports the SAME promotion numbers as a finished round:
// both steps call the one rule module (scripts/zeref_promotion_rule.py), and recovery never promotes.
// 2026-11-12: Cory loosened the promotion rule; the old strict rule is kept in that module.
const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
const wf=fs.readFileSync('.github/workflows/zeref-continuous-learning-006.yml','utf8');
const RULE="python -u scripts/zeref_promotion_rule.py apps/beastbox-cloud/lib/rawrphos-public-pin.json build/zeref-006/report.json build/zeref-006/";
test('promotion rule module is called by the training job and the recovery job',()=>{
 assert.equal(wf.split(RULE).length-1,2);
 assert.match(wf,/build\/zeref-006\/chat-eval\.json build\/zeref-006\/promotion-decision\.json/);
 const mod=fs.readFileSync('scripts/zeref_promotion_rule.py','utf8');
 assert.match(mod,/STRICT_2026_10_22 = "strict-2026-10-22"/);
 assert.match(mod,/ok = bool\(chat_not_worse and nll_ok\)/,'old predicate kept for a one-line revert');
 assert.match(mod,/leaks_ok = type\(leaks\) is int and leaks == 0/,'leak screen stays hard');
});
test('recovery decision is report-only and reads the recovery chat eval',()=>{
 const i=wf.indexOf('Same promotion rule on the recovered checkpoint');assert.ok(i>0);
 const block=wf.slice(i,wf.indexOf('- name:',i+10));
 assert.match(block,/recovery-chat-eval\.json/);assert.match(block,/"report_only":true,"publication_performed":false/);
 assert.doesNotMatch(block,/approval\.json|gh pr|git push/);
});
