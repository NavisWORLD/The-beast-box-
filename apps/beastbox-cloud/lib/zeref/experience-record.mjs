/**
 * ZEREF EXPERIENCE RECORD — one canonical, versioned
 *   observation -> decision -> action -> outcome -> reward -> memory
 * record for every place a Beast can have an experience, with the ORIGIN of
 * that experience stated explicitly and never relabelled.
 *
 * Origins (closed list):
 *  - live_browser                      a real visitor's browser (pocket rAF loop)
 *  - original_native_rom               the original Lost COSMOS GBA ROM in an emulator
 *  - deterministic_pocket_simulation   the seeded pocket rules replayed offline (diary loop, experiments)
 *  - azure_rigetti_qvm_simulation      counts from the free Rigetti QVM SIMULATOR (simulated, not hardware)
 *  - ibm_recorded_historical           recorded IBM hardware counts (birth spark; never re-run)
 *
 * Label kinds (what a number means, never mixed):
 *  - observed_outcome   what actually happened after the action (moved, blocked, new cell, ACK)
 *  - computed_reward    a reward computed by a fixed rule from the observed outcome
 *  - heuristic_target   an action a hand-written heuristic would have chosen
 *  - imitation_target   an action copied from a scripted teacher / demonstration
 *  - human_feedback     an explicit rating from the owner (requires consent)
 *
 * Consent: public game events are the default. private_interaction,
 * microphone and chat scopes are NEVER training-eligible unless the owner
 * explicitly approved that scope. Raw audio and chat text are never stored here.
 *
 * Pure: no DOM, storage, clock or network. Same canonical JSON + SHA-256 as the diary.
 */
import {canonicalJson} from '../../public/spark/genome.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';

export const EXPERIENCE_SCHEMA='zeref-experience/v1';
export const ORIGINS=Object.freeze(['live_browser','original_native_rom','deterministic_pocket_simulation','azure_rigetti_qvm_simulation','ibm_recorded_historical']);
export const LABEL_KINDS=Object.freeze(['observed_outcome','computed_reward','heuristic_target','imitation_target','human_feedback']);
export const CONSENT_SCOPES=Object.freeze(['public_game_event','private_interaction','microphone','chat','approved_computation']);
export const ACTIONS=Object.freeze(['UP','DOWN','LEFT','RIGHT','A','B','WAIT']);
/** Origins whose records describe an action the Beast took (others are state inputs only). */
export const ACTION_ORIGINS=Object.freeze(['live_browser','original_native_rom','deterministic_pocket_simulation']);
const PRIVATE=new Set(['private_interaction','microphone','chat']);
const r4=v=>Number.isFinite(Number(v))?Math.round(Number(v)*1e4)/1e4:null;

/** Hash of the record body (everything except `hash`). */
export function recordHash(rec){const {hash,...body}=rec;return sha256Hex(canonicalJson(body));}

/**
 * Build a record. `prev` is the previous record hash in this stream (or null).
 * Throws on anything that would blur provenance.
 */
export function makeRecord({qbeast_id,origin,consent={scope:'public_game_event',owner_approved:false},episode=null,step=null,
 observation,decision,action,outcome,reward=null,memory=null,labels=[],source={},prev=null}){
 if(!/^bb-[0-9a-f]{8}$/.test(String(qbeast_id||'')))throw Error('experience: invalid qbeast id');
 if(!ORIGINS.includes(origin))throw Error('experience: unknown origin '+origin);
 if(!CONSENT_SCOPES.includes(consent?.scope))throw Error('experience: unknown consent scope');
 const takesAction=ACTION_ORIGINS.includes(origin);
 if(takesAction&&!ACTIONS.includes(action?.key))throw Error('experience: action origins need a legal action key');
 if(!takesAction&&action)throw Error('experience: '+origin+' is a state input, not an action the Beast took');
 for(const l of labels)if(!LABEL_KINDS.includes(l.kind))throw Error('experience: unknown label kind '+l.kind);
 if(reward&&reward.kind!=='computed_reward'&&reward.kind!=='human_feedback')throw Error('experience: reward must be computed_reward or human_feedback');
 if(reward?.kind==='human_feedback'&&!consent.owner_approved)throw Error('experience: human feedback needs owner approval');
 const rec={schema:EXPERIENCE_SCHEMA,qbeast_id,origin,
  simulated:origin==='deterministic_pocket_simulation'||origin==='azure_rigetti_qvm_simulation',
  real_game_progress:false, // only an instrumented native objective event may ever set this, never a simulation
  consent:{scope:consent.scope,owner_approved:Boolean(consent.owner_approved)},
  episode,step,observation:observation??null,decision:decision??null,action:action??null,outcome:outcome??null,
  reward:reward?{kind:reward.kind,value:r4(reward.value),rule:String(reward.rule||'')}:null,
  memory:memory??null,labels:labels.map(l=>({kind:l.kind,value:l.value??null,by:String(l.by||'')})),
  source:{ref:String(source.ref||''),sha256:source.sha256?String(source.sha256):null},prev_hash:prev,hash:''};
 rec.hash=recordHash(rec);
 return rec;
}

/** Verify a stream: schema, hashes and chain. Returns {ok, reason?, index?, head}. */
export function verifyStream(records){
 let prev=null;
 for(let i=0;i<records.length;i++){
  const r=records[i];
  if(r.schema!==EXPERIENCE_SCHEMA)return{ok:false,reason:'schema',index:i};
  if(!ORIGINS.includes(r.origin))return{ok:false,reason:'origin',index:i};
  if(r.prev_hash!==prev)return{ok:false,reason:'chain',index:i};
  if(recordHash(r)!==r.hash)return{ok:false,reason:'hash',index:i};
  if(r.simulated&&r.real_game_progress)return{ok:false,reason:'simulation-claims-game-progress',index:i};
  prev=r.hash;
 }
 return {ok:true,head:prev,count:records.length};
}

/**
 * May this record be used to train the given identity's neural policy?
 * Returns {ok, why}. Default-deny for private scopes and other identities.
 */
export function trainingEligible(rec,{identity,approvedScopes=[],approvedAssociations=[]}={}){
 if(!ACTION_ORIGINS.includes(rec.origin))return{ok:false,why:'state-input origin (quantum/recorded) is provenance, not a training action'};
 if(PRIVATE.has(rec.consent.scope)&&!(rec.consent.owner_approved&&approvedScopes.includes(rec.consent.scope)))return{ok:false,why:'private scope without explicit owner approval'};
 if(rec.qbeast_id!==identity&&!approvedAssociations.some(a=>a.subject===rec.qbeast_id&&a.object===identity&&a.status==='APPROVED'))
  return{ok:false,why:'different identity and no APPROVED association'};
 return{ok:true,why:'eligible'};
}

/* ------------------------------ adapters ------------------------------ */

/**
 * Pocket stepPocket() events -> records (origin is the caller's: live_browser
 * in a visitor's tab, deterministic_pocket_simulation in the diary/experiments).
 * The continuous pocket has goals, not keys, so the action key is the dominant
 * grid direction of travel (WAIT for rest).
 */
export function pocketEventRecords(events,{qbeast_id,origin,p,learner,energy,prev=null,consent}){
 const out=[];
 const dir=(dx,dy)=>Math.abs(dx)>=Math.abs(dy)?(dx<0?'LEFT':'RIGHT'):(dy<0?'UP':'DOWN');
 for(const ev of events){
  if(!['blocked','new-cell','arrive','explored','came'].includes(ev.type)&&!(ev.type==='decide'&&ev.goal==='rest'))continue;
  const t=p.target||{x:p.x,y:p.y};
  const key=ev.type==='decide'?'WAIT':dir(t.x-p.x,t.y-p.y);
  const outcome={kind:ev.type==='decide'?'rested':ev.type,cell:ev.cell??p.cell,poi:ev.poi??null};
  const reward=ev.type==='blocked'?-1:ev.type==='new-cell'?1:ev.type==='arrive'?.5:0;
  const rec=makeRecord({qbeast_id,origin,consent,step:Math.round(p.t*10),
   observation:{cell:p.cell,energy:r4(energy),near:(p.pois||[]).map(o=>({kind:o.kind,d:r4(Math.hypot(o.x-p.x,o.y-p.y))})).sort((a,b)=>a.d-b.d).slice(0,3)},
   decision:{policy:'pocket-learner/v1',goal:p.goal||ev.goal||null},action:{key},outcome:{...outcome,observed:true},
   reward:{kind:'computed_reward',value:reward,rule:'pocket-v1: new cell +1, arrive +0.5, blocked -1, else 0'},
   memory:learner?{cells_visited:learner.cells.filter(v=>v>0).length,known_rifts:[...learner.known_blocked],moves:{...learner.moves}}:null,
   labels:[{kind:'observed_outcome',value:outcome.kind,by:'pocket-rules'}],source:{ref:'zeref-pocket/v1'},prev});
  out.push(rec);prev=rec.hash;
 }
 return out;
}

/** A diary loop Rigetti QVM receipt -> state-input record (simulated; never an action). */
export function qvmReceiptRecord(growth,{qbeast_id,prev=null}){
 if(!growth||growth.kind!=='rigetti-qvm-simulated')throw Error('experience: not a simulated QVM growth source');
 return makeRecord({qbeast_id,origin:'azure_rigetti_qvm_simulation',consent:{scope:'approved_computation',owner_approved:true},
  observation:{target:growth.target,shots:growth.shots,counts:growth.counts,circuit_params:growth.circuit_params},
  outcome:{kind:'simulator_counts',observed:true},labels:[{kind:'observed_outcome',value:'simulator_counts',by:growth.target}],
  source:{ref:'azure-quantum job '+growth.job_id,sha256:growth.counts_sha256},prev});
}

/** Recorded IBM birth spark -> provenance record (historical; never re-run, never an action). */
export function ibmRecordedRecord({job_id,backend,counts_sha256},{qbeast_id,prev=null}){
 return makeRecord({qbeast_id,origin:'ibm_recorded_historical',consent:{scope:'approved_computation',owner_approved:true},
  observation:{job_id,backend},outcome:{kind:'recorded_hardware_counts',observed:true},
  labels:[{kind:'observed_outcome',value:'birth_spark',by:backend}],source:{ref:'ibm '+job_id,sha256:counts_sha256||null},prev});
}

/**
 * A verified diary entry -> records: its QVM growth input (if simulated counts)
 * plus one pocket summary record. Diary thought text is NOT copied; we keep only
 * whether it was deterministic template narrative or model-generated dialogue.
 */
export function diaryEntryRecords(entry,{prev=null}={}){
 const out=[];
 if(entry.growth_source?.kind==='rigetti-qvm-simulated'){const r=qvmReceiptRecord(entry.growth_source,{qbeast_id:entry.beast_id,prev});out.push(r);prev=r.hash;}
 const L=entry.learning||{};
 const r=makeRecord({qbeast_id:entry.beast_id,origin:'deterministic_pocket_simulation',consent:{scope:'public_game_event',owner_approved:false},
  episode:entry.tick,observation:{signals:entry.signals,place:entry.place},decision:{policy:'pocket-learner/v1',goals:L.goals||{}},
  action:{key:'WAIT'}, // summary of a 90 s replay, not a single key press: not usable as a per-step training target
  outcome:{kind:'diary_tick_summary',observed:true,new_cells:L.new_cells??null,moves_succeeded:L.moves_succeeded??null,moves_blocked:L.moves_blocked??null},
  memory:{cells_visited:L.cells_visited??null,known_rifts:L.known_rifts??null,favorite_spot:L.favorite_spot??null},
  labels:[{kind:'observed_outcome',value:'diary_tick_summary',by:'zeref-diary/v1'},
   {kind:'observed_outcome',value:entry.thought?.by==='deterministic-template'?'narrative:deterministic_template':'narrative:model_generated',by:String(entry.thought?.by||'')}],
  source:{ref:'zeref-diary tick '+entry.tick,sha256:entry.hash},prev});
 out.push(r);
 return out;
}
