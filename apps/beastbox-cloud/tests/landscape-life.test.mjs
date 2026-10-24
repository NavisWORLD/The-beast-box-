// Landscapes 3/3: the life layer's pure parts (home_landscape view field, roam targets by mode, resident goals). View-model only.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {seededLandscapes,withHomeLandscapes,homeLandscapeId,landscapeTargets,landscapeGoal,landscapeAnchors,landscapeSlots,angleBetween,LANDSCAPE_MODES,LANDSCAPE} from '../lib/universe/seeded-landscapes.mjs';
import {LANDSCAPE_LOOK as LOOK} from '../lib/universe/landscape-look-data.mjs';
const shard=JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url),'utf8'));
const real=genesis(shard);const g={...real,planets:real.planets.map(p=>({...p,habitability:0.9,water:0.4}))};const u=grow(g,40);
const L=seededLandscapes(u,{biomeAt:()=>'grassland'});
test('home_landscape is a view field: deterministic, a valid id, and u.life is untouched',()=>{
 const before=JSON.stringify(u);const a=withHomeLandscapes(u,L),b=withHomeLandscapes(u,L);assert.deepEqual(a,b);assert.equal(JSON.stringify(u),before);
 for(const l of a){const here=L.filter(x=>x.planet===l.planet);if(here.length)assert.ok(here.some(x=>x.id===l.home_landscape));else assert.equal(l.home_landscape,null);assert.ok(!('home_landscape' in (u.life.find(x=>x.id===l.id)||{})));}
 assert.equal(homeLandscapeId('s','k',[]),null);
});
test('the home pick draws only from its own key (another entry never changes it)',()=>{
 const two=[{id:'a',planet:'p'},{id:'b',planet:'p'},{id:'c',planet:'p'}];const x=homeLandscapeId('seed','res:Moss',two);for(let i=0;i<5;i++)homeLandscapeId('seed','res:Other'+i,two);assert.equal(homeLandscapeId('seed','res:Moss',two),x);
});
test('targets by mode: gather = ring + seats, shelter/sleep = the shelter anchor, empty = none',()=>{
 const ls=L[0],A=landscapeAnchors(ls),S=landscapeSlots(ls);
 assert.deepEqual(landscapeTargets(ls,'gather'),[A.play,...S.seats]);assert.deepEqual(landscapeTargets(ls,'shelter'),[A.shelter]);assert.deepEqual(landscapeTargets(ls,'sleep'),[A.shelter]);assert.deepEqual(landscapeTargets(ls,'empty'),[]);
 assert.equal(landscapeGoal(ls,'empty','res:x'),null);
});
test('resident goals are deterministic, inside the place, and the huddle is within 0.55 m of the shelter',()=>{
 const ls=L[0],A=landscapeAnchors(ls);const R=ls.radiusM/LANDSCAPE.worldRadiusM;
 for(const mode of ['gather','shelter','sleep']){for(const key of ['res:A','res:B','res:C','life:1']){const a=landscapeGoal(ls,mode,key,'s'),b=landscapeGoal(ls,mode,key,'s');assert.deepEqual(a,b);assert.ok(angleBetween(a.target,A.play)<=R*1.001,mode+key);assert.ok(a.arrive>0);}}
 for(const key of ['res:A','res:B','res:C','res:D']){const h=landscapeGoal(ls,'shelter',key,'s');assert.ok(angleBetween(h.target,A.shelter)<=0.55/LANDSCAPE.worldRadiusM+1e-9);}
 const diff=new Set(['A','B','C','D','E','F'].map(k=>landscapeGoal(ls,'shelter','res:'+k,'s').target.join()));assert.ok(diff.size>1,'huddle spreads, not one point');
});
test('rain spec: caps 220 desktop / 90 phone, dry zone 0.2 of the pad, drawn over the pad only',()=>{
 assert.equal(LOOK.rain.max_instances_desktop,220);assert.equal(LOOK.rain.max_instances_phone,90);assert.equal(LOOK.rain.sheltered_zone.cull_radius_frac_of_pad,0.2);
});
test('every mode has a goal rule and the life layer never reads a clock or Math.random',()=>{
 for(const m of LANDSCAPE_MODES)assert.ok(Array.isArray(landscapeTargets(L[0],m)));
 const src=readFileSync(new URL('../lib/universe/seeded-landscapes.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');assert.ok(!/Math\.random|Date\.now|performance\.now|new Date/.test(src));
});
