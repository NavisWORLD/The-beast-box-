import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {boomStage,stageBooms,phaseT,limbPoint,PHASES} from '../lib/universe/event-staging.mjs';
import {boomState,BOOM} from '../lib/universe/boom.mjs';
import {VL_EVENTS} from '../lib/universe/vislife-look-data.mjs';
const S12={id:'s',mass_solar:12,temperature_k:20000,luminosity:12**3.5};
const S3={id:'c',mass_solar:3,temperature_k:6000,luminosity:3**3.5};
test('pack phase names and edges equal boom.mjs (the engine wins)',()=>{
 assert.deepEqual(VL_EVENTS.phases,[...PHASES]);const e=VL_EVENTS.timing.phase_edges_u;assert.deepEqual(e,[0,BOOM.flashEnd,BOOM.shellEnd,BOOM.fadeEnd,1]);assert.equal(VL_EVENTS.timing.life_ticks,BOOM.lifeTicks);
});
test('the stage follows the engine phases flash, shell, fade, remnant, and is null before / for a star that cannot explode',()=>{
 assert.equal(boomStage(S12,10,5,1),null);assert.equal(boomStage(S3,0,10,1),null);
 const seen=[];for(let k=0;k<=70;k++){const s=boomStage(S12,0,k,1);if(s&&seen[seen.length-1]!==s.phase)seen.push(s.phase);assert.equal(s.phase,boomState(S12,0,k).phase);}
 assert.deepEqual(seen,[...PHASES]);
});
test('phaseT is the local position inside the engine phase',()=>{assert.equal(phaseT('flash',0),0);assert.ok(Math.abs(phaseT('shell',(BOOM.flashEnd+BOOM.shellEnd)/2)-0.5)<1e-9);assert.equal(phaseT('remnant',1),1);});
test('the ring grows with the engine shellFrac and strength falls off with 1/d^2 (distance), paler by day',()=>{
 const a=boomStage(S12,0,10,1),b=boomStage(S12,0,10,8),c=boomStage(S12,0,10,1,1);
 assert.ok(b.skyTerm<a.skyTerm&&b.ring.alpha<a.ring.alpha&&b.bloom.gain<a.bloom.gain);assert.ok(c.skyTerm<a.skyTerm);
 const r=[5,15,25].map(k=>boomStage(S12,0,k,12).ring.angDeg);assert.ok(r[0]<r[1]&&r[1]<r[2]);assert.ok(r[2]<=40);
 assert.equal(a.shellFrac,boomState(S12,0,10).shellFrac);
});
test('lit water mix follows the pack table with intensity, bounded, and a far boom lights less',()=>{
 const a=boomStage(S12,0,1,0.5),b=boomStage(S12,0,1,12);assert.ok(a.waterLit.mix<=0.55+1e-9&&a.waterLit.mix>b.waterLit.mix);assert.equal(a.waterLit.underMax,0.12);
});
test('orbit bloom radius by phase is the pack table',()=>{for(const [k,p] of [[0,'flash'],[10,'shell'],[35,'fade'],[60,'remnant']]){const s=boomStage(S12,0,k,1);assert.equal(s.phase,p);assert.equal(s.bloom.radiusFrac,VL_EVENTS.mood_31.orbit_inset_bloom.bloom_radius_frac_of_globe_by_phase[p]);}});
test('colours are finite 0..1-ish linear triples',()=>{for(let k=0;k<=64;k+=4){const s=boomStage(S12,0,k,1);for(const c of [s.ring.outer,s.ring.inner,s.bloom.colour]){assert.equal(c.length,3);for(const v of c)assert.ok(Number.isFinite(v)&&v>=0&&v<=1.2);}}});
test('deterministic: two runs deep-equal; isolation: staging never mutates the star',()=>{
 const run=()=>{const o=[];for(let k=0;k<=64;k++)o.push(boomStage(S12,3,k+3,1.7,0.3));return o;};const snap=JSON.stringify(S12);
 assert.deepEqual(run(),run());assert.equal(JSON.stringify(S12),snap);
});
test('stageBooms picks the strongest; limbPoint is a unit vector perpendicular to the camera',()=>{
 const l=[{star:S12,eventTick:0,distance:6,dir:[1,0,0]},{star:S12,eventTick:0,distance:1,dir:[0,1,0]}];const r=stageBooms(l,5);assert.deepEqual(r.dir,[0,1,0]);assert.equal(stageBooms([],5),null);
 const p=limbPoint([0.6,0.8,0],[0,0,1]);assert.ok(Math.abs(Math.hypot(...p)-1)<1e-9&&Math.abs(p[2])<1e-9);assert.equal(limbPoint([0,0,1],[0,0,1]),null);
});
test('no clock and no randomness in the source',()=>{const s=fs.readFileSync(new URL('../lib/universe/event-staging.mjs',import.meta.url),'utf8').replace(/^\s*\/\/.*$/gm,'');assert.ok(!/Date\.now|new Date|Math\.random|performance\.now|requestAnimationFrame/.test(s));});
