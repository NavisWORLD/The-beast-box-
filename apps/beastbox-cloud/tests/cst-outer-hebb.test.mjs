import test from 'node:test';import assert from 'node:assert/strict';
import {createCSTState,stepCSTState,hebbVector,outerHebbStrength,HEBB_OUTER,HEBB12,creatureMood} from '../lib/physics/cst-integrator.mjs';
const mean=a=>a.reduce((s,x)=>s+x,0)/a.length,sd=a=>{const m=mean(a);return Math.sqrt(a.reduce((s,x)=>s+(x-m)**2,0)/(a.length-1));};
const E={valence:.7,arousal:.55,curiosity:.8,fear:.1};
const SEEDS=[...Array(20)].map((_,i)=>'ab'+(201+i)),T=3000,DT=.05;
const KEYS=['coherence','chaos','hebb','mood_joy','mood_calm'];
const run=(seed,opts)=>{const S=createCSTState(seed,{emotion:E});for(let i=0;i<T;i++)stepCSTState(S,DT,E,opts);
 const m=creatureMood(S.ch);return {S,coherence:S.ch.coherence,chaos:S.ch.chaos,hebb:S.hebb,mood_joy:m.joy,mood_calm:m.calm};};
const batch=opts=>SEEDS.map(s=>run(s,opts));

test('default stays the relaxation rule: no W is created, flag off/{} behaves identically',()=>{
 const a=batch(null),b=batch({outerHebb:false});
 a.forEach((r,i)=>{assert.equal(r.S.W,undefined);assert.deepEqual(r.S,b[i].S);});
});
test('outer-product rule: weights bounded in [0,wMax], deterministic, channels stay in [0,1]',()=>{
 const a=batch({outerHebb:true}),b=batch({outerHebb:true});
 a.forEach((r,i)=>{assert.deepEqual(r.S,b[i].S);assert.equal(r.S.W.length,144);
  for(const w of r.S.W)assert.ok(w>=0&&w<=HEBB_OUTER.wMax);
  for(const v of Object.values(r.S.ch))assert.ok(v>=0&&v<=1);assert.ok(r.S.hebb>=0&&r.S.hebb<=1);});
 // learns the outer product: after settling W_ij ≈ pre_i·post_j (η=decay)
 const S=a[0].S,v=hebbVector(S);let err=0;for(let i=0;i<11;i++)for(let j=0;j<11;j++)err=Math.max(err,Math.abs(S.W[i*12+j]-v[i]*v[j])); // 11 settled channels; Lorenz x swings fast so it is excluded here
 assert.ok(err<.2,'max |W − v vᵀ| = '+err);
 // pairs that co-activate wire stronger than pairs with a silent member (valence·curiosity vs avoid·chaos)
 const ix=k=>HEBB12.indexOf(k);assert.ok(S.W[ix('valence')*12+ix('curiosity')]>S.W[ix('avoid')*12+ix('chaos')]);
});
test('ABLATION (combined.mjs style): paired change vs the default relaxation baseline, 20 seeds',()=>{
 const base=batch(null);
 const C={'outer-product rule ON (η=decay=.5, pull .10)':{outerHebb:true},
  'outer ON, pull 0 (W learns but cannot reach the dynamics)':{outerHebb:{pull:0}},
  'outer ON, η=0 (W stays 0, pull drags S.hebb to 0)':{outerHebb:{eta:0}},
  'outer ON, decay 5 (short memory)':{outerHebb:{decay:5,eta:5}},
  'ψ MODEL nudge ON (opts.psi)':{psi:true},
  'outer + ψ together':{outerHebb:true,psi:true}};
 console.log('Cell = Glass Δ (mean change / between-seed SD of baseline); * = paired change > 2 SE; (relative change). MODEL ablation, not a measurement.');
 console.log('baseline means:',KEYS.map(k=>`${k}=${mean(base.map(r=>r[k])).toFixed(4)}`).join(' '));
 console.log('| condition | '+KEYS.join(' | ')+' |');console.log('|---|'+KEYS.map(()=>'---').join('|')+'|');
 const res={};
 for(const [name,o] of Object.entries(C)){const r=batch(o);res[name]=r;
  console.log(`| ${name} | `+KEYS.map(k=>{const d=r.map((x,i)=>x[k]-base[i][k]),m=mean(d),s=sd(d),sb=sd(base.map(x=>x[k]))||1e-12,bm=mean(base.map(x=>x[k]));
   return `${(m/sb).toFixed(2)}${Math.abs(m)>2*s/Math.sqrt(d.length)?'*':''} (${(100*m/(bm||1e-12)).toFixed(1)}%)`;}).join(' | ')+' |');}
 // pull 0: W is inert, trajectory is exactly the baseline on every dynamical channel
 res['outer ON, pull 0 (W learns but cannot reach the dynamics)'].forEach((r,i)=>{assert.deepEqual(r.S.ch,base[i].S.ch);assert.equal(r.S.hebb,base[i].S.hebb);assert.ok(outerHebbStrength(r.S)>0);});
 // the pull is the effect: η=0 (no learned structure) vs learned W give different S.hebb on every seed
 const on=res['outer-product rule ON (η=decay=.5, pull .10)'],z=res['outer ON, η=0 (W stays 0, pull drags S.hebb to 0)'];
 on.forEach((r,i)=>assert.notEqual(r.S.hebb,z[i].S.hebb));
 assert.ok(mean(on.map(r=>r.hebb))>mean(z.map(r=>r.hebb)));
});
