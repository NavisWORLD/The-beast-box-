import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {genesis,grow} from '../lib/universe/tiny-universe.mjs';
import {seededGrowthNodes,growthNodesAt,growthNodeState,growthScaleAt,growthDrive,stageAt,stageScale,GROWTH,GROWTH_NODE_LABEL,NODE_KINDS,NODE_STAGES} from '../lib/universe/seeded-growth-nodes.mjs';
const shard=JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url),'utf8'));
const real=genesis(shard);
// The recorded genesis has one planet at habitability .17 (< minHabitability .25), so it plants no nodes. Tests use the same genesis with every planet set habitable.
const g={...real,planets:real.planets.map(p=>({...p,habitability:0.9}))};const u40=grow(g,40);
const stages=(u,ticks)=>ticks.map(t=>growthNodesAt(u,t).map(n=>n.stage+':'+n.scale).join(','));

test('determinism: same seed and tick give the same forest, a different tick changes a stage or scale',()=>{
 const a=growthNodesAt(u40,40),b=growthNodesAt(structuredClone(u40),40);assert.ok(a.length>=1);assert.deepEqual(a,b);
 assert.deepEqual(seededGrowthNodes(g),seededGrowthNodes(structuredClone(g)));
 const other=stages(u40,[0,30,60,90,120,160,200,260]);assert.ok(new Set(other).size>1);
 const c=growthNodesAt(u40,70);assert.ok(a.some((n,i)=>n.stage!==c[i].stage||n.scale!==c[i].scale));
});
test('labels: every node SEEDED, genesis untouched, growth_label unchanged',()=>{
 const before=JSON.stringify(u40);const nodes=growthNodesAt(u40,40);
 for(const n of nodes){assert.equal(n.label,'SEEDED');assert.equal(n.type,'growth_node');assert.ok(NODE_KINDS.includes(n.kind));assert.ok(NODE_STAGES.includes(n.stage));}
 assert.equal(GROWTH_NODE_LABEL,'SEEDED');assert.equal(JSON.stringify(u40),before);
 assert.equal(u40.growth_label,'SIMULATED (Rigetti Bell simulator, not hardware)');
 assert.ok(/RECORDED_IBM_HARDWARE/.test(JSON.stringify(g.source)+JSON.stringify(g.pairs?.[0]??{})));
 assert.ok(nodes.every(n=>g.planets.find(p=>p.id===n.planet).habitability>=GROWTH.minHabitability));
});
test('isolation: stars, planets, storms, life, pairs are byte-identical with nodes on or off',()=>{
 const pick=u=>JSON.stringify({stars:u.stars,planets:u.planets,storms:u.storms,life:u.life,pairs:u.pairs});
 const off=pick(u40);const copy=structuredClone(u40);growthNodesAt(copy,40);seededGrowthNodes(copy);growthScaleAt(growthNodesAt(copy,40),40,[0,1,0]);
 assert.equal(pick(copy),off);assert.equal(JSON.stringify(copy),JSON.stringify(u40));
 // and the nodes never shift the universe's own streams: growing after computing nodes matches growing without
 growthNodesAt(g,0);assert.equal(JSON.stringify(grow(g,25)),JSON.stringify(grow({...real,planets:real.planets.map(p=>({...p,habitability:0.9}))},25)));
 assert.deepEqual(seededGrowthNodes(real),[]);// honest: no node on worlds below minHabitability
});
test('fixed draws: removing the last planet leaves every earlier planet node list unchanged',()=>{
 const u=g;const all=seededGrowthNodes(u);
 const last=u.planets[u.planets.length-1].id;const less=seededGrowthNodes({...u,planets:u.planets.slice(0,-1)});
 assert.deepEqual(less,all.filter(n=>n.planet!==last));assert.ok(all.some(n=>n.planet===last));
 // a skipped (dead) middle planet does not shift the next one either
 const mid=u.planets[1].id;const dead=seededGrowthNodes({...u,planets:u.planets.map(p=>p.id===mid?{...p,habitability:0}:p)});
 assert.deepEqual(dead,all.filter(n=>n.planet!==mid));
});
test('drive: high sim_E gives a strictly larger front than low at the same tick',()=>{
 const hi=structuredClone(u40),lo=structuredClone(u40);hi.history.at(-1).sim_E=0.99;lo.history.at(-1).sim_E=0.1;const t=hi.history.at(-1).tick;
 const a=growthNodesAt(hi,t),b=growthNodesAt(lo,t);assert.ok(growthDrive(hi,t)>growthDrive(lo,t));
 a.forEach((n,i)=>assert.ok(n.front>b[i].front,n.id));
 const empty=growthNodesAt({...g,history:[]},50);assert.ok(empty.every(n=>n.drive===+(Math.max(0.1,Math.min(1.6,0.5+g.entanglement_E))).toFixed(4)));
});
test('scar: a storm on the node planet while it is in full/bloom scars it and brings gold earlier',()=>{
 const n0=seededGrowthNodes(g)[0];const life=n0.lifespan;
 const hist=[];for(let t=Math.round(life*0.4);t<=Math.round(life*0.7);t++)hist.push({tick:t,source:'SIMULATED',sim_E:0.5,counts:{},events:[]});
 const storms=[{id:'s',planet:n0.planet,intensity:.3,lifetime:9999,born:0}];
 const control=growthNodeState(n0,{...g,history:hist,storms:[]},hist.at(-1).tick);
 const scarred=growthNodeState(n0,{...g,history:hist,storms},hist.at(-1).tick);
 assert.equal(control.scarred,false);assert.equal(scarred.scarred,true);assert.ok(scarred.scars>0);assert.ok(scarred.gold<control.gold);assert.ok(scarred.gold>=GROWTH.minGold);
 // earlier gold: pick the first life position where the stage is gold
 const first=(gold)=>{for(let x=0;x<1;x+=0.001)if(stageAt(x,gold)==='gold')return x;return 1;};assert.ok(first(scarred.gold)<first(control.gold));
 const hist2=hist.map(h=>({...h,storms:[n0.planet]}));assert.equal(growthNodeState(n0,{...g,history:hist2,storms:[]},hist.at(-1).tick).scarred,true);
});
test('renewal: past two life spans the generation is >=2 and the stage is back at sprout or tuft',()=>{
 for(const n of seededGrowthNodes(g)){const t=n.born+2*n.lifespan+Math.ceil(n.lifespan*0.05);const s=growthNodeState(n,g,t);assert.ok(s.generation>=2,n.id);assert.ok(['sprout','tuft'].includes(s.stage),n.id+' '+s.stage);}
});
test('full cycle by stepping ticks: sprout, bloom with fruit, gold, shed, renewal; layers in succession order',()=>{
 const seen={};for(const n of seededGrowthNodes(g)){const st=new Set(),fruit=[];let firstFull=null;
  for(let t=0;t<=n.lifespan*1.3;t++){const s=growthNodeState(n,g,t);st.add(s.stage);if(s.fruit)fruit.push(1);if(s.stage==='full'&&firstFull==null)firstFull=t;}
  for(const x of NODE_STAGES)assert.ok(st.has(x),n.id+' misses '+x);seen[n.kind]=(seen[n.kind]||0)+1;
  assert.equal(fruit.length>0,GROWTH.fruitKinds.includes(n.kind));}
 const L=GROWTH.kinds;assert.ok(L.ring.life<L.patch.life&&L.patch.life<L.shrub.life&&L.shrub.life<L.canopy.life);
 assert.equal(stageScale(.7),1);assert.equal(stageScale(.78+.15-.001)>1.05,true);
 const s=[0,.05,.2,.5,.7,.85,.95].map(x=>stageScale(x));assert.ok(s[0]<s[1]&&s[1]<s[2]&&s[2]<s[3]);
});
test('growthScaleAt: identity where no node reaches, front timing inside, unborn before the front, rim overflow, byte-neutral',()=>{
 const nodes=growthNodesAt(g,0).map(n=>({...n}));const n=nodes[0];const a=n.lat*Math.PI/180,o=n.lon*Math.PI/180;const c=[Math.cos(a)*Math.cos(o),Math.sin(a),Math.cos(a)*Math.sin(o)];
 const far=c.map(v=>-v);assert.equal(growthScaleAt(nodes,0,far),1);assert.equal(growthScaleAt([],0,c),1);
 const t=Math.round(n.lifespan*0.3);const late=growthNodesAt(g,t);const m=late[0];
 const here=growthScaleAt(late,t,c);assert.ok(here>0&&here<=1.07);
 // a direction at the rim of the territory is younger than the centre
 const e1=[-c[2],0,c[0]];const l=Math.hypot(...e1);const ang=GROWTH.cellRad*m.spread*0.95;
 const rim=c.map((v,i)=>v*Math.cos(ang)+e1[i]/l*Math.sin(ang));assert.ok(growthScaleAt(late,t,rim)<=here);
 const early=growthNodesAt(g,1);assert.equal(growthScaleAt(early,1,rim),GROWTH.unborn);// the front has not reached the rim yet
});
test('no Math.random or clock reads in the module, and no UI claims of live quantum or recorded growth',()=>{
 const src=readFileSync(new URL('../lib/universe/seeded-growth-nodes.mjs',import.meta.url),'utf8');const code=src.replace(/\/\/.*$/gm,'');
 assert.ok(!/Math\.random|Date\.|performance\.now|new Date/.test(code));
 assert.ok(/SEEDED/.test(src)&&/SIMULATED/.test(src)&&/RECORDED/.test(src));
 assert.ok(!/live quantum|hardware-measured/i.test(code));
});
