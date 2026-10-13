import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {researchEvidence} from '../lib/zeref/research-status.mjs';

const raw=JSON.parse(readFileSync(new URL('../public/spark/zeref-learning/research-status.json',import.meta.url)));

test('research approval does not promote rejected candidates or replace the production model',()=>{
 const view=researchEvidence(raw);
 assert.equal(view.approved.checkpoint_sha256,'460a1a3fbbc16919c5030af16d5bd451ef43e96fd28b8c3201ca7efca1250ef2');
 assert.equal(view.approved.training_steps,14448);
 assert.equal(view.runtime.stable_training_steps,14000);
 assert.equal(view.runtime.approved_research_checkpoint_served,false);
 assert.equal(view.runtime.fresh_inference_verified,false);
 assert.ok(view.trials.every(x=>x.status==='REJECTED'&&!x.eligible_as_parent&&!x.production_promoted));
 assert.equal(view.trials.find(x=>x.experiment==='012').generated_answers.candidate.correct,0);
 assert.ok(view.trials.find(x=>x.experiment==='013').losses.action_conditioned>view.trials.find(x=>x.experiment==='013').losses.action_blind);
});

test('a rejected checkpoint or a merged identity cannot become an approved research view',()=>{
 const rejected=structuredClone(raw);
 rejected.latest_approved_research_parent.checkpoint_sha256=raw.latest_research[0].checkpoint_candidate;
 assert.equal(researchEvidence(rejected),null);
 const merged=structuredClone(raw);
 merged.display_identity.qbeast_id=merged.training_identity.qbeast_id;
 assert.equal(researchEvidence(merged),null);
 const weak=structuredClone(raw);
 weak.latest_approved_research_parent.status='workflow success';
 assert.equal(researchEvidence(weak),null);
});

test('the historical Experiment 011 rejection record stays byte-identical',()=>{
 const old=readFileSync(new URL('../public/spark/zeref-learning/status.json',import.meta.url));
 assert.equal(createHash('sha256').update(old).digest('hex'),'ec777aad9b54e91d89aa7f3b739da07a91047155e1d0a4934986d6ef3412b6a6');
 assert.equal(JSON.parse(old).accepted,false);
});
