import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {growthNodesAt,growthCellAt,growthScaleAt,GROWTH,LAYER_LAG} from '../lib/universe/seeded-growth-nodes.mjs';
import {GROWTH_TINT} from '../lib/universe/growth-tint-data.mjs';
import {LW_LINES} from '../lib/universe/living-world-lines.mjs';
import {GROWTH_LAYER,TINT_BIOMES,tintBiome,TINT_STRENGTH,srgbToLinear,hexToLinear,blendLinear,tintFor,desatAmount,emissiveAdd,fruitDensity,instanceGrowth,tapBounce,tapGlow,tapNoticeKey,tapNode,snapNodesToHabitat,fruitOffsets,leanAffinity,TAP_MS,shedRecipe} from '../lib/universe/growth-view.mjs';
import {gaussianAffinity} from '../lib/companion/spark/engine.mjs';
const J=p=>JSON.parse(readFileSync(new URL(p,import.meta.url),'utf8'));
const real=genesis(J('../public/spark/ibm-marrakesh-reality-probe-20261009.json'));
const unit=(lat,lon)=>{const a=lat*Math.PI/180,o=lon*Math.PI/180;return [Math.cos(a)*Math.cos(o),Math.sin(a),Math.cos(a)*Math.sin(o)];};

test("Cosmo's tint pack and Emeth's growth lines are in the code verbatim",()=>{
 assert.deepEqual(GROWTH_TINT,J('../lib/universe/data/growth_tint.json'));
 assert.deepEqual(LW_LINES,J('../lib/universe/data/living_world_lines.json'));
 for(const k of ['sprout','full','bloom','gold','shed','canopy','scarred']){const p=LW_LINES.creature_notices['growth_tap_'+k];assert.ok(p.length>=1);for(const l of p)assert.ok(l.includes('{beast}')||k==='scarred'||k==='canopy'||k==='shed',k);}
 assert.equal(LW_LINES.creature_notices.growth_tap_sprout[0],'{beast} noses the new shoot. So small.');
});
test('tint blends toward the pack colour in LINEAR light and cannot be a multiply',()=>{
 const base=hexToLinear('#3F9995');const gold=hexToLinear(GROWTH_TINT.resolved.grassland.canopy.gold);
 const m=blendLinear(base,gold,.88);const mul=base.map((v,i)=>v*gold[i]);
 assert.ok(m[0]>base[0]*1.5,'red rises: a multiply could never do that');assert.ok(m[0]>mul[0]*2);
 assert.deepEqual(blendLinear(base,gold,0),base);assert.deepEqual(blendLinear(base,gold,1),gold);
 // linear light: half-way is NOT the sRGB average
 const half=blendLinear([0,0,0],[1,1,1],.5);assert.equal(half[0],.5);assert.ok(srgbToLinear(.5)<.25);
});
test('tintFor: stage anchors, smooth blend windows, scarred early gold, unborn untouched, kind mix_scale',()=>{
 const P=GROWTH_TINT;
 for(const b of TINT_BIOMES)for(const k of ['ring','patch','shrub','canopy']){
  const t=tintFor(b,k,'full',.6);const want=hexToLinear(P.resolved[b][k].full);for(let i=0;i<3;i++)assert.ok(Math.abs(t.rgb[i]-want[i])<1e-9);
  assert.ok(Math.abs(t.mix-P.mix_by_stage.full*P.kind_overrides[k].mix_scale)<1e-9);}
 // continuous across a window and monotone from the previous colour to this one
 const a=tintFor('grassland','canopy','gold',.78),b=tintFor('grassland','canopy','gold',.83),c=tintFor('grassland','canopy','gold',.9);
 const prev=hexToLinear(P.resolved.grassland.canopy.bloom),tgt=hexToLinear(P.resolved.grassland.canopy.gold);
 assert.ok(Math.abs(a.rgb[0]-prev[0])<1e-9);assert.ok(a.rgb[0]<b.rgb[0]&&b.rgb[0]<c.rgb[0]);assert.ok(Math.abs(c.rgb[0]-tgt[0])<1e-9);
 // scarred nodes: gold starts earlier, so the gold window moves with gold; and full/bloom lean toward gold
 const early=tintFor('grassland','canopy','gold',.7,{gold:.7});assert.ok(early.rgb[0]>=tintFor('grassland','canopy','gold',.7,{gold:.78}).rgb[0]);
 const sc=tintFor('grassland','canopy','full',.5,{scars:1}),ns=tintFor('grassland','canopy','full',.5);assert.ok(sc.rgb[0]>ns.rgb[0]);
 assert.equal(tintFor('nope','canopy','bogus',.5).mix,0);
 assert.equal(tintBiome('pine_forest'),'heartwood_forest');assert.equal(tintBiome('grassland'),'grassland');
});
test('material gating: tint only the listed leaf materials, tips at half, never bark/petals/trims/rocks',()=>{
 for(const n of GROWTH_TINT.apply_to_materials)assert.equal(TINT_STRENGTH(n),1);
 for(const n of GROWTH_TINT.apply_half_strength)assert.equal(TINT_STRENGTH(n),.5);
 for(const n of GROWTH_TINT.never_tint_materials)assert.equal(TINT_STRENGTH(n),0);
 assert.equal(TINT_STRENGTH('unknown_material'),0);
});
test('desaturation caps at 0.3, storm only on shrub/canopy; emissive stays under 0.15; fruit only bloom on shrub/canopy',()=>{
 assert.equal(desatAmount('ring',1,false),0);assert.equal(desatAmount('patch',1,false),0);
 assert.ok(Math.abs(desatAmount('canopy',1,false)-.22)<1e-9);assert.equal(desatAmount('canopy',1,true),.3);assert.ok(desatAmount('canopy',5,true)<=.3);assert.equal(desatAmount('ring',0,true),.15);
 for(const l of ['ring','patch','shrub','canopy'])for(const s of GROWTH_TINT.stages){const e=emissiveAdd(l,s,1);const lin=e.map(v=>v);assert.ok(Math.max(...lin)<=.15+1e-9);}
 assert.deepEqual(emissiveAdd('canopy','sprout',0),[0,0,0]);
 for(const l of ['ring','patch'])for(const s of GROWTH_TINT.stages)assert.equal(fruitDensity('grassland',l,s,.7),0);
 assert.ok(fruitDensity('grassland','shrub','bloom',.75)>0.5);assert.ok(fruitDensity('grassland','canopy','bloom',.75)>0);
 assert.ok(fruitDensity('grassland','shrub','gold',.85)>0&&fruitDensity('grassland','shrub','gold',.85)<fruitDensity('grassland','shrub','bloom',.75));
 assert.equal(fruitDensity('grassland','shrub','shed',.95),0);assert.equal(fruitDensity('grassland','shrub','full',.5),0);
 assert.ok(fruitDensity('rainforest','shrub','bloom',.75)>=fruitDensity('crystal_moss','shrub','bloom',.75));
});
test('layers grow in succession (ring, patch, shrub, canopy) from the same node and tick; identity outside territories',()=>{
 const t=40;const nodes=growthNodesAt(real,t);assert.ok(nodes.length>=1);const n=nodes[0];const c=unit(n.lat,n.lon);
 const s=l=>growthCellAt(nodes,t,c,{layer:l});
 const sc=['ring','patch','shrub','canopy'].map(l=>s(l).scale);
 const x=['ring','patch','shrub','canopy'].map(l=>s(l).x);
 assert.ok(x.every((v,i)=>i===0||v==null||x[i-1]==null||v<=x[i-1]),'lagging layers are younger: '+x);
 assert.equal(LAYER_LAG.ring,0);assert.ok(LAYER_LAG.canopy>LAYER_LAG.shrub&&LAYER_LAG.shrub>LAYER_LAG.patch);
 assert.equal(growthScaleAt(nodes,t,c),growthCellAt(nodes,t,c).scale);
 const far=c.map(v=>-v);const i=instanceGrowth(nodes,t,far,'canopy','grassland');assert.equal(i.hit,false);assert.equal(i.scale,1);assert.equal(i.mix,0);assert.deepEqual(i.emissive,[0,0,0]);
 // tint + scale + fruit come from ONE cell: stage in the result is the stage of x
 const g=instanceGrowth(nodes,t,c,'shrub','grassland');assert.equal(g.hit,true);assert.equal(g.scale,growthCellAt(nodes,t,c,{layer:'shrub'}).scale);
 // deterministic
 assert.deepEqual(instanceGrowth(nodes,t,c,'canopy','grassland'),instanceGrowth(structuredClone(nodes),t,c,'canopy','grassland'));
});
test('tap: bounce is view-only, 600 ms, zero under reduced motion; notice keys exist in Emeth lines; a tap hits only a territory',()=>{
 assert.equal(tapBounce(0,true),0);assert.equal(tapBounce(300,true),0);assert.equal(tapBounce(TAP_MS,false),0);assert.equal(tapBounce(-5,false),0);
 assert.ok(Math.max(...[...Array(60)].map((_,i)=>Math.abs(tapBounce(i*10))))>.05);assert.ok(tapGlow(0)>0.9&&tapGlow(TAP_MS*2)===0);
 const stages=['sprout','tuft','full','bloom','gold','shed'];
 for(const st of stages)for(const sc of [false,true])for(const kind of ['ring','canopy']){const k=tapNoticeKey({stage:st,scarred:sc,node:{kind}});assert.ok(LW_LINES.creature_notices[k],k);}
 assert.equal(tapNoticeKey({stage:'tuft',node:{kind:'ring'}}),'growth_tap_sprout');assert.equal(tapNoticeKey({stage:'full',node:{kind:'canopy'}}),'growth_tap_canopy');assert.equal(tapNoticeKey(null),null);
 const nodes=growthNodesAt(real,60);const c=unit(nodes[0].lat,nodes[0].lon);assert.ok(tapNode(nodes,60,c));assert.equal(tapNode(nodes,60,c.map(v=>-v)),null);
});
test('home-world nodes are moved to the nearest habitat by the view only, deterministically; none within reach means none shown',()=>{
 const nodes=growthNodesAt(real,0);assert.ok(nodes.length>=1);
 const all=snapNodesToHabitat(nodes,()=>true);assert.deepEqual(all.map(n=>[n.lat,n.lon]),nodes.map(n=>[n.lat,n.lon]));assert.ok(all.every(n=>n.view_snapped===false));
 const c0=unit(nodes[0].lat,nodes[0].lon);const hab=d=>d[0]*c0[0]+d[1]*c0[1]+d[2]*c0[2]<Math.cos(.5);// habitat starts 0.5 rad away from the seeded spot
 const a=snapNodesToHabitat([nodes[0]],hab),b=snapNodesToHabitat([structuredClone(nodes[0])],hab);assert.deepEqual(a,b);assert.equal(a.length,1);assert.equal(a[0].view_snapped,true);
 const d=unit(a[0].lat,a[0].lon);assert.ok(hab(d));const ang=Math.acos(Math.max(-1,Math.min(1,d[0]*c0[0]+d[1]*c0[1]+d[2]*c0[2])));assert.ok(ang<.6,'nearest, not random: '+ang);
 assert.equal(a[0].label,'SEEDED');assert.equal(snapNodesToHabitat([nodes[0]],()=>false).length,0);
 assert.equal(a[0].home_exception,nodes[0].home_exception);// the SEEDED home-world exception flag survives
});
test('fruit offsets and shed recipe: seeded, fixed draw counts, pack colours',()=>{
 const a=fruitOffsets('s',10,6),b=fruitOffsets('s',10,6);assert.deepEqual(a,b);assert.equal(a.length,10*6*5);assert.notDeepEqual(a,fruitOffsets('t',10,6));
 assert.deepEqual(fruitOffsets('s',4,6),a.slice(0,4*6*5));// a prefix: draw count per tree is fixed
 for(const k of ['ring','patch','shrub','canopy']){const r=shedRecipe(k);assert.equal(r.colors.length,4);assert.ok(r.size_m[0]<r.size_m[1]);}
 assert.ok(shedRecipe('canopy').size_m[1]>shedRecipe('ring').size_m[1]);
});
test('lean uses the engine gaussianAffinity kernel',()=>{
 for(const d of [0,1,2.2,5])assert.equal(leanAffinity(d),gaussianAffinity([d],[0],2.2));assert.equal(leanAffinity(0),1);assert.ok(leanAffinity(6)<.05);
});
test('no Math.random or clock reads in the growth view code; reduced motion gates every moving term; honesty labels present',()=>{
 for(const f of ['growth-view.mjs','growth-three.ts','surface-three.ts']){const src=readFileSync(new URL('../lib/universe/'+f,import.meta.url),'utf8').replace(/\/\*[\s\S]*?\*\//g,'').replace(/\/\/.*$/gm,'');
  assert.ok(!/Math\.random|Date\.now|new Date|performance\.now/.test(src),f);}
 const sv=readFileSync(new URL('../lib/universe/surface-three.ts',import.meta.url),'utf8');
 assert.ok(/swg=\(.*\)\*uGMotion/.test(sv));assert.ok(/uGShiver\*uGMotion/.test(sv));assert.ok(/aGl\*uGMotion/.test(sv));assert.ok(/tapBounce\(age,f\.reduced\)/.test(sv));
 assert.ok(/uMotion\)/.test(readFileSync(new URL('../lib/universe/growth-three.ts',import.meta.url),'utf8')));
 const gv=readFileSync(new URL('../lib/universe/growth-view.mjs',import.meta.url),'utf8');assert.ok(/SEEDED/.test(gv)&&/SIMULATED/.test(gv)&&!/live quantum|recorded growth/i.test(gv.replace(/nothing here claims live quantum or recorded growth/i,'')));
 const sh=readFileSync(new URL('../lib/universe/growth-three.ts',import.meta.url),'utf8');assert.ok(/SEEDED/.test(sh)&&/SIMULATED/.test(sh));
});
test('identity with the layer off: assets without growth keep their own keys; GROWTH_LAYER only names existing assets',async()=>{
 const gc=await import('../lib/universe/groundcover.mjs');
 for(const k of Object.keys(GROWTH_LAYER)){const ok=k.startsWith('tree:')?gc.TREE_KINDS.includes(k.slice(5)):gc.GROUND_ASSETS.includes(k);assert.ok(ok,k);}
 for(const k of ['rock_pebble','rock_boulder','crystal_small','crystal_cluster','crystal_spire','tree:dead_ember'])assert.equal(GROWTH_LAYER[k],undefined);
 assert.ok(Object.isFrozen(GROWTH));
});
