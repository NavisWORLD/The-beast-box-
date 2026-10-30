// Visual Life Pass, B2: caustics. One wave function, pack depth/sun rules, GLSL mirror agrees with the CPU, calm and night limits, determinism, no clock.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {CAUSTIC_GATE_GLSL,causticLite,CAUSTIC_LITE_GLSL,CAUSTIC,CAUSTIC_GLSL,CAUSTIC_TAP_GLSL,causticFocus,causticPattern,causticSun,causticDepth,causticColour,causticAt,tangents} from '../lib/universe/caustics.mjs';
import {SEA,SEA_GLSL,waveHeightAt,seaFrom} from '../lib/universe/sea-state.mjs';
import {createWorldField,stepWorldField} from '../lib/universe/world-field.mjs';
const dirs=[[0,1,0],[1,0,0],[0,0,1],[0.6,0.64,0.48],[-0.3,0.5,0.81240384],[0.1,-0.9,0.42]].map(v=>{const l=Math.hypot(...v);return v.map(x=>x/l);});
const glsl=new Function('clamp','max',CAUSTIC_GLSL.replace(/float causticFocus\(([^)]*)\)\{/,(m,a)=>'return function('+a.replace(/float /g,'')+'){').replace(/float /g,'let ').replace(/\n\}$/,'\n}'))(Math.min&&((v,a,b)=>Math.min(b,Math.max(a,v))),Math.max);
const sea=(storm=.5,wind=.5)=>({dir:.7,wind,storm,amp:(SEA.ampBase+SEA.ampStorm*storm)*(.35+.65*wind),chop:.25+.75*storm,whitecap:.5});
test('GLSL focus agrees with the CPU focus on many heights, amps and chops',()=>{
 for(const amp of [.004,.012,.05])for(const chop of [.25,.6,1])for(const h of [[0,0,0,0,0],[.001,.002,-.001,.0005,.003],[-.01,.01,.02,-.02,.0]]){
  const a=causticFocus(...h,amp,chop),b=glsl(...h,amp,chop);assert.ok(Math.abs(a-b)<1e-9,`${a} vs ${b}`);}
});
test('the shader tap uses the same constants and the same wave function text; ES 1.00 safe',()=>{
 assert.ok(CAUSTIC_TAP_GLSL.includes(CAUSTIC.eps.toFixed(6)));assert.ok(CAUSTIC_TAP_GLSL.includes('seaWaveHeight('));assert.ok(SEA_GLSL.includes('float seaWaveHeight('));
 assert.ok(CAUSTIC_TAP_GLSL.includes(CAUSTIC.decayM.toFixed(3)));assert.ok(!/\bint\b|\bfor\b|\buvec|\bin\b/.test(CAUSTIC_GLSL+CAUSTIC_TAP_GLSL.replace(/vec3/g,'')));
});
test('pattern is 0..1, sharp (varies over the surface) and moves with engine time',()=>{
 const s=sea();let lo=1,hi=0,moved=false;for(const d of dirs)for(let t=0;t<30;t+=.7){const p=causticPattern(s,d,t);assert.ok(p>=0&&p<=1);lo=Math.min(lo,p);hi=Math.max(hi,p);if(Math.abs(p-causticPattern(s,d,0))>1e-3)moved=true;}
 assert.ok(hi-lo>.15,'contrast '+(hi-lo));assert.ok(moved);
});
test('depth fall-off follows the pack rule: 1 at the surface, decays, 0 at the 30 m cutoff; sun gate zero at the horizon, night multiplier at night',()=>{
 assert.equal(causticDepth(0),1);assert.ok(causticDepth(2)<causticDepth(1));assert.equal(causticDepth(CAUSTIC.cutoffM),0);assert.equal(causticDepth(80),0);
 assert.equal(causticSun(0,0),0);assert.equal(causticSun(.35,0),1);assert.ok(causticSun(.18,0)<1);assert.equal(causticSun(-.3,1),CAUSTIC.nightMul);assert.equal(causticSun(-.3,0),0);
 const c0=causticColour(0),c15=causticColour(15);assert.deepEqual(c0,[1,1,1]);assert.ok(c15[0]<c0[0]);assert.ok(c15[2]>=.7);
});
test('caustics vanish with the sun and with depth, and show on a sunlit shallow',()=>{
 const s=sea(),d=dirs[3];let best=0;for(let t=0;t<40;t+=.5)best=Math.max(best,causticAt(s,d,t,.5,.6,0));assert.ok(best>0.1);
 assert.equal(causticAt(s,d,3,.5,0,0),0);assert.equal(causticAt(s,d,3,40,.6,0),0);
});
test('same engine ticks twice = the same caustics; isolation: the world field is untouched',()=>{
 const mk=()=>{const F=createWorldField({seed:'caus',W:16,H:8,initial:()=>({id:'deep_ocean',h:-.2})});for(let i=0;i<30;i++)stepWorldField(F,.25);return F;};
 const a=mk(),b=mk();const before=JSON.stringify([...a.height]);const sa=seaFrom(a),sb=seaFrom(b);const ta=a.tick/4+a.clock.alpha/4,tb=b.tick/4+b.clock.alpha/4;
 const va=dirs.map(d=>causticAt(sa,d,ta,1,.4,0)),vb=dirs.map(d=>causticAt(sb,d,tb,1,.4,0));assert.deepEqual(va,vb);assert.equal(JSON.stringify([...a.height]),before);assert.deepEqual(JSON.parse(JSON.stringify(a.S)),JSON.parse(JSON.stringify(b.S)));
});
test('tangent basis is orthonormal, including at the poles',()=>{for(const d of dirs){const [a,b]=tangents(d);const dot=(x,y)=>x[0]*y[0]+x[1]*y[1]+x[2]*y[2];assert.ok(Math.abs(dot(a,d))<1e-9&&Math.abs(dot(b,d))<1e-9&&Math.abs(dot(a,b))<1e-9);assert.ok(Math.abs(Math.hypot(...a)-1)<1e-9);}});
test('no clock and no Math.random in caustics',()=>{const src=readFileSync(new URL('../lib/universe/caustics.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src));void waveHeightAt;});
test('light mode: one-tap caustics agree with their GLSL text and stay 0..1',()=>{
 const g=new Function('clamp','max',CAUSTIC_LITE_GLSL.replace(/float causticLite\(([^)]*)\)\{/,(m,a)=>'return function('+a.replace(/float /g,'')+'){').replace(/float /g,'let ').replace(/\}$/,'}'))((v,a,b)=>Math.min(b,Math.max(a,v)),Math.max);
 for(const amp of [.004,.05])for(const h of [-.06,-.01,0,.01,.06]){const a=causticLite(h,amp),b=g(h,amp);assert.ok(Math.abs(a-b)<1e-9&&a>=0&&a<=1);}
});
test('GLSL sun gate text agrees with the CPU gate table (stops built from the same pack data)',()=>{
 const js=CAUSTIC_GATE_GLSL.replace(/float causticGate\(float s\)\{/,'return function(s){').replace(/float /g,'let ');
 const g=new Function('mix',js)((a,b,t)=>a+(b-a)*t);
 for(const s of [-.4,0,.01,.05,.1,.18,.27,.35,.7,1])assert.ok(Math.abs(g(s)-causticSun(s,0))<1e-9,'s='+s+' '+g(s)+' vs '+causticSun(s,0));
});
