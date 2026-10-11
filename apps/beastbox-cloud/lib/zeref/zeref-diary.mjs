/**
 * ZEREF'S DIARY — the deterministic "forever loop" step.
 *
 * A scheduled GitHub Actions job (.github/workflows/zeref-diary-loop.yml)
 * calls stepDiary() roughly every 30 minutes. Each tick replays a short,
 * seeded exploration of the Cage pocket with the same mind + pocket rules the
 * browser uses, drifts Zeref's signals, grants growth XP and appends ONE
 * hash-chained entry to the diary (append-only, verifiable with verifyChain).
 *
 * Honest boundaries:
 *  - Seeded from RECORDED IBM counts (the shipped Moonwraith shard), plus the
 *    tick number and elapsed time. Not a live quantum link.
 *  - Zeref is a game companion; "thoughts" are generated lines (a template
 *    unless an owner-approved model is configured), not a conscious mind.
 *  - The identity block (beast id + recorded digest) is fixed at genesis and
 *    never rewritten; entries only reference the beast id.
 *
 * Pure: no filesystem, no network, no clock. The caller supplies `now`.
 */
import {ZEREF_PROFILE,ZEREF_RECORDED_SOURCE,createMind,describeMind,frameFor,nextRandom,recordedSeed,stepMind} from './zeref-mind.mjs';
import {blendFrame,createPocket,sampleCombo,stepPocket} from './zeref-pocket.mjs';
import {canonicalJson} from '../../public/spark/genome.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';

export const DIARY_SCHEMA='zeref-diary/v1';
export const DIARY_TIMEZONE='America/Chicago';
export const SIM_SECONDS=90;
export const SIM_DT=.1;
export const STAGES=Object.freeze([
 Object.freeze({stage:1,name:'Moonling',xp:0}),
 Object.freeze({stage:2,name:'Duskwing',xp:300}),
 Object.freeze({stage:3,name:'Eclipse Prowler',xp:1200}),
 Object.freeze({stage:4,name:'Void Moonwraith',xp:3600}),
 Object.freeze({stage:5,name:'Crescent Sovereign',xp:9000})
]);
export const XP_PER_TICK=10,XP_PER_COMBO=3,XP_PER_CARE=5,CARE_CAP_PER_TICK=20;
export const DIARY_LABELS=Object.freeze({
 seed:'Seeded from recorded IBM ibm_marrakesh counts (job db4te7slf4us73c3888g). Not a live quantum link.',
 mind:'Zeref is a game companion with a deterministic mind. Diary lines are generated, not a conscious mind.',
 loop:'Written by the scheduled Zeref diary loop (GitHub Actions), one hash-chained entry per tick.',
 growth:'Growth ticks run a small circuit on the free Azure Quantum Rigetti QVM simulator (simulated, not hardware). If it fails, the deterministic step runs and the real error is logged.'
});

export const BIRTH_SPARK=Object.freeze({provider:'IBM Quantum',backend:'ibm_marrakesh',job_id:'db4te7slf4us73c3888g',source:'recorded hardware counts (birth seed, never re-run)'});
export const QVM_TARGET='rigetti.sim.qvm';
export const QVM_SHOTS=256;
export const QVM_BITS=3;

const clamp=(v,lo,hi)=>Math.min(hi,Math.max(lo,v));
const r1=v=>Math.round(v*10)/10;
export function stageFor(xp){let s=STAGES[0];for(const x of STAGES)if(xp>=x.xp)s=x;return s;}
export function nextStage(xp){return STAGES.find(x=>x.xp>xp)||null;}
export function localHour(iso,tz=DIARY_TIMEZONE){
 const h=new Intl.DateTimeFormat('en-US',{timeZone:tz,hour:'numeric',hourCycle:'h23'}).format(new Date(iso));
 return Number(h)%24;
}
function hash32(text){let h=0x811c9dc5;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}

/**
 * The growth circuit for the NEXT tick, parameterised from Zeref's current
 * signals: RY(energy) RY(signal) RX(resonance), then a CNOT chain. Quil text
 * for the free Azure Quantum Rigetti QVM simulator. Pure + deterministic.
 */
export function planGrowthCircuit(state){
 const s=state.signals,tick=state.tick+1;
 const ang=v=>Math.round(Math.PI*clamp(Number(v)||0,0,100)/100*1e6)/1e6;
 const params={energy:ang(s.energy),signal:ang(s.signal),resonance:ang(s.resonance)};
 const quil=['DECLARE ro BIT[3]',`RY(${params.energy}) 0`,`RY(${params.signal}) 1`,`RX(${params.resonance}) 2`,'CNOT 0 1','CNOT 1 2',
  'MEASURE 0 ro[0]','MEASURE 1 ro[1]','MEASURE 2 ro[2]'].join('\n')+'\n';
 return {schema:'zeref-growth-circuit/v1',tick,target:QVM_TARGET,shots:QVM_SHOTS,params,quil,quil_sha256:sha256Hex(quil),
  job_name:`zeref-diary-tick-${tick}-${state.identity.beast_id}`};
}

/** Validate simulator counts; returns features or null. */
export function countsFeatures(counts,shots=QVM_SHOTS){
 if(!counts||typeof counts!=='object')return null;
 const keys=Object.keys(counts);
 if(!keys.length||keys.some(k=>!/^[01]{3}$/.test(k)))return null;
 const total=keys.reduce((t,k)=>t+(Number.isInteger(counts[k])&&counts[k]>=0?counts[k]:NaN),0);
 if(total!==shots)return null;
 const p=i=>keys.reduce((t,k)=>t+(k[i]==='1'?counts[k]:0),0)/total;
 const odd=keys.reduce((t,k)=>t+((k.split('').filter(c=>c==='1').length%2)?counts[k]:0),0)/total;
 const ent=-keys.reduce((t,k)=>{const q=counts[k]/total;return q>0?t+q*Math.log2(q):t;},0)/3;
 return {p0:p(0),p1:p(1),p2:p(2),odd,entropy:ent};
}

/** Tick-0 state. The identity block is written once here and copied verbatim forever after. */
export function genesisState({profile=ZEREF_PROFILE,source=ZEREF_RECORDED_SOURCE}={}){
 const seed=recordedSeed(source);
 return {
  schema:DIARY_SCHEMA,
  identity:{beast_id:profile.id,name:profile.name,title:profile.title,recorded_digest:seed.digest,
   backend:source.backend,job_id:source.job_id,source_path:source.path,source_class:source.source_class},
  tick:0,xp:0,stage:1,stage_name:STAGES[0].name,
  signals:{energy:profile.stats.energy,signal:profile.stats.signal,memory:profile.stats.memory,resonance:profile.stats.resonance},
  bond:0,care_total:0,combos_known:[],places:{},last_tick_at:null,last_entry_hash:null
 };
}

const OPENERS={
 sleepy:['The moon pool was warm tonight.','I curled up where the light pools.','Slow blinks. Soft stars.'],
 'charged up':['The crystals hummed back at me!','My crescent is still buzzing.','Resonance up, up, up.'],
 curious:['Something on the other side of the rift moved.','I found a seam in the pocket and stared at it.','New smell near the gate. Investigating.'],
 exploring:['I patrolled every corner of my little universe.','Paws on the grid, nose to the stars.','Long walk. Good walk.'],
 playful:['Pounced on a drifting spark. Missed. Pounced again.','I chased my own tail through a portal.','Stardust is for catching.'],
 floaty:['Wings on. I floated over the whole pocket.','Hovered so high the grid looked tiny.','Drifting between realities again.'],
 content:['Quiet tick. I like quiet ticks.','Just being here is nice.','Purring at nothing in particular.'],
 affectionate:['Slow blink for whoever is reading this.','I saved a warm spot for you.','I remember the last visit.']
};
/** Deterministic diary line from state (no model). */
export function templateThought({mood,place,newCombos,stage,grew,rng,spark=null}){
 const pick=a=>a[Math.floor(rng()*a.length)%a.length];
 const opener=pick(OPENERS[mood]||OPENERS.content);
 const bits=[opener];
 if(place)bits.push(`Spent most of the tick at ${place}.`);
 if(spark)bits.push(spark.odd>.5?'The simulator sparks fizzed odd and restless.':'The simulator sparks lined up even and calm.');
 if(newCombos>0)bits.push(newCombos===1?'My body did a new combination of moves.':`My body tried ${newCombos} new move combinations.`);
 if(grew)bits.push(`I feel bigger. Stage ${grew}.`);
 else if(stage>=3&&rng()<.3)bits.push('The pocket feels smaller than it used to.');
 return bits.join(' ');
}

/** Hash of an entry without its own hash field. */
export function entryHash(entry){const {hash,...rest}=entry;return sha256Hex(canonicalJson(rest));}

/**
 * One loop tick. Returns {state,entry}. Never mutates the input state.
 * care = real care events supplied by the caller for this tick (bounded).
 * thought = optional {text,by} from an owner-approved model; otherwise template.
 */
export function stepDiary(prev,{now,care=0,thought=null,growth=null}={}){
 if(!prev||prev.schema!==DIARY_SCHEMA)throw Error('Unknown diary state schema.');
 if(!now||Number.isNaN(Date.parse(now)))throw Error('stepDiary needs an ISO `now`.');
 if(prev.last_tick_at&&Date.parse(now)<=Date.parse(prev.last_tick_at))throw Error('Diary time must move forward.');
 const state=JSON.parse(JSON.stringify(prev));
 const identity=prev.identity;
 const tick=prev.tick+1;
 const hour=localHour(now);
 const night=hour>=22||hour<6;
 const elapsedH=prev.last_tick_at?clamp((Date.parse(now)-Date.parse(prev.last_tick_at))/3.6e6,0,48):.5;
 const rngState={rng:hash32(identity.recorded_digest+':tick:'+tick)|0};
 const rng=()=>nextRandom(rngState);
 const seed=recordedSeed();
 // Signals drift: rest at night, spend energy by day; resonance breathes slowly.
 // Growth source: real counts from the free Rigetti QVM SIMULATOR when this tick's job succeeded,
 // otherwise the deterministic step with the real error recorded. Counts are never invented.
 const plan=planGrowthCircuit(prev);
 let growthSource,q=null;
 if(growth&&growth.ok){
  q=countsFeatures(growth.counts,Number(growth.shots));
  if(q&&growth.target===QVM_TARGET&&growth.job_id)growthSource={kind:'rigetti-qvm-simulated',simulated:true,provider:'azure-quantum/rigetti',target:growth.target,
   job_id:String(growth.job_id),job_name:String(growth.job_name||''),shots:Number(growth.shots),counts:Object.fromEntries(Object.keys(growth.counts).sort().map(k=>[k,growth.counts[k]])),
   counts_sha256:sha256Hex(canonicalJson(growth.counts)),circuit_params:plan.params,quil_sha256:plan.quil_sha256};
  else{q=null;growthSource={kind:'deterministic-fallback',simulated:false,provider:'azure-quantum/rigetti',target:String(growth.target||QVM_TARGET),job_id:growth.job_id?String(growth.job_id):null,error:'invalid simulator counts or target; counts ignored'};}
 }else growthSource={kind:'deterministic-fallback',simulated:false,provider:'azure-quantum/rigetti',target:QVM_TARGET,job_id:growth?.job_id?String(growth.job_id):null,
  error:growth?.error?String(growth.error).slice(0,300):'no simulator job this tick'};
 if(q)rngState.rng=(rngState.rng^parseInt(growthSource.counts_sha256.slice(0,8),16))|0;
 const s=state.signals;
 s.energy=Math.round(clamp(s.energy+(night?10:-5)*Math.min(2,elapsedH*2)+(q?(q.p0-.5)*10:(rng()-.5)*8),15,100));
 s.signal=Math.round(clamp(s.signal+(seed.features.lean*3)+(q?(q.p1-.5)*8:(rng()-.5)*6),30,100));
 s.memory=Math.round(clamp(s.memory+.5,0,100));
 s.resonance=Math.round(clamp(88+Math.sin(tick/7)*6+seed.features.xxEven*4+(q?(q.p2-.5)*4:(rng()-.5)*3),0,100));
 const careN=clamp(Math.floor(Number(care)||0),0,CARE_CAP_PER_TICK);
 state.care_total+=careN;state.bond=clamp(state.bond+careN*2+.25,0,100);
 // Replay a seeded exploration with the same mind + pocket the browser uses.
 const profile={...ZEREF_PROFILE,stats:{...s}};
 const m=createMind({profile,care:{energy:s.energy,bond:state.bond},hour});
 m.rng=(hash32(identity.recorded_digest+':mind:'+tick)^(q?parseInt(growthSource.counts_sha256.slice(8,16),16):0))|0;
 const p=createPocket({digest:identity.recorded_digest,key:identity.beast_id});
 p.rng=(hash32(identity.recorded_digest+':walk:'+tick)^(q?parseInt(growthSource.counts_sha256.slice(16,24),16):0))|0;
 const known=new Set(prev.combos_known);const fresh=[];const visits={};const moods={};
 for(let i=0;i<SIM_SECONDS/SIM_DT;i++){
  stepMind(m,SIM_DT,{hour});
  for(const ev of stepPocket(p,m,SIM_DT))if(ev.type==='arrive')visits[ev.name]=(visits[ev.name]||0)+1;
  const f=blendFrame(frameFor(m),p,m,{stage:prev.stage});
  const c=sampleCombo(p,f,m);
  if(c&&!known.has(c.key)){known.add(c.key);fresh.push({key:c.key,name:c.name});}
  const mood=describeMind(m).mood;moods[mood]=(moods[mood]||0)+1;
 }
 const mood=Object.entries(moods).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0][0];
 const place=Object.entries(visits).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0]?.[0]||null;
 for(const [k,v] of Object.entries(visits))state.places[k]=(state.places[k]||0)+v;
 const xpGain=XP_PER_TICK+fresh.length*XP_PER_COMBO+careN*XP_PER_CARE+(q?Math.round(q.entropy*6):0);
 state.xp=prev.xp+xpGain;
 const st=stageFor(state.xp);const grew=st.stage>prev.stage?st.stage:0;
 state.stage=st.stage;state.stage_name=st.name;
 state.combos_known=[...prev.combos_known,...fresh.map(c=>c.key)];
 state.tick=tick;state.last_tick_at=now;
 const line=thought&&typeof thought.text==='string'&&thought.text.trim()&&thought.by
  ?{text:thought.text.trim().slice(0,280),by:String(thought.by)}
  :{text:templateThought({mood,place,newCombos:fresh.length,stage:st.stage,grew,rng,spark:q}),by:'deterministic-template'};
 const entry={
  schema:DIARY_SCHEMA,beast_id:identity.beast_id,tick,at:now,hour_local:hour,timezone:DIARY_TIMEZONE,
  signals:{...s},bond:r1(state.bond),mood,place,places_visited:Object.keys(visits).sort(),
  discovered_combos:fresh.slice(0,5),new_combo_count:fresh.length,combos_total:state.combos_known.length,
  xp_gain:xpGain,xp:state.xp,stage:st.stage,stage_name:st.name,grew:Boolean(grew),care:careN,
  birth_spark:BIRTH_SPARK,growth_source:growthSource,
  thought:line,prev_hash:prev.last_entry_hash,hash:''
 };
 entry.hash=entryHash(entry);
 state.last_entry_hash=entry.hash;
 return {state,entry};
}

/** Verify an append-only, hash-chained diary. Returns {ok,reason?,tick}. */
export function verifyChain(entries,identity){
 let prev=null,tick=0;
 for(const e of entries){
  if(e.schema!==DIARY_SCHEMA)return{ok:false,reason:'schema',tick:e.tick};
  if(identity&&e.beast_id!==identity.beast_id)return{ok:false,reason:'identity',tick:e.tick};
  if(e.tick!==tick+1)return{ok:false,reason:'tick-gap',tick:e.tick};
  if(e.prev_hash!==prev)return{ok:false,reason:'chain',tick:e.tick};
  if(entryHash(e)!==e.hash)return{ok:false,reason:'hash',tick:e.tick};
  prev=e.hash;tick=e.tick;
 }
 return {ok:true,tick,head:prev};
}

/** Small public summary served to the site (no combos_known list). */
export function summarize(state,entries,limit=12){
 const {combos_known,...rest}=state;
 const ns=nextStage(state.xp);
 return {...rest,combos_total:combos_known.length,next_stage:ns?{stage:ns.stage,name:ns.name,xp:ns.xp}:null,
  labels:DIARY_LABELS,birth_spark:BIRTH_SPARK,recent:entries.slice(-limit).reverse()};
}
