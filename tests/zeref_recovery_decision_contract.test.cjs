// The interrupted-round recovery job reports the SAME promotion numbers as a finished round:
// its rule lines must be byte-identical to the training job's promotion step, and it never promotes.
const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
const wf=fs.readFileSync('.github/workflows/zeref-continuous-learning-006.yml','utf8');
const RULE=[
 "bar=g.get('chat_before_nll') or (pin.get('promotion') or {}).get('candidate_ref_nll') or ev['baseline']['ref_nll']",
 "c=ev['candidate']['ref_nll'];tol=0.005;ok=bool(ev['chat_not_worse'] and c<=bar*(1+tol))",
 "d={'schema':'zeref-promotion-decision-v1','candidate_ref_nll':c,'pin_ref_nll_bar':bar,'tolerance':tol,'rule':'within 0.5% of pin on set A AND fresh held-out set B not worse (training gate)','chat_not_worse_vs_14000':ev['chat_not_worse'],'promote':ok}"];
test('promotion rule appears identically in the training job and the recovery job',()=>{
 for(const line of RULE)assert.equal(wf.split(line).length-1,2,line);
});
test('recovery decision is report-only and reads the recovery chat eval',()=>{
 const i=wf.indexOf('Same promotion rule on the recovered checkpoint');assert.ok(i>0);
 const block=wf.slice(i,wf.indexOf('PY\n',wf.indexOf("python - <<'PY'",i)+20));
 assert.match(block,/recovery-chat-eval\.json/);assert.match(block,/'report_only':True,'publication_performed':False/);
 assert.doesNotMatch(block,/approval\.json|gh pr|git push/);
});
