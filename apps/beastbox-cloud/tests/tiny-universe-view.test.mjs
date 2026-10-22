import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {grow} from '../lib/universe/tiny-universe.mjs';
import {biomeOf,starClass,lifeStage,entangledPairs,homeOf,hearthOf,zerefStar} from '../lib/universe/tiny-universe-view.mjs';
const g=JSON.parse(readFileSync(new URL('../public/universe/tiny-universe-genesis.json',import.meta.url),'utf8'));
test('bible mappings',()=>{assert.equal(biomeOf({temperature_k:900,water:0.2}),'ember');assert.equal(biomeOf({temperature_k:900,water:0.8}),'paper');assert.equal(biomeOf({temperature_k:200,water:0.5}),'glacier');assert.equal(biomeOf({temperature_k:300,water:0.9}),'jelly');assert.equal(biomeOf({temperature_k:234,water:0.9}),'glacier');assert.equal(biomeOf({temperature_k:300,water:0.5}),'sunflower');assert.equal(biomeOf({temperature_k:300,water:0.1}),'moss');
 assert.equal(starClass({mass_solar:0.5}),'Ember star');assert.equal(starClass({mass_solar:5}),'Lantern star');assert.equal(starClass({mass_solar:9}),'Storm-crowned star');assert.equal(starClass({mass_solar:9,remnant:'neutron_star'}),'the Clenched Heart');assert.equal(starClass({mass_solar:20,remnant:'black_hole'}),'the Quiet Door');
 assert.deepEqual([0.1,0.4,0.7,0.95].map(c=>lifeStage({complexity_norm:c})),['Glimmer','Drifters','Choirs','Dreamers']);});
test('view picks only engine bodies, deterministic',()=>{const u=grow(g,200);const ids=new Set(u.planets.map(p=>p.id));
 for(const[a,b]of entangledPairs(u)){assert.ok(ids.has(a)&&ids.has(b));}assert.deepEqual(entangledPairs(u),entangledPairs(grow(g,200)));
 assert.ok(ids.has(homeOf(u)));if(u.life.length)assert.equal(homeOf(u),hearthOf(u));assert.ok(u.stars.some(s=>s.id===zerefStar(u)));assert.equal(u.growth_label.startsWith('SIMULATED'),true);});
test('universe page labels and nav',()=>{const c=readFileSync(new URL('../components/tiny-universe-view.tsx',import.meta.url),'utf8');assert.match(c,/GENESIS_LABEL/);assert.match(c,/GROWTH_LABEL/);assert.doesNotMatch(c,/\bAI\b/);
 assert.match(readFileSync(new URL('../lib/site-nav.ts',import.meta.url),'utf8'),/href:'\/universe'/);});
import {genesis,COMPLEXITY_K,derivePairs} from '../lib/universe/tiny-universe.mjs';
const shard=JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url),'utf8'));
test('engine additions: pairs, complexity_norm, stage, scars',()=>{const g0=genesis(shard);assert.deepEqual(g0.pairs,derivePairs(g0));assert.equal(g0.pairs.length,Math.floor(g0.planets.length/2));
 const seen=new Set();for(const p of g0.pairs){assert.ok(!seen.has(p.a)&&!seen.has(p.b));seen.add(p.a);seen.add(p.b);assert.equal(p.E,g0.entanglement_E);}
 const u=grow(g0,200);for(const l of u.life){assert.ok(l.complexity_norm>=0&&l.complexity_norm<1);assert.equal(l.complexity_norm,+(1-Math.exp(-l.complexity/COMPLEXITY_K)).toFixed(4));assert.ok(['Glimmer','Drifters','Choirs','Dreamers'].includes(l.stage));assert.equal(l.scarred,l.scars>0);}
 const old=grow({...g0,pairs:undefined},200);assert.deepEqual(old.planets,u.planets);assert.deepEqual(old.stars,u.stars);});
test('storm sample has storms',()=>{const s=JSON.parse(readFileSync(new URL('../public/universe/tiny-universe-storm-sample.json',import.meta.url),'utf8'));assert.ok(s.storms.length>0);for(const k of ['planet','intensity','lifetime','born'])assert.ok(k in s.storms[0]);});
test('scars count when a storm hits a life world',()=>{const g={...genesis(shard)};let u=grow(g,1);u.life=[{id:'life-x',type:'life',planet:u.planets[0].id,complexity:1,diversity:3,born:0,traits:{hue:0,motility:0,sociality:0}}];u.storms=[{id:'s',type:'storm',planet:u.planets[0].id,intensity:0.5,lifetime:99,born:u.tick}];const n=grow(u,1);const L=n.life.find(l=>l.id==='life-x');if(L){assert.equal(L.scars,1);assert.equal(L.scarred,true);}});
import {threadFrame,stormPhase,hearthFrame} from '../lib/universe/tiny-universe-view.mjs';
test('per-pair SIMULATED sim_E, hardware E kept',()=>{const u=grow(genesis(shard),30);const v=new Set();for(const p of u.pairs){assert.equal(p.E,u.entanglement_E);assert.equal(p.E_source,'RECORDED_IBM_HARDWARE');assert.equal(p.sim_source,'SIMULATED');assert.ok(p.sim_E<=1&&p.sim_E>=-1);v.add(p.sim_E);}assert.ok(v.size>1);assert.deepEqual(grow(genesis(shard),30).pairs,u.pairs);
 assert.deepEqual(threadFrame({sim_E:1},0),{key:'thread.e3.f0',alpha:1});assert.equal(threadFrame({sim_E:0.1},5).key,'thread.e0.f1');assert.equal(threadFrame({sim_E:0.1},0).alpha,0.2);
 assert.equal(stormPhase({born:10,lifetime:1},10),'peak');assert.equal(stormPhase({born:0,lifetime:10},1),'spawn');assert.equal(stormPhase({born:10,lifetime:1},11),'fade');assert.equal(stormPhase({born:0,lifetime:10},5),'peak');
 const t=grow(genesis(shard),200);const h=t.planets.find(p=>p.id===hearthOf(t));assert.equal(hearthFrame(t,h),'hearth.living');});
