import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {psiTerms,psi,bekensteinBits,L_PLANCK,LN_2,PSI_CONST,creaturePsi,creaturePsiK,psiNudge,PSI_GAIN,PSI_CHANNELS} from '../lib/physics/cst-psi.mjs';
import {createCSTState,stepCSTState,lorenzStep,coherenceFeedback,clamp} from '../lib/physics/cst-integrator.mjs';
const ref=JSON.parse(readFileSync(new URL('./fixtures/cst-psi-reference.json',import.meta.url),'utf8'));
const rel=(a,b)=>Math.abs(a-b)/(Math.abs(b)||1);

test('ψ parity: JS port equals the Python cst_psi.py reference values (fixed inputs, rel 1e-9)',()=>{
 assert.equal(PSI_CONST.G,ref.constants.G);assert.equal(PSI_CONST.C,ref.constants.C);assert.equal(PSI_CONST.MPC,ref.constants.MPC);
 assert.ok(rel(L_PLANCK,ref.constants.L_PLANCK)<1e-12);
 for(const [r,bits] of ref.bits)assert.ok(rel(bekensteinBits(r),bits)<1e-12,`bits(${r})`);
 for(const c of ref.cases){
  const {tau,r0,ell,...sys}=c.input,o=psiTerms(sys,{tau,r0,ell});
  for(const k of ['K','S','U','I','psi'])c.out[k].forEach((e,i)=>assert.ok(rel(o[k][i],e)<1e-9||Math.abs(o[k][i]-e)<1e-300,`${k}[${i}] ${o[k][i]} vs ${e}`));
 }
});
test('ψ port: dimensionless K is mass independent, coincident entities throw, ψ = K+S+U+I',()=>{
 const c=ref.cases[0].input,a=psiTerms(c),b=psiTerms({...c,masses:c.masses.map(m=>m*7)});
 a.K.forEach((k,i)=>assert.ok(rel(b.K[i],k)<1e-12));
 a.psi.forEach((p,i)=>assert.ok(rel(p,a.K[i]+a.S[i]+a.U[i]+a.I[i])<1e-15));
 assert.throws(()=>psi({masses:[1,1],positions:[[0,0],[0,0]],velocities:[[0,0],[0,0]],radii:[1,1],lyapunovs:[0,0]}),/coincident/);
 assert.ok(rel(bekensteinBits(3.5e8),4*Math.PI*3.5e8**2/(4*L_PLANCK**2*LN_2))<1e-12);
});
const ch=v=>Object.fromEntries(PSI_CHANNELS.map(k=>[k,v]));
test('creature ψn is bounded in (0,1), monotone in the channels, 0.5 at the reference, deterministic',()=>{
 assert.ok(Math.abs(creaturePsi(ch(.5))-.5)<1e-12);
 let prev=-1;for(let v=0;v<=1.0001;v+=.1){const p=creaturePsi(ch(v));assert.ok(p>=0&&p<1&&p>=prev);prev=p;assert.equal(p,creaturePsi(ch(v)));}
 assert.equal(creaturePsiK(ch(0)),0);assert.ok(creaturePsi(ch(7))<1&&creaturePsi(ch(-3))===0&&Number.isFinite(creaturePsi({})));
 assert.ok(Math.abs(psiNudge(ch(1)))<=PSI_GAIN/2&&Math.abs(psiNudge(ch(0)))<=PSI_GAIN/2);
});

// frozen copy of stepCSTState as it was before this change (fallback must stay bit-identical)
function legacyStep(S,dt,emotion=null){
 const c=S.ch;
 if(emotion){for(const [k,src] of [['valence','valence'],['arousal','arousal'],['curiosity','curiosity'],['avoid','fear']])
  if(Number.isFinite(emotion[src]))c[k]+=(clamp(emotion[src])-c[k])*Math.min(1,dt*3);}
 lorenzStep(S.L,dt*.35,{arousal:c.arousal,qe:c.quantum_entropy});
 const lx=clamp(.5+S.L.x/40),ly=clamp(.5+S.L.y/50);
 c.chaos+=(clamp(Math.abs(lx-.5)*1.4+Math.abs(ly-.5)*.6)-c.chaos)*Math.min(1,dt*2);
 c.instability+=(clamp(c.chaos*.5+c.avoid*.4+c.arousal*.2)-c.instability)*Math.min(1,dt*2);
 const coh=coherenceFeedback(clamp((1-c.instability)*.5+c.valence*.3+c.phi_harmonics*.2),S.hebb);
 c.coherence+=(coh-c.coherence)*Math.min(1,dt*2);
 S.hebb+=(clamp(c.coherence*.6+c.valence*.2)-S.hebb)*dt*.05;
 c.resonance+=(clamp(c.coherence*.7+c.valence*.3)-c.resonance)*Math.min(1,dt);
 S.phase+=dt*(1+c.arousal);
 return S;
}
test('default (no opts) stays bit-identical to the original relaxation rule; opts.psi:false/null too',()=>{
 for(const seed of ['a','zeref','bb-x']){
  const e={valence:.7,arousal:.3,curiosity:.8,fear:.1},A=createCSTState(seed,{emotion:e}),B=createCSTState(seed,{emotion:e}),C=createCSTState(seed,{emotion:e});
  for(let i=0;i<4000;i++){legacyStep(A,.05,e);stepCSTState(B,.05,e);stepCSTState(C,.05,e,{psi:false});}
  assert.deepEqual(B,A);assert.deepEqual(C,A);
 }
});
test('opts.psi is flagged MODEL: bounded modulation, deterministic, channels stay in [0,1]',()=>{
 const e={valence:.7,arousal:.6,curiosity:.8,fear:.1},A=createCSTState('p',{emotion:e}),B=createCSTState('p',{emotion:e}),D=createCSTState('p',{emotion:e});
 for(let i=0;i<4000;i++){stepCSTState(A,.05,e);stepCSTState(B,.05,e,{psi:true});stepCSTState(D,.05,e,{psi:true});}
 assert.deepEqual(B,D);assert.notDeepEqual(B.ch,A.ch);
 for(const v of Object.values(B.ch))assert.ok(v>=0&&v<=1);assert.ok(B.hebb>=0&&B.hebb<=1);
 // bounded: with gain g the coherence target moves ≤ g/2, so steady coherence differs by far less than 1
 assert.ok(Math.abs(B.ch.coherence-A.ch.coherence)<.15);
 const Z=createCSTState('p',{emotion:e});for(let i=0;i<4000;i++)stepCSTState(Z,.05,e,{psi:{gain:0}});assert.deepEqual(Z,A);
});
test('source states the MODEL label and the Lorenz dt difference',()=>{
 const p=readFileSync(new URL('../lib/physics/cst-psi.mjs',import.meta.url),'utf8'),i=readFileSync(new URL('../lib/physics/cst-integrator.mjs',import.meta.url),'utf8');
 assert.match(p,/LABEL: MODEL/);assert.doesNotMatch(p.replace(/\/\*[^]*?\*\//g,''),/Math\.random/);assert.match(i,/0\.035/);assert.match(i,/dt·0\.35/);
});
