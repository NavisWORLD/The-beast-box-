import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {ZEREF_PROFILE,ZEREF_RECORDED_SOURCE,BEHAVIORS,REACTIONS,LOCOMOTION,recordedSeed,createMind,stepMind,tapMind,greetMind,forceBehavior,frameFor,describeMind,behaviorWeights} from '../lib/zeref/zeref-mind.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');

// Scripted, reproducible "visitor": pointer bursts and a few taps at fixed times.
function run(options={},seconds=600,script=true){
 const m=createMind({hour:14,...options});const timeline=[];let last='';
 for(let i=0;i<seconds*20;i++){
  const pointer=script&&i%600<15?{x:Math.sin(i/40),y:-.3,moved:true}:undefined;
  stepMind(m,.05,{hour:14,pointer});
  if(script&&i%2400===1200)tapMind(m);
  const s=describeMind(m).state;if(s!==last){last=s;timeline.push(`${m.t.toFixed(2)}:${s}`);}
 }
 return {m,timeline};
}

test('Zeref seed comes from the shipped recorded IBM counts, digest-verified',()=>{
 const shard=JSON.parse(read('public/spark/ibm-moonwraith-cassette-kit-20261010.json'));
 assert.equal(shard.source_class,'RECORDED_IBM_HARDWARE');
 assert.deepEqual(ZEREF_RECORDED_SOURCE.rows.map(r=>({...r})),shard.runs,'inline rows must equal the public recorded shard');
 assert.equal(ZEREF_RECORDED_SOURCE.job_id,shard.job_id);
 const seed=recordedSeed();
 assert.match(seed.digest,/^[a-f0-9]{64}$/);
 assert.equal(seed.shots,8192);assert.equal(seed.backend,'ibm_marrakesh');
 assert.ok(seed.features.zzOdd>.9&&seed.features.xxEven>.9,'bell parities read from counts');
 const tampered={...ZEREF_RECORDED_SOURCE,rows:[{...ZEREF_RECORDED_SOURCE.rows[0],c:'00:129,01:1917,10:1907,11:143'},ZEREF_RECORDED_SOURCE.rows[1]]};
 assert.throws(()=>recordedSeed(tampered),/digest/i,'tampered counts are rejected');
 assert.deepEqual(ZEREF_PROFILE.stats,{energy:90,signal:78,memory:62,resonance:95});
 assert.equal(ZEREF_PROFILE.id,'bb-7f9c2a03');
});

test('same seed + same inputs = identical behaviour timeline; another beast differs',()=>{
 const a=run(),b=run();
 assert.deepEqual(a.timeline,b.timeline);
 assert.deepEqual(a.m.expr,b.m.expr);
 assert.equal(a.m.rng,b.m.rng);
 const other=run({profile:{...ZEREF_PROFILE,id:'bb-00000001'}});
 assert.notDeepEqual(other.timeline,a.timeline,'personality is per-beast');
});

test('over a session every one of the 8 atlas behaviours appears',()=>{
 const {m}=run({},1800);
 const seen=new Set(m.history);
 const {timeline}=run({},1800);
 const states=new Set(timeline.map(x=>x.split(':')[1]));
 for(const b of BEHAVIORS)assert.ok(states.has(b),`missing behaviour ${b}`);
 assert.ok(seen.size>0);
});

test('taps change state: reaction, sleeping wake-up, over-tapping and long-press purr',()=>{
 const m=createMind();stepMind(m,.05);
 const r=tapMind(m);assert.ok(REACTIONS.includes(r));
 assert.equal(describeMind(m).state,r);assert.equal(describeMind(m).mood,{happy:'happy',startled:'startled',purr:'purring'}[r]);
 const bond=m.bond;
 for(let i=0;i<40;i++)stepMind(m,.1);
 assert.equal(m.reaction,null,'reaction ends and returns to ambient life');
 assert.ok(bond>0);
 forceBehavior(m,'sleep');assert.equal(tapMind(m),'startled','tapping a sleeping beast startles it awake');
 for(let i=0;i<40;i++)stepMind(m,.1);
 assert.equal(tapMind(m,{hold:true}),'purr','press-and-hold is petting');
 const q=createMind();stepMind(q,.05);let last;for(let i=0;i<4;i++){last=tapMind(q);stepMind(q,.1);}
 assert.equal(last,'startled','four rapid taps startle');
 const g=createMind();assert.equal(greetMind(g),'happy');
});

test('expressions blend smoothly and match the mood',()=>{
 const m=createMind();let prev={...m.expr};let maxJump=0;
 forceBehavior(m,'curious');
 for(let i=0;i<60;i++){stepMind(m,1/60);for(const k of Object.keys(prev))maxJump=Math.max(maxJump,Math.abs(m.expr[k]-prev[k]));prev={...m.expr};}
 assert.ok(maxJump<.12,`no expression snaps (max per-frame change ${maxJump})`);
 assert.ok(m.expr.o>.4&&m.expr.brow>.5,'curious: o-mouth, raised brows');
 forceBehavior(m,'sleep');for(let i=0;i<60;i++)stepMind(m,.05);
 const f=frameFor(m);assert.ok(f.lid>.9&&f.mouth.sleepy>.7&&f.fx.zzz===1,'sleep: closed eyes, sleepy mouth, zzz');
 const mouthSum=Object.values(f.mouth).reduce((s,v)=>s+v,0);assert.ok(Math.abs(mouthSum-1)<.05,'mouth shapes are a normalised blend');
});

test('care stats drive behaviour: low energy sleeps, high resonance charges more',()=>{
 const tired=createMind({care:{energy:12}});
 assert.equal(tired.behavior,'sleep');
 stepMind(tired,.05);assert.equal(describeMind(tired).mood,'sleepy');
 const count=(profile)=>run({profile},1800,false).m.history.filter(b=>b==='charge').length;
 const hi=count(ZEREF_PROFILE),lo=count({...ZEREF_PROFILE,stats:{...ZEREF_PROFILE.stats,resonance:10}});
 assert.ok(hi>lo,`resonance 95 charges (${hi}) more than resonance 10 (${lo})`);
 const night=createMind({hour:2}),day=createMind({hour:14});
 assert.ok(behaviorWeights(night).sleep>behaviorWeights(day).sleep,'night time is sleepier');
});

test('reduced motion: no locomotion, zero motion amplitudes, taps still change expression',()=>{
 const m=createMind({reduced:true});
 for(let i=0;i<20*900;i++){
  stepMind(m,.05,{hour:14});
  const f=frameFor(m);
  assert.equal(f.floatY,0);assert.equal(f.floatX,0);assert.equal(f.wingL,0);assert.equal(f.tail,0);assert.equal(f.rot,0);
 }
 assert.ok(!m.history.some(b=>LOCOMOTION.includes(b)),'no pounce/walk/hover/charge under reduced motion');
 assert.equal(forceBehavior(m,'pounce'),'idle');
 const before={...m.expr};tapMind(m);
 assert.notDeepEqual(m.expr,before,'tap snaps a new expression immediately');
});

test('the home hero and support mascot use Zeref while keeping existing systems',()=>{
 const hero=read('components/homepage-creature.tsx');
 assert.match(hero,/<ZerefMoonwraith/);
 assert.match(hero,/useState<View>\('zeref'\)/,'Zeref is the default guide');
 assert.match(hero,/CosmicCompanion3D quality="low"/,'3D guide kept one tap away');
 assert.match(hero,/preferSprite=\{Boolean\(genome\)\}/,'saved QBEAST keeps its own sprite');
 assert.match(hero,/not a live quantum link/);
 const live=read('components/zeref-moonwraith.tsx');
 assert.match(live,/requestAnimationFrame/);assert.match(live,/visibilitychange/);assert.match(live,/useUniverseMotion/);
 assert.doesNotMatch(live+read('lib/zeref/zeref-mind.mjs'),/localStorage\.setItem|fetch\(|change\(/,'visual only: no storage writes or network');
 const mascot=read('components/support-mascot.tsx');
 assert.match(mascot,/<ZerefFigure/);assert.ok(!mascot.includes('rotate(${i*30})')&&!mascot.includes('#${petal}'),'old petal puff body removed');
 assert.match(read('components/zeref-figure.tsx'),/support-mascot-breathe/,'reduced-motion CSS hook kept for the shrine');
});
