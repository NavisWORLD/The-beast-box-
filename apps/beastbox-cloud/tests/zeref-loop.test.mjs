import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createLoop,stepLoop,runLoop,verifyMoments,loopWellWeights,momentLine,momentRecord,normalizeInputs,MOMENT_KINDS} from '../lib/loop/loop-chain.mjs';
import {loopStatus,LINKS} from '../lib/loop/loop-status.mjs';
import {createSandField} from '../lib/pocket-sand.mjs';
import {verifyStream} from '../lib/zeref/experience-record.mjs';
import {buildBank,searchBank,bankContext,isStillLearningReply} from '../lib/knowledge/bank.mjs';

const ROOT=new URL('../../../',import.meta.url);
const read=p=>readFileSync(new URL(p,ROOT),'utf8');
const SPARK=JSON.parse(read('apps/beastbox-cloud/public/spark/zeref-bio-spark.json'));
const SEED=SPARK.heart_seed_v9_sha256;
const feed=t=>({rigetti_ticks:t%7===0?3:0,pulse:t%50<10?{bpm:70+t%9,hrv_rmssd_ms:40,sqi:.9}:null});
const j=x=>JSON.stringify(x);

test('the public bio spark is numbers only and equals the recorded evidence', () => {
  const ev=JSON.parse(read('evidence/zeref-bio-spark-001/heart-seed-v9.json'));
  assert.equal(SEED,ev.heart_seed_sha256);
  assert.deepEqual(SPARK.labels,{pulse:'MEASURED',ibm:'RECORDED',rigetti:'SIMULATED',placement:'SEEDED'});
  assert.equal(SPARK.creature_id,'bb-deada969');
  assert.ok(!/raw_(audio|video|frames)"\s*:\s*true/.test(j(SPARK)));
  assert.ok(!('envelope_1s' in SPARK)&&!('samples' in SPARK));
});

test('same inputs give the same output', () => {
  assert.equal(j(runLoop(createLoop({seed:SEED}),300,feed)),j(runLoop(createLoop({seed:SEED}),300,feed)));
});

test('different inputs give different output', () => {
  const base=runLoop(createLoop({seed:SEED}),60,feed);
  const other=[
   runLoop(createLoop({seed:SEED}),60,t=>({...feed(t),rigetti_ticks:(feed(t).rigetti_ticks||0)+1})),
   runLoop(createLoop({seed:SEED}),60,t=>({...feed(t),pulse:{bpm:90+t%9,sqi:.9}})),
   runLoop(createLoop({seed:SEED.replace(/^./,c=>c==='0'?'1':'0')}),60,feed),
   runLoop(createLoop({seed:SEED,creatures:[{id:'bb-deada969',name:'Zeref'},{id:'bb-00000001',name:'Other'}]}),60,feed)
  ];
  for(const o of other){assert.notEqual(o.head,base.head);assert.notDeepEqual(o.creatures[0].brain,base.creatures[0].brain);}
  // a different previous event changes the very next tick too
  const a=runLoop(createLoop({seed:SEED}),40,feed),b={...a,last_moment_hash:'f'.repeat(64)};
  assert.notEqual(stepLoop(a,{}).head,stepLoop(b,{}).head);
});

test('the loop advances across many ticks without idling, repeating or escaping its bounds', () => {
  let s=createLoop({seed:SEED});const heads=new Set([s.head]);const brains=new Set();
  for(let t=1;t<=3000;t++){
   const n=stepLoop(s,feed(t));
   assert.equal(n.tick,t);assert.equal(n.sim_seconds,t); // one clock, +1 every call
   assert.ok(!heads.has(n.head),'chain head repeated at tick '+t);heads.add(n.head);
   brains.add(j(n.creatures[0].brain));
   for(const x of n.creatures[0].brain)assert.ok(x>0&&x<1);
   assert.ok(Math.abs(n.wells.reduce((a,b)=>a+b,0)-4)<1e-6);
   s=n;
  }
  assert.equal(brains.size,3000);
  assert.ok(s.moments_total>100&&s.moments_total<900,'surprises happen, but not every tick: '+s.moments_total);
  assert.deepEqual(verifyMoments(s.moments).ok,true);
  assert.ok(s.moments.length<=24);
});

test('surprise moments are unscripted-looking but honest: SEEDED or SIMULATED, provenance, never "quantum random"', () => {
  const s=runLoop(createLoop({seed:SEED}),1500,feed);
  const kinds=new Set();let sim=0,seeded=0,measured=0;
  for(const m of s.moments){kinds.add(m.kind);
   assert.ok(m.label==='SEEDED'||m.label==='SIMULATED');
   assert.ok(m.provenance.includes('RECORDED '+SEED.slice(0,8)));
   assert.ok(m.provenance.includes('Rigetti ticks SIMULATED '));
   assert.ok(!/quantum random/i.test(momentLine(m)));
   if(m.label==='SIMULATED')sim++;else seeded++;
   if(m.measured_input){measured++;assert.match(m.provenance,/pulse MEASURED [\d.]+ bpm/);}else assert.match(m.provenance,/pulse none/);
  }
  assert.ok(kinds.size>=4,'a variety of moments: '+[...kinds]);
  assert.ok(sim>0&&seeded>0);
  assert.ok(MOMENT_KINDS.length>=6);
});

test('nothing is invented: a missing or poor pulse is never labelled MEASURED', () => {
  assert.equal(normalizeInputs({pulse:{bpm:5}}).pulse,null);
  assert.equal(normalizeInputs({pulse:{bpm:72,sqi:.2}}).pulse,null);
  assert.equal(normalizeInputs({}).rigetti_ticks,0);
  const s=runLoop(createLoop({seed:SEED}),800,()=>({}));
  for(const m of s.moments){assert.equal(m.label,'SEEDED');assert.equal(m.measured_input,false);}
});

test('no Math.random, no clock and no network in the loop code', () => {
  const src=read('apps/beastbox-cloud/lib/loop/loop-chain.mjs').split('\n').filter(l=>!/^\s*(\*|\/\*|\/\/)/.test(l)).join('\n');
  assert.ok(!/Math\.random|Date\.now|new Date|performance\.now|fetch\(|crypto\.getRandomValues/.test(src));
});

test('end to end: recorded seed -> loop -> pocket universe, moments -> experience records, bank -> chat, status', () => {
  // 1 inputs: RECORDED seed from the evidence, MEASURED pulse from the recorded packet numbers, SIMULATED ticks
  const s=runLoop(createLoop({seed:SEED}),400,t=>({pulse:{bpm:SPARK.pulse.bpm,hrv_rmssd_ms:SPARK.pulse.hrv_rmssd_ms,sqi:SPARK.pulse.sqi},rigetti_ticks:t%5===0?2:0}));
  assert.equal(s.tick,400);
  // 2 world: the loop tilts the real sand field through the existing environment hook; default weights untouched
  const f=createSandField({seed:'e2e',count:50});assert.deepEqual(f.wells.map(w=>w.w),[1,1,1,1]);
  f.setEnvironment(loopWellWeights(s));assert.equal(f.environment,true);assert.notDeepEqual(f.wells.map(w=>w.w),[1,1,1,1]);
  f.step(.05,[]);
  // 3 records: moments become chained experience records (provenance only)
  let prev=null;const recs=s.moments.map(m=>{const r=momentRecord(m,{prev});prev=r.hash;return r;});
  assert.ok(recs.length>3);assert.equal(verifyStream(recs).ok,true);
  assert.ok(recs.every(r=>r.simulated===true&&r.real_game_progress===false&&r.qbeast_id==='bb-deada969'));
  // 4 knowledge: a question is answered from the bank with provenance, and a name-list reply is flagged as still learning
  const bank=buildBank(JSON.parse(read('apps/beastbox-cloud/public/knowledge-bank/bank.json')));
  const ctx=bankContext(searchBank(bank,'what does RECORDED mean'));
  assert.ok(ctx.text.includes('real IBM quantum computer')&&ctx.used[0].license);
  assert.equal(isStillLearningReply('Zeref, Moonwraith, Cory'),true);
  // 5 status: every link is reported
  const st=loopStatus();assert.equal(st.links.length,LINKS.length);assert.ok(st.links.every(l=>l.status&&l.label));
  // 6 the pin-sync and the unchanged gate are part of the loop and still present
  assert.ok(existsSync(new URL('.github/workflows/zeref-bridge-pin-sync-check.yml',ROOT)));
});

test('loop status is tied to real code and tests (no fictional links)', () => {
  const ok=new Set(['wired','optin','design','outside','approval','gap']);
  for(const l of LINKS){
   assert.ok(ok.has(l.status),l.id);
   for(const c of l.code){assert.ok(existsSync(new URL(c.path,ROOT)),l.id+' missing '+c.path);assert.ok(read(c.path).includes(c.has),l.id+': '+c.path+' lacks '+c.has);}
   for(const t of l.tests)assert.ok(existsSync(new URL(t,ROOT)),l.id+' missing test '+t);
  }
  const by=Object.fromEntries(LINKS.map(l=>[l.id,l.status]));
  assert.equal(by['creature-birth-dna'],'design');assert.equal(by['diary-genesis'],'design');
  assert.equal(by['records-to-training-mix'],'approval');
  // known gaps are reported as gaps, never hidden
  assert.equal(by['moments-to-pocket-view'],'gap');assert.equal(by['bio-to-chat-context'],'gap');assert.equal(by['spark-latest-pointer'],'wired');
  // new behaviour stays opt-in
  assert.match(read('apps/beastbox-cloud/components/pocket-sand-layer.ts'),/getItem\(LOOP_WORLD_KEY\)==='on'/);
});
