import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {seededGrowthNodes} from '../lib/universe/seeded-growth-nodes.mjs';
import {seededLandscapes,landscapeMode,landscapeAnchors,landscapeSlots,landscapeHomeWorld,lampLevel,nightT,landscapeZoom,landscapeNotice,landscapeTapLine,angleBetween,dirOf,LANDSCAPE,LANDSCAPE_LABEL,LANDSCAPE_KINDS,LANDSCAPE_MODES,KIND_BY_BIOME,HOME_WORLD_LANDSCAPE_LABEL} from '../lib/universe/seeded-landscapes.mjs';
import {LANDSCAPE_NAMES} from '../lib/universe/landscape-names-data.mjs';
import {lwStream} from '../lib/universe/living-world.mjs';
const J=f=>JSON.parse(readFileSync(new URL(f,import.meta.url),'utf8'));
const shard=J('../public/spark/ibm-marrakesh-reality-probe-20261009.json');
const real=genesis(shard);
// The recorded genesis has one habitable planet (home, .17 < .35, glacier). Tests also use the same genesis with every planet made habitable and land-bearing.
const g={...real,planets:real.planets.map(p=>({...p,habitability:0.9,water:0.4}))};
const grass=()=>'grassland';
const u40=grow(g,40);

test('determinism: two calls deep-equal, names identical',()=>{
 const a=seededLandscapes(g,{biomeAt:grass}),b=seededLandscapes(structuredClone(g),{biomeAt:grass});assert.ok(a.length>=1);assert.deepEqual(a,b);assert.deepEqual(a.map(x=>x.name),b.map(x=>x.name));
 assert.deepEqual(seededLandscapes(real),seededLandscapes(structuredClone(real)));
});
test('labels: every landscape SEEDED; genesis and growth_label untouched',()=>{
 const before=JSON.stringify(u40);const a=seededLandscapes(u40,{biomeAt:grass});
 for(const l of a){assert.equal(l.label,'SEEDED');assert.equal(l.type,'landscape');assert.ok(LANDSCAPE_KINDS.includes(l.kind));}
 assert.equal(LANDSCAPE_LABEL,'SEEDED');assert.equal(JSON.stringify(u40),before);assert.equal(u40.growth_label,'SIMULATED (Rigetti Bell simulator, not hardware)');
 assert.ok(/RECORDED_IBM_HARDWARE/.test(JSON.stringify(g.source)+JSON.stringify(g.pairs?.[0]??{})));
});
test('isolation: bodies byte-identical with landscapes computed or not; growth nodes unchanged',()=>{
 const pick=u=>JSON.stringify({stars:u.stars,planets:u.planets,storms:u.storms,life:u.life,pairs:u.pairs});
 const off=pick(u40);const copy=structuredClone(u40);const nodesBefore=JSON.stringify(seededGrowthNodes(copy));
 seededLandscapes(copy,{biomeAt:grass});seededLandscapes(copy);
 assert.equal(pick(copy),off);assert.equal(JSON.stringify(copy),JSON.stringify(u40));assert.equal(JSON.stringify(seededGrowthNodes(copy)),nodesBefore);
 assert.equal(JSON.stringify(grow(g,25)),JSON.stringify(grow({...real,planets:real.planets.map(p=>({...p,habitability:0.9,water:0.4}))},25)));
});
test('gates: hostile biome none; grassland >= 1; ocean-world, low habitability and water>=0.9 get none; separation holds',()=>{
 const hostile=seededLandscapes({...g,planets:g.planets.map(p=>({...p}))},{home:null,biomeAt:()=>'glacier'});assert.equal(hostile.length,0);
 for(const b of ['deep_ocean','frozen_sea','volcano','ember_fields'])assert.equal(seededLandscapes(g,{home:null,biomeAt:()=>b}).length,0);
 assert.ok(seededLandscapes(g,{biomeAt:grass}).length>=1);
 assert.equal(seededLandscapes({...g,planets:g.planets.map(p=>({...p,water:0.95}))},{home:null,biomeAt:grass}).length,0);
 assert.equal(seededLandscapes({...g,planets:g.planets.map(p=>({...p,habitability:0.34}))},{home:null,biomeAt:grass}).length,0);
 assert.equal(LANDSCAPE.minHabitability,0.35);
 let two=0;for(const p of g.planets){const only={...g,planets:[p]};const ls=seededLandscapes(only,{home:null,biomeAt:grass});assert.ok(ls.length<=LANDSCAPE.maxPerPlanet);
  if(ls.length===2){two++;assert.ok(angleBetween(dirOf(ls[0].lat,ls[0].lon),dirOf(ls[1].lat,ls[1].lon))>=LANDSCAPE.minSeparationRad);}}
 assert.ok(two>=1,'at least one planet should place a second landscape');
 // a second place needs hab >= .65
 const mid={...g,planets:g.planets.map(p=>({...p,habitability:0.5}))};for(const p of mid.planets)assert.ok(seededLandscapes({...mid,planets:[p]},{home:null,biomeAt:grass}).length<=1);
});
test('home-world exception: only the home world below 0.35 gets a place, flagged SEEDED, habitability not raised',()=>{
 assert.equal(real.planets.filter(p=>p.habitability>0).length,1);
 const homeId=landscapeHomeWorld(real);assert.equal(homeId,real.planets.find(p=>p.habitability>0).id);
 const ls=seededLandscapes(real);assert.equal(ls.length,1);assert.equal(ls[0].planet,homeId);assert.equal(ls[0].home_exception,true);assert.equal(ls[0].home_label,HOME_WORLD_LANDSCAPE_LABEL);
 assert.equal(ls[0].recorded_habitability,real.planets.find(p=>p.id===homeId).habitability);assert.ok(ls[0].recorded_habitability<LANDSCAPE.minHabitability);
 // every other low-habitability planet gets none, even with a friendly biome
 const lowAll={...real,planets:real.planets.map(p=>({...p,habitability:p.habitability||0.2,water:0.4}))};
 const home2=landscapeHomeWorld(lowAll);const got=seededLandscapes(lowAll,{biomeAt:grass});assert.deepEqual([...new Set(got.map(l=>l.planet))],[home2]);
 for(const l of got)assert.ok(l.planet===home2);assert.equal(seededLandscapes(real,{home:null}).length,0);
 // a qualifying (>=.35) home world is not flagged as an exception
 assert.ok(!seededLandscapes(g,{biomeAt:grass}).some(l=>l.home_exception));
});
test('fixed draws: dropping the last planet changes no earlier planet\'s list; draws per planet are fixed',()=>{
 const all=seededLandscapes(g,{home:null,biomeAt:grass});const cut=seededLandscapes({...g,planets:g.planets.slice(0,-1)},{home:null,biomeAt:grass});
 const last=g.planets.at(-1).id;assert.deepEqual(all.filter(l=>l.planet!==last),cut);
 const withBiome=(p,d)=>p.id===g.planets[2].id?'glacier':'grassland';
 const some=seededLandscapes(g,{home:null,biomeAt:withBiome});assert.deepEqual(some.filter(l=>l.planet!==g.planets[2].id),all.filter(l=>l.planet!==g.planets[2].id));
});
test('mode truth table: four modes in the specified priority',()=>{
 const ls={};
 assert.equal(landscapeMode(ls,{ins:1,storm:0,hasLife:true}),'gather');
 assert.equal(landscapeMode(ls,{ins:1,storm:0.5,hasLife:true}),'shelter');
 assert.equal(landscapeMode(ls,{ins:0.05,storm:0.1,hasLife:true}),'sleep');
 assert.equal(landscapeMode(ls,{ins:1,storm:0,hasLife:false}),'empty');
 assert.equal(landscapeMode(ls,{ins:0,storm:0.9,hasLife:true}),'shelter','storm beats night');
 assert.equal(landscapeMode(ls,{ins:0,storm:0.9,hasLife:false}),'empty','empty beats all');
 assert.equal(landscapeMode(ls,{ins:0.06,storm:0.49,hasLife:true}),'gather');
 assert.deepEqual(new Set(['gather','shelter','sleep','empty']),new Set(LANDSCAPE_MODES));
});
test('lamps: mode factors, night values unchanged, shelter-lamp deviation nf_eff=max(nightFactor,0.5*storm_t)',()=>{
 assert.equal(lampLevel({nightFactor:1,lifeVolume:1,mode:'sleep'}),1);assert.equal(lampLevel({nightFactor:1,lifeVolume:1,mode:'shelter'}),0.6);
 assert.equal(lampLevel({nightFactor:1,lifeVolume:1,mode:'gather'}),0.05);assert.equal(lampLevel({nightFactor:1,lifeVolume:1,mode:'empty'}),0);
 assert.equal(lampLevel({nightFactor:0,storm_t:0,lifeVolume:1,mode:'shelter'}),0);// without the deviation a daytime storm keeps lamps dark
 assert.equal(lampLevel({nightFactor:0,storm_t:1,lifeVolume:1,mode:'shelter'}),0.5*0.6);// with it, half
 assert.equal(lampLevel({nightFactor:0.9,storm_t:1,lifeVolume:1,mode:'shelter'}),0.9*0.6);// night wins when brighter
 assert.ok(nightT(1)===0&&nightT(0.05)===1&&nightT(0.2)>0&&nightT(0.2)<1);
 const src=readFileSync(new URL('../lib/universe/seeded-landscapes.mjs',import.meta.url),'utf8');assert.match(src,/nf_eff=max\(nightFactor, 0\.5 \* storm_t\)/);assert.match(src,/DEVIATION/);
});
test('anchors: unit dirs, shelter inside the pad, garden at the rim opposite the shelter; slots are unit dirs',()=>{
 for(const l of seededLandscapes(g,{biomeAt:grass})){const a=landscapeAnchors(l);const R=l.radiusM/LANDSCAPE.worldRadiusM;
  for(const k of ['play','shelter','lamp','garden'])assert.ok(Math.abs(Math.hypot(...a[k])-1)<1e-9,k);
  assert.ok(angleBetween(a.play,a.shelter)<R);assert.ok(angleBetween(a.play,a.garden)<=R&&angleBetween(a.play,a.garden)>0.8*R);
  assert.ok(angleBetween(a.shelter,a.garden)>angleBetween(a.play,a.shelter));
  const s=landscapeSlots(l);assert.equal(s.lamps.length,l.slots.lamps);assert.equal(s.seats.length,l.slots.seats);assert.equal(s.trees.length,l.slots.trees);
  for(const d of [...s.lamps,...s.seats,...s.trees])assert.ok(Math.abs(Math.hypot(...d)-1)<1e-9);
  assert.ok(l.slots.lamps>=1&&l.slots.lamps<=3&&l.slots.seats>=1&&l.slots.seats<=3&&l.slots.trees>=0&&l.slots.trees<=3);}
});
test('homes derived from the life entry key consume neither the landscape nor the growth stream',()=>{
 const before=seededLandscapes(g,{biomeAt:grass}),gb=seededGrowthNodes(g);
 for(const l of u40.life.length?u40.life:[{id:'life-x'}])lwStream(g.seed+':home:'+l.id)();
 assert.deepEqual(seededLandscapes(g,{biomeAt:grass}),before);assert.deepEqual(seededGrowthNodes(g),gb);
 const a=lwStream(g.seed+':landscapes:'+g.planets[0].id)(),b=lwStream(g.seed+':growth-nodes:'+g.planets[0].id)();assert.notEqual(a,b);
});
test('text is authored: names, notices and zoom lines come from the tables, and no copy claims recorded places',()=>{
 const names=J('../lib/universe/data/landscape_names.json');assert.deepEqual(JSON.parse(JSON.stringify(LANDSCAPE_NAMES)),names);
 assert.deepEqual(names.A,["Chalk","Sunmark","Nap","Ember","Paper","Moss","Star","Low","Amber","Quiet","Little","First"]);
 assert.deepEqual(names.B.court,["Square","Court","Ring"]);assert.deepEqual(names.B.shrine,["Shrine","Lights","Still"]);
 const ls=seededLandscapes(g,{biomeAt:grass});for(const l of ls){const [A,B]=l.name.split(' ');assert.ok(names.A.includes(A)&&names.B[l.kind].includes(B));}
 const lines=J('../lib/universe/data/living_world_lines.json').landscape_notices;
 assert.deepEqual(lines.gather,["{beast} watches the little ones play at {place}. Nobody is keeping score.","Games at {place} again. The ring on {planet} is worn smooth by feet."]);
 assert.deepEqual(lines.shelter,["Rain on {planet}. Everyone at {place} is under cover, waiting it out together."]);
 assert.deepEqual(lines.sleep,["{place} sleeps. The lamps stay lit so the dark knows it is expected."]);
 assert.deepEqual(lines.empty,["{place} is built and waiting. A place is patient. Life will find it."]);
 assert.deepEqual(lines.tap,["{beast} taps the edge of {place}. The whole little world looks up."]);
 const l=ls[0];assert.equal(landscapeNotice(l,'sleep',{beast:'Zeref',planet:'P'}),l.name+' sleeps. The lamps stay lit so the dark knows it is expected.');
 assert.equal(landscapeTapLine(l,{beast:'Cosmo'}),'Cosmo taps the edge of '+l.name+'. The whole little world looks up.');
 const z=landscapeZoom(l,'shelter',{beast:'Zeref',planet:'P'});assert.equal(z.title,l.name+' · '+l.kind.replace('_',' '));assert.equal(z.line,l.name+' is sheltering from the storm.');
 assert.ok(!/recorded|measured|hardware|quantum|live/i.test(z.title+z.line+Object.values(lines).flat().filter(x=>typeof x==='string'&&/place|ring/.test(x)&&x.includes('{place}')).join(' ')));
 assert.equal(KIND_BY_BIOME.paper_marsh,'garden');assert.equal(KIND_BY_BIOME.savanna,'court');assert.equal(KIND_BY_BIOME.glacier,undefined);
});
test('pure: no Math.random, no clock, no growth-nodes import',()=>{
 const src=readFileSync(new URL('../lib/universe/seeded-landscapes.mjs',import.meta.url),'utf8').split('\n').filter(l=>!l.trim().startsWith('//')).join('\n');
 assert.ok(!/Math\.random|Date\.|performance\./.test(src));assert.ok(!/seeded-growth-nodes/.test(src));
});
test('zoom lines: Emeth\'s short mode lines are wired, seeded, honest and keep the storm line exact',()=>{
 const f=J('../lib/universe/data/living_world_lines.json').landscape_zoom;
 assert.deepEqual(f.gather,["{place} is at play. No one keeps score.","The ring at {place} is full of small feet."]);
 assert.deepEqual(f.shelter,["{place} is sheltering from the storm."]);assert.deepEqual(f.empty,["{place} is built and waiting.","No one here yet. {place} is patient."]);
 const l=seededLandscapes(real)[0];const pools={gather:f.gather,sleep:f.sleep,empty:f.empty};
 for(const [m,pool] of Object.entries(pools)){const a=landscapeZoom(l,m,{beast:'Zeref',planet:'Home',seed:'s1'});
  assert.ok(pool.map(t=>t.replace('{place}',l.name).replace('{planet}','Home')).includes(a.line),m);
  assert.deepEqual(a,landscapeZoom(l,m,{beast:'Zeref',planet:'Home',seed:'s1'}));// seeded: same seed, same line
  assert.ok(!/recorded|measured|hardware|quantum|aware|conscious|feels|thinks|live/i.test(a.line),m);}
 assert.equal(landscapeZoom(l,'shelter',{seed:'x'}).line,l.name+' is sheltering from the storm.');
 const seen=new Set();for(let i=0;i<40;i++)seen.add(landscapeZoom(l,'gather',{seed:'seed'+i}).line);assert.equal(seen.size,2);// both lines are reachable
});
