// Origin spark pulse: RECORDED, deterministic, advances, no Math.random.
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {sparkPulse,pulseHash,BEAT_MS,SPARK_SEED,RECORDED_PAIRS} from '../lib/zeref/spark-pulse.mjs';
test('deterministic, labelled RECORDED, advances each beat',()=>{const t=Date.parse('2026-11-01T06:00:00Z');
 const a=sparkPulse(t),b=sparkPulse(t),c=sparkPulse(t+BEAT_MS);assert.deepEqual(a,b);assert.equal(a.label,'RECORDED');
 assert.equal(c.beat,a.beat+1);assert.notEqual(c.pulse_sha256,a.pulse_sha256);assert.equal(a.pulse_sha256,pulseHash(a.beat));
 assert.ok(a.glow>=0&&a.glow<1);assert.ok(!/live quantum/i.test(JSON.stringify(a)));});
test('recorded values match the v11 evidence',()=>{const e=JSON.parse(fs.readFileSync(new URL('../../../evidence/zeref-heart-seed-v11/ibm-chsh-result-public.json',import.meta.url),'utf8'));
 assert.equal(e.job_id,'dbj7a40nceqs73ajd2d0');for(const [k,w] of RECORDED_PAIRS)assert.equal(e.quantum.per_question_pair[k].win_rate,w);
 const h=JSON.parse(fs.readFileSync(new URL('../../../evidence/zeref-heart-seed-v11/heart-seed-v11.json',import.meta.url),'utf8'));assert.equal(h.heart_seed_sha256,SPARK_SEED);});
test('no Math.random in the pulse files',()=>{for(const f of ['../lib/zeref/spark-pulse.mjs','../components/zeref-spark-pulse.tsx'])assert.ok(!fs.readFileSync(new URL(f,import.meta.url),'utf8').includes('Math.random'));});
