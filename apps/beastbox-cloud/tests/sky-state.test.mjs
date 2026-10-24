// "The engine carries the sky", PR 4: skyAt, shared terminator/twilight/moon-phase, land state, accuracy traces, isolation.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {skyAt,SKY,terminatorWidth,terminatorWeight,skyNightFactor,twilightBandAt,twilightWeight,moonPhaseDiffuse,moonPhase,starAlpha,weberVisible,byAtmo,NIGHT_OPS_SHA256} from '../lib/universe/sky-state.mjs';
import {snowCover,snowAmount,wetnessTarget,wetnessStep,groundTint,wetSheen,LAND} from '../lib/universe/land-state.mjs';
import {PLANET_SHADING} from '../lib/universe/planet-shading.mjs';
import {blackBodyToRGB,sunDirAt,DAY_LENGTH_TICKS} from '../lib/universe/genesis-sun.mjs';
import {starVisual} from '../lib/universe/star-visual.mjs';
import {boomState,boomSkyTerm,remnantFor} from '../lib/universe/boom.mjs';
import {createWorldField,stepWorldField} from '../lib/universe/world-field.mjs';
const here=p=>new URL(p,import.meta.url);const glslTs=readFileSync(here('../lib/universe/planet-glsl.ts'),'utf8');
const real=genesis(JSON.parse(readFileSync(here('../public/spark/ibm-marrakesh-reality-probe-20261009.json'),'utf8')));
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const dirE=e=>[Math.sqrt(1-e*e),e,0];
test('nightFactor endpoints: 1 at/below -w, 0 at/above 1.6w, monotone, midpoint matches the pack table (0.67 at the horizon, w=.015)',()=>{
 for(const atmo of [0,0.3,0.55,0.85,1]){const w=terminatorWidth(atmo);assert.equal(skyNightFactor(-w,w),1);assert.equal(skyNightFactor(-5*w,w),1);assert.equal(skyNightFactor(1.6*w,w),0);assert.equal(skyNightFactor(0.9,w),0);
  let last=2;for(let i=-20;i<=40;i++){const nf=skyNightFactor(i*w/10,w);assert.ok(nf<=last+1e-12);last=nf;}}
 assert.ok(Math.abs(skyNightFactor(0,0.015)-0.67)<0.01);assert.ok(/^[0-9a-f]{64}$/.test(NIGHT_OPS_SHA256));
});
test('terminator width is wired per planet from atmosphere: the generated shader uses mix(0.015,0.12,uAtmo) and every type feeds uAtmo from its own atmo_amount',()=>{
 assert.ok(glslTs.includes('mix(0.015, 0.12, uAtmo)'));assert.ok(!/float width = 0\.\d+;/.test(glslTs));
 assert.equal(terminatorWidth(0),0.015);assert.equal(terminatorWidth(1),0.12);
 const src=readFileSync(here('../lib/universe/planet-body-three.ts'),'utf8');assert.ok(src.includes('uAtmo:{value:sh.atmo_amount}'));
 for(const [t,v] of Object.entries(PLANET_SHADING)){const a=v.shading.atmo_amount;assert.ok(a>=0&&a<=1,t);}
});
test('twilight band: the JS function equals the planet-glsl twilightBand (formula text and numbers) and its colour is the shared planet colour',()=>{
 const m=glslTs.match(/vec3 twilightBand\(vec3 N_geo, vec3 L, float width, vec3 twilightColor, float strength\)\{\s*float x = dot\(N_geo, L\) \/ \(width \* ([0-9.]+) \+ ([0-9e.\-]+)\);\s*return twilightColor \* exp\(-x \* x\) \* strength;/);
 assert.ok(m,'planet-glsl twilightBand text changed');assert.equal(+m[1],1.4);assert.equal(+m[2],1e-4);
 const glsl=(elev,width,c,s)=>{const x=elev/(width*+m[1]+ +m[2]);return c.map(k=>k*Math.exp(-x*x)*s);};
 for(const [t,v] of Object.entries(PLANET_SHADING)){const a=v.shading.atmo_amount,w=terminatorWidth(a);for(const e of [-0.2,-0.05,0,0.03,0.4]){const A=twilightBandAt(e,w,v.shading.twilight_color,0.5*a),B=glsl(e,w,v.shading.twilight_color,0.5*a);assert.deepEqual(A,B,t);}}
 const sky=skyAt({sunDir:dirE(0),atmosphere:0.85,starTempK:5800,twilightColor:PLANET_SHADING.temperate.shading.twilight_color});
 assert.deepEqual(sky.twilight.color,twilightBandAt(0,terminatorWidth(0.85),PLANET_SHADING.temperate.shading.twilight_color,0.85));assert.ok(sky.twilight.weight>0.8);
 assert.equal(skyAt({sunDir:dirE(0),atmosphere:0,starTempK:5800}).twilight.weight,0);
});
test('moon phase: new at the sun, full opposite, quarter between; one function shared with the GLSL (constants re-read from planet-glsl)',()=>{
 assert.ok(/1\.0 \+ 0\.45 \* exp\(-acos\(cosA\) \/ 0\.10\)/.test(glslTs)&&/2\.0 \* ndl \/ \(ndl \+ ndv \+ 1e-3\)/.test(glslTs));
 const sun=[1,0,0];const nw=moonPhase(sun,[1,0,0]),fl=moonPhase(sun,[-1,0,0]),qt=moonPhase(sun,[0,0,1]);
 assert.ok(nw.litFraction<1e-9&&fl.litFraction>0.999&&Math.abs(qt.litFraction-0.5)<1e-9);assert.ok(fl.brightness>qt.brightness&&qt.brightness>nw.brightness);assert.ok(nw.brightness<0.02);
 let last=2;for(let a=0;a<=Math.PI;a+=Math.PI/12){const p=moonPhase(sun,[-Math.cos(a),0,Math.sin(a)]);assert.ok(p.litFraction<=last+1e-9);last=p.litFraction;}
 assert.equal(moonPhaseDiffuse([1,0,0],[-1,0,0],[1,0,0]),0);
});
test('star visibility: brightest first, airless always, none in full day on a thick sky, monotone in nightFactor',()=>{
 assert.equal(starAlpha(0,0.5,0),1);assert.equal(starAlpha(0,1,0.01),1);assert.equal(starAlpha(0,1,0.85),0);assert.equal(starAlpha(1,0,0.85),1);
 for(const a of [0.3,0.55,0.85]){assert.ok(starAlpha(0.5,1,a)>=starAlpha(0.5,0,a));let l=-1;for(let n=0;n<=1.001;n+=0.1){const v=starAlpha(n,0.5,a);assert.ok(v>=l);l=v;}}
 assert.ok(weberVisible(0.05,1.0)&&!weberVisible(0.01,1.0));
});
test('sky continuity over a full engine day: gradients move smoothly, noon is blue, midnight is the night colour, dusk goes gold',()=>{
 let prev=null,maxJump=0,minNf=1,maxNf=0;const T=DAY_LENGTH_TICKS;
 for(let i=0;i<=T;i++){const s=skyAt({sunDir:sunDirAt(i/T*Math.PI*2),atmosphere:0.85,starTempK:5800});
  const cur=[...s.zenith,...s.horizon,s.nightFactor];if(prev)for(let k=0;k<7;k++)maxJump=Math.max(maxJump,Math.abs(cur[k]-prev[k]));prev=cur;minNf=Math.min(minNf,s.nightFactor);maxNf=Math.max(maxNf,s.nightFactor);}
 assert.ok(maxJump<0.02,'jump '+maxJump);assert.equal(minNf,0);assert.equal(maxNf,1);
 const noon=skyAt({sunDir:[0,1,0],atmosphere:0.85,starTempK:5800}),night=skyAt({sunDir:[0,-1,0],atmosphere:0.85,starTempK:5800}),dusk=skyAt({sunDir:dirE(0.02),atmosphere:0.85,starTempK:5800});
 assert.ok(noon.zenith[2]>noon.zenith[0]*2);assert.deepEqual(night.zenith,SKY.nightZenith);assert.ok(dusk.horizon[0]>dusk.horizon[2]);
 assert.deepEqual(skyAt({sunDir:[0,1,0],atmosphere:0,starTempK:5800}).zenith,SKY.nightZenith,'airless day is a black sky');
});
test('star colour tints the sky: a red dwarf sky is warmer than a blue star sky; same inputs twice = same sky',()=>{
 const a=skyAt({sunDir:[0,1,0],atmosphere:0.85,starTempK:3000}),b=skyAt({sunDir:[0,1,0],atmosphere:0.85,starTempK:25000});assert.ok(a.horizon[0]/a.horizon[2]>b.horizon[0]/b.horizon[2]);
 assert.equal(JSON.stringify(skyAt({sunDir:dirE(0.1),atmosphere:0.5,starTempK:6000})),JSON.stringify(skyAt({sunDir:dirE(0.1),atmosphere:0.5,starTempK:6000})));
});
test('boom term in the sky: 0 before the event, peaks in the flash, pale by day, ambient for the rig; replay identical',()=>{
 const star={id:'s',mass_solar:12,temperature_k:20000,luminosity:12**3.5};const mk=(tick,e)=>skyAt({sunDir:dirE(e),atmosphere:0.85,starTempK:5800,tick,booms:[{star,eventTick:100,distance:2,dir:[0,0.5,0.8]}]});
 assert.equal(mk(99,-0.5).booms.length,0);const f=mk(101,-0.5),sh=mk(130,-0.5),fd=mk(150,-0.5);
 assert.ok(f.booms[0].phase==='flash'&&f.booms[0].strength>=sh.booms[0].strength&&sh.booms[0].strength>=fd.booms[0].strength);assert.ok(f.booms[0].rays&&!sh.booms[0].rays);assert.ok(f.booms[0].radiusDeg>sh.booms[0].radiusDeg);
 assert.ok(mk(101,0.8).booms[0].strength<f.booms[0].strength*0.3,'pale by day');assert.ok(f.rig.ambient>SKY.nightAmbient&&f.rig.ambient<=SKY.nightAmbient*2);assert.equal(JSON.stringify(mk(130,-0.5)),JSON.stringify(mk(130,-0.5)));
 assert.equal(f.booms[0].label,'SEEDED (stepped test universe)');
 assert.equal(f.booms[0].strength,Math.min(1,boomSkyTerm(star,100,101,2,f.dayWeight)));
});
test('bodies: moon phase from the real sun direction, partner above/below horizon, neighbour star alpha, parent star visual',()=>{
 const star={id:'n',mass_solar:3,temperature_k:6000,luminosity:3**3.5};
 const s=skyAt({sunDir:[1,0,0],atmosphere:0.85,starTempK:5800,star,channels:{chaos:0.4,coherence:0.9,tick:5},bodies:[{id:'m1',kind:'moon',dir:[-0.5,0.8,0.1]},{id:'m2',kind:'moon',dir:[0.9,0.1,0]},{id:'p',kind:'partner',dir:[0,-1,0]},{id:'s2',kind:'neighbor',dir:[0,1,0],star,distance:50},{id:'sun',kind:'star',dir:[1,0.05,0],star,distance:1}]});
 const by=Object.fromEntries(s.bodies.map(b=>[b.id,b]));assert.ok(by.m1.phase.litFraction>by.m2.phase.litFraction);assert.equal(by.p.visible,false);assert.ok(by.m1.visible);
 assert.deepEqual(by.sun.visual,starVisual(star,{chaos:0.4,coherence:0.9,tick:5},1));assert.ok('alpha' in by.s2);
});
test('land accuracy traces: snow iff snowAmount > 0 (from recorded temperature), wetness 0 at baseline moisture, drying has hysteresis',()=>{
 for(const [type,T] of [['temperate',300],['temperate',200],['ice',150],['desert',250],['volcanic',100],['moon',50]]){const a=snowAmount(type,T);for(const ny of [0.2,0.5,0.95]){const c=snowCover({snowAmount:a,normalY:ny,rockiness:0.5,noise:0.5});assert.equal(c>0,a>0,type+T+ny);}}
 assert.equal(snowCover({snowAmount:0,normalY:1}),0);assert.ok(snowCover({snowAmount:0.5,normalY:1})>snowCover({snowAmount:0.5,normalY:0.5}));
 assert.ok(snowAmount('temperate',200)>snowAmount('temperate',280));
 assert.equal(wetnessTarget(0.4,0.4),0);assert.equal(wetnessTarget(0.3,0.4),0);assert.ok(wetnessTarget(0.5,0.4)>0&&wetnessTarget(0.9,0.4)===1);
 let w=1;const tgt=0;const half=Math.round(LAND.dryHalfLifeDay*DAY_LENGTH_TICKS);for(let i=0;i<half;i++)w=wetnessStep(w,tgt);assert.ok(Math.abs(w-0.5)<0.02);
 assert.equal(wetnessStep(0.2,0.6),0.6);assert.ok(wetnessStep(0.8,0.1)>0.1,'falls slowly, does not snap');
 const base=[0.1,0.3,0.2];assert.deepEqual(groundTint(base,{}),base.map(x=>x));assert.ok(groundTint(base,{wet:1})[1]<base[1]);assert.ok(groundTint(base,{cover:1})[0]>base[0]);
 assert.equal(wetSheen(0.1,0.8).on,0);assert.ok(wetSheen(1,0.8).roughness<0.8);
});
test('star table audit (spec TINY_UNIVERSE_SPEC body table): remnant thresholds, temperature from flux, luminosity = mass^3.5 as makeStar; no proven mismatch to fix',()=>{
 assert.equal(remnantFor(8),null);assert.equal(remnantFor(8.1),'neutron_star');assert.equal(remnantFor(15),'neutron_star');assert.equal(remnantFor(15.1),'black_hole');
 for(const s of real.stars){assert.ok(Math.abs(s.luminosity-+(s.mass_solar**3.5).toFixed(4))<1e-3);}
 for(const p of real.planets){const st=real.stars.find(s=>s.id===p.star);assert.ok(Math.abs(p.temperature_k-Math.round(278*(st.luminosity/p.orbit_au**2)**0.25))<=1);}
 const lum=[0.5,2,8,40,200],sz=lum.map(l=>starVisual({temperature_k:6000,luminosity:l},{},1).apparentSize);for(let i=1;i<sz.length;i++)assert.ok(sz[i]>=sz[i-1]);
});
test('isolation: engine JSON byte-identical with all sky/land visual state derived vs not',()=>{
 const u=grow(real,30);const before=JSON.stringify(u);const frozen=structuredClone(u);
 for(const st of u.stars)for(let i=0;i<40;i++)skyAt({sunDir:sunDirAt(i/40*6.283),atmosphere:0.6,starTempK:st.temperature_k,star:st,channels:{chaos:0.3,coherence:0.8,tick:i},tick:u.tick,bodies:[{id:'n',kind:'neighbor',dir:[0,1,0],star:st,distance:30}],booms:[{star:st,eventTick:u.tick-3,distance:3}]});
 snowCover({snowAmount:0.4});groundTint([0.1,0.2,0.3],{wet:0.5,cover:0.5});
 assert.equal(JSON.stringify(u),before);assert.deepEqual(u,frozen);
 const F1=createWorldField({seed:'iso',W:8,H:4,initial:()=>({id:'deep_ocean',h:-.2})}),F2=createWorldField({seed:'iso',W:8,H:4,initial:()=>({id:'deep_ocean',h:-.2})});
 for(let i=0;i<50;i++){stepWorldField(F1,1);stepWorldField(F2,1);skyAt({sunDir:F2.sunDir,atmosphere:0.5,starTempK:5800});}assert.deepEqual(F1.sunDir,F2.sunDir);
});
test('no clock and no Math.random in sky-state or land-state',()=>{for(const f of ['sky-state','land-state']){const src=readFileSync(here(`../lib/universe/${f}.mjs`),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src),f);}});
