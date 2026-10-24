// "The engine carries the sky", PR 2: starVisual + the boom. Pure, replayable, labelled SEEDED (stepped test universe).
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {boomState,boomSkyTerm,boomsAt,supernovaEvents,remnantFor,boomLuminosity,BOOM,BOOM_LABEL} from '../lib/universe/boom.mjs';
import {starVisual,engineChannels,STAR_VISUAL} from '../lib/universe/star-visual.mjs';
import {blackBodyToRGB,coronaParams} from '../lib/universe/genesis-sun.mjs';
import {createWorldField,stepWorldField} from '../lib/universe/world-field.mjs';
const real=genesis(JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url),'utf8')));
const S12={id:'s',mass_solar:12,temperature_k:20000,luminosity:12**3.5},S20={id:'b',mass_solar:20,temperature_k:25000,luminosity:20**3.5},S3={id:'c',mass_solar:3,temperature_k:6000,luminosity:3**3.5};
test('starVisual: colour is the ported blackbody, corona the ported params, shimmer = chaos, pulse = coherence within +/- 4%',()=>{
 const v=starVisual(S12,{chaos:0.7,coherence:0.9,tick:10},2);assert.deepEqual(v.colorRGB,blackBodyToRGB(20000));
 assert.equal(v.corona.intensity,coronaParams(20000).intensity);assert.equal(v.corona.noiseScale,coronaParams(20000).noiseScale);assert.equal(v.corona.shimmer,0.7);
 assert.ok(Math.abs(v.pulse-1)<=STAR_VISUAL.pulseAmp+1e-12);assert.ok(starVisual(S12,{coherence:1}).pulse>starVisual(S12,{coherence:0}).pulse);
 assert.ok(starVisual(S12,{chaos:1,tick:5}).corona.phase>starVisual(S12,{chaos:0,tick:5}).corona.phase);
});
test('starVisual is pure and identical for the same inputs; apparent size follows luminosity and distance',()=>{
 const a=starVisual(S12,{chaos:.3,coherence:.4,tick:7},1),b=starVisual(S12,{chaos:.3,coherence:.4,tick:7},1);assert.deepEqual(a,b);
 assert.ok(starVisual(S20,{},3).apparentSize>starVisual(S3,{},3).apparentSize);assert.ok(starVisual(S12,{},1).apparentSize>starVisual(S12,{},8).apparentSize);
});
test('starVisual reads the stepped world field channels (same seed + ticks = same visual)',()=>{
 const init=n=>({id:'grassland',h:.2});const mk=()=>{const F=createWorldField({seed:'s',W:16,H:8,initial:init});for(let i=0;i<300;i++)stepWorldField(F,1);return F;};
 assert.deepEqual(starVisual(S12,engineChannels(mk()),2),starVisual(S12,engineChannels(mk()),2));
});
test('a remnant: neutron star keeps a small pulsing point, a black hole none',()=>{
 assert.ok(starVisual({...S12,luminosity:0,remnant:'neutron_star'},{coherence:.5}).brightness>0);assert.equal(starVisual({...S20,luminosity:0,remnant:'black_hole'}).brightness,0);
});
test('boom remnant follows the spec mass thresholds (>8 neutron star, >15 black hole, else none)',()=>{
 assert.equal(remnantFor(8),null);assert.equal(remnantFor(8.1),'neutron_star');assert.equal(remnantFor(15),'neutron_star');assert.equal(remnantFor(15.1),'black_hole');
 assert.equal(boomState(S12,10,500).remnantType,'neutron_star');assert.equal(boomState(S20,10,500).remnantType,'black_hole');assert.equal(boomState(S3,10,500).phase,'none');
});
test('boom phases are in order, boundaries monotonic in tick, intensity peaks in the flash and the shell expands ease-out',()=>{
 const order=['none','flash','shell','fade','remnant'];let last=0,peakI=0,peakPhase='',lastR=-1;
 for(let t=0;t<=10+BOOM.lifeTicks*1.2;t+=0.25){const s=boomState(S12,10,t);const k=order.indexOf(s.phase);assert.ok(k>=last,'phase never goes back');last=k;assert.ok(s.shellFrac>=lastR);lastR=s.shellFrac;if(s.intensity>peakI){peakI=s.intensity;peakPhase=s.phase;}}
 assert.equal(peakPhase,'flash');assert.equal(boomState(S12,10,9.99).phase,'none');assert.equal(boomState(S12,10,10).phase,'flash');
 assert.equal(boomState(S12,10,10+BOOM.lifeTicks*BOOM.flashEnd+1e-9).phase,'shell');assert.equal(boomState(S12,10,10+BOOM.lifeTicks*BOOM.shellEnd+1e-9).phase,'fade');assert.equal(boomState(S12,10,10+BOOM.lifeTicks*BOOM.fadeEnd+1e-9).phase,'remnant');
 const mid=boomState(S12,10,10+BOOM.lifeTicks*0.2).shellFrac,quarter=boomState(S12,10,10+BOOM.lifeTicks*0.1).shellFrac;assert.ok(mid-quarter<quarter,'ease-out: early growth is faster than late growth');
 assert.ok(boomState(S12,10,10+BOOM.lifeTicks*0.6).intensity<=boomState(S12,10,10+BOOM.lifeTicks*0.3).intensity);
});
test('the flash is pushed toward white-blue and the shell cools toward ember',()=>{
 const bb=blackBodyToRGB(20000),f=boomState(S12,0,BOOM.lifeTicks*BOOM.flashEnd*0.99).colorRGB;assert.ok(f[0]>=bb[0]-1e-9);
 const late=boomState(S12,0,BOOM.lifeTicks*0.7).colorRGB;assert.ok(late[0]>late[2],'cooled: red above blue');
});
test('the boom replays from history identically, from the star numbers alone, and writes nothing',()=>{
 let g=real;for(let i=0;i<400&&!supernovaEvents(g).length;i++)g=grow(g,g.tick+1);
 const ev=supernovaEvents(g);assert.ok(ev.length>0,'the stepped universe has a supernova');
 const snap=JSON.stringify(g);const t=ev[0].tick+5;const a=boomsAt(g,t),b=boomsAt(JSON.parse(snap),t);assert.deepEqual(a,b);assert.equal(JSON.stringify(g),snap);
 assert.equal(a[0].state.label,BOOM_LABEL);assert.equal(BOOM_LABEL,'SEEDED (stepped test universe)');
 const st=g.stars.find(s=>s.id===ev[0].star);assert.ok(st.remnant);assert.equal(st.luminosity,0);assert.ok(boomLuminosity(st)>0,'remnant luminosity falls back to the engine relation mass^3.5');
});
test('the sky term is 0 before the event, peaks in the flash, falls with distance, and is pale by day',()=>{
 assert.equal(boomSkyTerm(S12,10,9,1),0);const flash=10+BOOM.lifeTicks*BOOM.flashEnd*0.999;const later=10+BOOM.lifeTicks*0.5;
 const a=boomSkyTerm(S12,10,flash,5),b=boomSkyTerm(S12,10,later,5);assert.ok(a>b&&b>0);assert.ok(boomSkyTerm(S12,10,flash,3)>=boomSkyTerm(S12,10,flash,30));
 assert.ok(boomSkyTerm(S12,10,flash,5,1)<a*0.3);assert.ok(boomSkyTerm(S12,10,flash,0.05)<=BOOM.skyCap+1e-12);
});
test('no clock and no Math.random in the new modules',()=>{
 for(const f of ['boom','star-visual']){const src=readFileSync(new URL('../lib/universe/'+f+'.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src),f);}
});
