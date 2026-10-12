import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ZEREF_PROFILE,createMind,stepMind,frameFor,recordedSeed} from '../lib/zeref/zeref-mind.mjs';
import {createPocket,stepPocket,blendFrame,sampleCombo,comboOf,poiWeights,growthLook,PHASES,POI_KINDS} from '../lib/zeref/zeref-pocket.mjs';
import {genesisState,stepDiary,verifyChain,entryHash,stageFor,STAGES,summarize,localHour,XP_PER_TICK} from '../lib/zeref/zeref-diary.mjs';
import {ZEREF_SKIN,isZerefBeast,skinFromGenome,seedFromGenome} from '../lib/zeref/rig-style.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const digest=recordedSeed().digest;

function run(seconds,{energy}={}){
 const m=createMind({care:energy!==undefined?{energy}:{} ,hour:14});
 const p=createPocket({digest,key:ZEREF_PROFILE.id});
 const events=[],phases=new Set(),combos=[];
 for(let i=0;i<seconds*10;i++){
  stepMind(m,.1,{hour:14});
  for(const e of stepPocket(p,m,.1))events.push(e);
  phases.add(p.phase);
  const c=sampleCombo(p,blendFrame(frameFor(m),p,m,{stage:2}),m);if(c)combos.push(c);
  assert.ok(p.x>=-1&&p.x<=1&&p.y>=-1&&p.y<=1,'stays inside the pocket');
 }
 return {m,p,events,phases,combos};
}

test('pocket places are seeded: same beast, same pocket; spread out; all three kinds',()=>{
 const a=createPocket({digest,key:'x'}),b=createPocket({digest,key:'x'});
 assert.deepEqual(a.pois,b.pois);
 assert.notDeepEqual(a.pois,createPocket({digest,key:'other'}).pois);
 assert.equal(a.pois.length,7);
 for(const k of POI_KINDS)assert.ok(a.pois.some(p=>p.kind===k),k);
 assert.equal(new Set(a.pois.map(p=>p.name)).size,7,'unique place names');
});

test('state machine: rest -> travel -> interact cycles, arrivals happen, replay is deterministic',()=>{
 const one=run(120),two=run(120);
 for(const ph of PHASES)assert.ok(one.phases.has(ph),ph);
 const arrivals=one.events.filter(e=>e.type==='arrive');
 assert.ok(arrivals.length>=4,'explores several places in two minutes: '+arrivals.length);
 assert.deepEqual(one.events,two.events,'same seed + same inputs = same exploration');
 assert.deepEqual(one.combos.map(c=>c.key),two.combos.map(c=>c.key));
 assert.ok(one.combos.length>=8,'blending produces many distinct combos');
 assert.equal(new Set(one.combos.map(c=>c.key)).size,one.combos.length,'a combo is reported once');
});

test('tired beasts favour moon pools; attacks (busy) plant the feet',()=>{
 const p=createPocket({digest,key:'w'});
 const tired=createMind({care:{energy:25}}),fresh=createMind({care:{energy:95}});
 const share=(m)=>{const w=poiWeights(p,m);const pools=p.pois.map((x,i)=>x.kind==='moon-pool'?w[i]:0).reduce((s,v)=>s+v,0);return pools/w.reduce((s,v)=>s+v,0);};
 assert.ok(share(tired)>share(fresh));
 const m=createMind({hour:14});const q=createPocket({digest,key:'b'});
 for(let i=0;i<40;i++){stepMind(m,.1);stepPocket(q,m,.1);}
 const at={x:q.x,y:q.y,t:q.t};
 for(let i=0;i<30;i++){stepMind(m,.1);stepPocket(q,m,.1,{busy:true});}
 assert.deepEqual({x:q.x,y:q.y},{x:at.x,y:at.y});
});

test('combos are honest blends of existing rig channels and growth maps to size/aura',()=>{
 const m=createMind();const p=createPocket({digest});
 const c=comboOf(frameFor(m),p,m);
 assert.deepEqual(Object.keys(c.parts),['action','gait','place','wings','tail','eyes','mouth']);
 assert.equal(c.key.split('|').length,7);
 assert.ok(growthLook(5).scale>growthLook(1).scale&&growthLook(5).aura>growthLook(1).aura);
 assert.deepEqual(growthLook(99),growthLook(5));
 const pocket=read('lib/zeref/zeref-pocket.mjs')+read('lib/zeref/zeref-diary.mjs');
 assert.doesNotMatch(pocket,/Math\.random|Date\.now|new Date\(\)|localStorage|fetch\(/,'pure and deterministic');
 assert.match(read('lib/zeref/zeref-pocket.mjs'),/not new animations/);
});

const T0=Date.parse('2026-10-11T23:37:00Z');
const iso=i=>new Date(T0+i*1800e3).toISOString();
function ticks(n){let s=genesisState();const out=[];for(let i=0;i<n;i++){const r=stepDiary(s,{now:iso(i)});s=r.state;out.push(r.entry);}return {s,out};}

test('loop step: deterministic, append-only hash chain, xp only grows, stage from xp',()=>{
 const a=ticks(30),b=ticks(30);
 assert.deepEqual(a.out,b.out,'same ticks + same times = same diary');
 assert.deepEqual(verifyChain(a.out,a.s.identity),{ok:true,tick:30,head:a.s.last_entry_hash});
 // Append-only: extending never rewrites earlier entries.
 const more=stepDiary(a.s,{now:iso(30)});
 assert.deepEqual([...a.out,more.entry].slice(0,30),a.out);
 assert.equal(more.entry.prev_hash,a.out.at(-1).hash);
 let xp=0;for(const e of a.out){assert.ok(e.xp>xp);assert.ok(e.xp_gain>=XP_PER_TICK);xp=e.xp;assert.equal(e.stage,stageFor(e.xp).stage);}
 assert.ok(a.s.stage>=2,'he visibly grows within a day of ticks');
 // Tampering is detected.
 const bad=a.out.map(e=>({...e}));bad[3].mood='hacked';
 assert.equal(verifyChain(bad).ok,false);
 const gap=a.out.filter((_,i)=>i!==5);assert.equal(verifyChain(gap).reason,'tick-gap');
 assert.throws(()=>stepDiary(a.s,{now:a.s.last_tick_at}),/move forward/);
});

test('identity never changes and the recorded digest stays out of mutable fields',()=>{
 const g=genesisState();const {s,out}=ticks(12);
 assert.deepEqual(s.identity,g.identity);
 assert.equal(s.identity.beast_id,ZEREF_PROFILE.id);
 assert.equal(s.identity.recorded_digest,digest);
 const {identity,...mutable}=s;
 assert.ok(!JSON.stringify(mutable).includes(digest),'digest not copied into mutable state');
 for(const e of out){assert.ok(!JSON.stringify(e).includes(digest),'digest not in entries');assert.equal(e.beast_id,ZEREF_PROFILE.id);assert.equal(entryHash(e),e.hash);}
 // A step never mutates the previous state object.
 const before=JSON.stringify(s);stepDiary(s,{now:iso(40)});assert.equal(JSON.stringify(s),before);
});

test('thoughts: template by default, a supplied model line is labelled, care is bounded',()=>{
 const g=genesisState();
 const t=stepDiary(g,{now:iso(0)}).entry.thought;
 assert.equal(t.by,'deterministic-template');assert.ok(t.text.length>10);
 const m=stepDiary(g,{now:iso(0),thought:{text:'Hi from a model',by:'huggingface-router:x/y'}}).entry.thought;
 assert.deepEqual(m,{text:'Hi from a model',by:'huggingface-router:x/y'});
 const noBy=stepDiary(g,{now:iso(0),thought:{text:'unlabelled'}}).entry.thought;
 assert.equal(noBy.by,'deterministic-template','an unlabelled line is never passed off as a model');
 const cared=stepDiary(g,{now:iso(0),care:999}).entry;
 assert.equal(cared.care,20);
 assert.equal(localHour('2026-10-12T03:00:00Z'),22,'Chicago local hour');
 const sum=summarize(ticks(3).s,ticks(3).out);
 assert.ok(!('combos_known' in sum));assert.equal(sum.recent.length,3);assert.match(sum.labels.seed,/Not a live quantum link/);
 assert.equal(STAGES.length,5);
});

test('rig skins: Zeref canonical, other beasts tinted from their own genome',()=>{
 assert.ok(isZerefBeast({name:'Zeref'})&&isZerefBeast({id:ZEREF_PROFILE.id})&&!isZerefBeast({name:'Emberkin'}));
 const gen={island:'Cinder Drift',genes:{hue:.5,sat:.5,val:.5},glow:'native',wings:'none',ears:'horns',tail:'flame',seed:'abc',quantum:{marginals:[.3,.7],entropy_norm:.8,counts_sha256:'ff'}};
 assert.equal(skinFromGenome(gen,{name:'Zeref'}),ZEREF_SKIN);
 const s=skinFromGenome(gen,{name:'Emberkin',id:'bb-1'});
 assert.equal(s.canonical,false);assert.equal(s.features.wings,false);assert.equal(s.features.horns,true);
 assert.notEqual(s.fur[1],ZEREF_SKIN.fur[1]);assert.match(s.fur[1],/^#[0-9a-f]{6}$/);
 const umbral=skinFromGenome({...gen,island:'Umbral Deep'},{name:'Nyx'});
 assert.notEqual(umbral.fur[1],s.fur[1],'palette follows the genome island');
 const seed=seedFromGenome(gen);assert.equal(seed.features.zzOdd,.3);assert.equal(seedFromGenome(gen).digest,seed.digest);
});

test('Cage wiring: rig is default, classic sprite reachable, diary + labels, loop never redeploys',()=>{
 const portal=read('components/beast-cage-portal.tsx'),arena=read('components/spark-beast-arena.tsx'),spark=read('components/spark-beast-companion.tsx');
 assert.match(portal,/useState<'pocket'\|'classic'>\('pocket'\)/);
 assert.match(portal,/Classic pixel sprite/);
 assert.match(portal,/rig=\{view==='pocket'&&\(!savedVisual\|\|savedVisual\.renderer==='moonwraith-rig'\)\}/,
  'pocket view retains the established Moonwraith rig, but other saved QBEASTs render their recorded native genome');
 assert.match(portal,/preferSavedBeast=\{sameSpark\}/,'saved creature must override an unrelated starter profile');
 assert.match(portal,/creatureVisual\(\{id:session\.beast\.qbeast\.profile\.id/,'presentation follows the exact selected QBEAST');
 assert.match(portal,/<ZerefDiaryPanel/);
 assert.match(arena,/createPocket\(/);assert.match(arena,/beastbox:rig-cue/);assert.match(arena,/Make the beast attack/);
 assert.match(spark,/<SparkRig /);assert.match(spark,/renderBeast/,'pixel renderer kept for the classic view');
 const rig=read('components/spark-rig.tsx');
 assert.match(rig,/requestAnimationFrame/);assert.match(rig,/visibilitychange/);assert.match(rig,/IntersectionObserver/);
 assert.doesNotMatch(rig+arena,/Math\.random/);
 const panel=read('components/zeref-diary-panel.tsx');
 assert.match(panel,/not a conscious mind|Not a live quantum link|not new hand-made animations/);
 assert.match(read('components/homepage-creature.tsx'),/<ZerefLatestThought/);
 const wf=read('../../.github/workflows/zeref-diary-loop.yml');
 assert.match(wf,/cron: '7,37 \* \* \* \*'/);assert.match(wf,/zeref-diary/);assert.match(wf,/\[skip ci\]/);assert.match(wf,/deploymentEnabled":false/);
 assert.match(wf,/ZEREF_DIARY_MODEL_BILLING_APPROVED == 'yes'/,'model secret only passed after explicit billing approval');
 assert.equal(JSON.parse(read('vercel.json')).git.deploymentEnabled['zeref-diary'],false);
 assert.match(read('app/api/zeref/diary/route.ts'),/raw\.githubusercontent\.com\/NavisWORLD\/The-beast-box-\/zeref-diary/);
});

import {planGrowthCircuit,countsFeatures,QVM_TARGET,BIRTH_SPARK} from '../lib/zeref/zeref-diary.mjs';
test('growth: free Rigetti QVM simulator counts feed the step; failures fall back honestly',()=>{
 const g=genesisState();
 const plan=planGrowthCircuit(g);
 assert.equal(plan.target,'rigetti.sim.qvm');assert.equal(QVM_TARGET,'rigetti.sim.qvm');
 assert.match(plan.quil,/^DECLARE ro BIT\[3\]\nRY\(/);assert.deepEqual(planGrowthCircuit(g),plan,'circuit is deterministic from state');
 assert.equal(plan.job_name,'zeref-diary-tick-1-bb-7f9c2a03');
 const counts={'000':40,'001':20,'010':30,'011':10,'100':50,'101':36,'110':40,'111':30};
 const ok=stepDiary(g,{now:iso(0),growth:{ok:true,target:'rigetti.sim.qvm',job_id:'job-1',job_name:plan.job_name,shots:256,counts}}).entry;
 assert.equal(ok.growth_source.kind,'rigetti-qvm-simulated');assert.equal(ok.growth_source.simulated,true);
 assert.equal(ok.growth_source.job_id,'job-1');assert.deepEqual(ok.growth_source.counts,counts);assert.equal(ok.growth_source.shots,256);
 assert.deepEqual(ok.birth_spark,BIRTH_SPARK);assert.equal(ok.birth_spark.backend,'ibm_marrakesh');
 const other=stepDiary(g,{now:iso(0),growth:{ok:true,target:'rigetti.sim.qvm',job_id:'job-2',job_name:plan.job_name,shots:256,counts:{...counts,'000':10,'111':60}}}).entry;
 assert.notDeepEqual(ok.signals,other.signals,'different simulator counts move the signals');
 const fail=stepDiary(g,{now:iso(0),growth:{ok:false,target:'rigetti.sim.qvm',error:'RuntimeError: target offline'}}).entry;
 assert.equal(fail.growth_source.kind,'deterministic-fallback');assert.equal(fail.growth_source.error,'RuntimeError: target offline');
 assert.ok(!('counts' in fail.growth_source),'no counts are invented on failure');
 const bad=stepDiary(g,{now:iso(0),growth:{ok:true,target:'rigetti.qpu.cepheus-1-108q',job_id:'x',shots:256,counts}}).entry;
 assert.equal(bad.growth_source.kind,'deterministic-fallback','a non-simulator target is never accepted');
 assert.equal(countsFeatures({'00':256}),null);assert.equal(countsFeatures({...counts,'000':1}),null,'shots must match');
 assert.equal(verifyChain([ok]).ok,true);
 const wf=read('../../.github/workflows/zeref-diary-loop.yml'),py=read('scripts/zeref_diary_qvm.py');
 assert.match(py,/ALLOWED_TARGET = "rigetti\.sim\.qvm"/);assert.doesNotMatch(py,/print\([^)]*secret/);
 assert.match(wf,/AZURE_QUANTUM_CONNECTION_STRING: \$\{\{ secrets\.AZURE_QUANTUM_CONNECTION_STRING \}\}/);
 assert.equal((wf.match(/secrets\.AZURE_QUANTUM_CONNECTION_STRING/g)||[]).length,1,'secret only reaches the simulator step');
 assert.match(read('components/zeref-diary-panel.tsx'),/birth spark: IBM recorded/);
 assert.match(read('components/zeref-diary-panel.tsx'),/growth: Rigetti simulator \(simulated\)/);
});
