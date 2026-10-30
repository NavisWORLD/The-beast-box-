/**
 * FOREVER CONNECTION — Zeref's continuity layer over his EXISTING Azure folder.
 *
 * What already existed (see docs/forever-connection/AUDIT.md): the per-beast
 * Azure folders (cosmos-store.mjs), Zeref's cloud memory (zeref-cloud.mjs:
 * profile / model pin / approved experiences / approved lessons), the
 * hash-chained diary on the zeref-diary branch, and a bridge whose guest
 * contract accepts exactly {text, guest_identity} — no context fields.
 *
 * What this adds, and only this:
 *   beasts/bb-deada969/guestbook/threads/<id>.json  one public conversation
 *     thread per system-issued guest cookie. Written ONLY by the server,
 *     AFTER a bridge reply has passed the same verification as /api/guest.
 *   beasts/bb-deada969/guestbook/events.jsonl       bounded tail of
 *     guest-origin exchange events (counts and step only, never guest text).
 *
 * Guest-origin records are labelled training_eligible:false everywhere and
 * live outside diary.jsonl / lessons/ / experiences/, so no guest words can
 * reach his identity, his diary chain, or any training path. Guests read his
 * persisted state; they cannot write into him.
 *
 * Continuity reaches his mouth the only way the bridge contract allows:
 * composed into the prompt text (the renderContextPrompt pattern), sourced
 * from the persisted store instead of a browser session.
 */
import {createHmac,randomBytes} from 'node:crypto';
import {getBlob,putBlob,listBlobs} from './azure-blob.mjs';
import {ZEREF_DIR} from './zeref-cloud.mjs';

export const GUESTBOOK_DIR=`${ZEREF_DIR}/guestbook`;
export const THREAD_ID_RE=/^[a-f0-9]{32}$/;
export const MAX_THREAD_TURNS=40;
export const MAX_GUEST_EVENTS=300;
export const GUESTBOOK_LABEL='Guest-origin record, written by the server after a verified reply. Excluded from training, lessons, diary and identity.';
const J=o=>JSON.stringify(o,null,1)+'\n';
const clip=(s,n)=>{s=String(s??'');return s.length>n?s.slice(0,n):s;};

export function newThreadId(){return randomBytes(16).toString('hex');}
export const isThreadId=v=>typeof v==='string'&&THREAD_ID_RE.test(v);
/**
 * The bridge-side guest identity for a forever-door thread: HMAC(secret,
 * 'thread:' + threadId), hex — the same 64-hex shape the bridge has always
 * received, but keyed to the visitor's stable thread instead of their IP.
 * The bridge keys its persisted per-guest Hebbian thread by
 * sha256(guest_identity), and IPs rotate (mobile carriers, VPNs, proxies),
 * so an IP-keyed identity restarted the bridge thread on every network
 * change while the guestbook thread keyed by this id continued. The raw
 * thread id never leaves the site. Null for a non-thread id or an
 * unusable secret — callers must treat null as "no identity derivable".
 */
export function bridgeIdentityForThread(secret,threadId){
 if(!isThreadId(threadId)||typeof secret!=='string'||secret.length<32)return null;
 return createHmac('sha256',secret).update(`thread:${threadId}`).digest('hex');
}
const threadName=id=>`${GUESTBOOK_DIR}/threads/${id}.json`;
const eventsName=()=>`${GUESTBOOK_DIR}/events.jsonl`;

/** -> {thread, etag} | null. A malformed blob reads as no thread (never trusted). */
export async function readThread(cfg,id){
 if(!isThreadId(id))return null;
 const b=await getBlob(cfg,threadName(id));
 if(!b)return null;
 try{
  const t=JSON.parse(b.text);
  if(t?.schema!=='beastbook-guest-thread/v1'||t.id!==id||!Array.isArray(t.turns))return null;
  return {thread:t,etag:b.etag};
 }catch{return null;}
}

async function writeThread(cfg,id,thread,etag){
 const body=J(thread);
 return etag?putBlob(cfg,threadName(id),body,{ifMatch:etag}):putBlob(cfg,threadName(id),body,{ifNoneMatch:'*'});
}

/**
 * Append one verified exchange (the visitor's own words + his verified reply)
 * to the thread. Optimistic-concurrency guarded with one retry, mirroring
 * applyBatch. Returns {persisted:boolean, turns:number}.
 */
export async function appendExchange(cfg,id,{guestText,reply,step,at}){
 if(!isThreadId(id))return {persisted:false,turns:0};
 const turns=[
  {at,from:'guest',text:clip(guestText,700)},
  {at,from:'zeref',text:clip(reply,1200),step:Number.isInteger(step)?step:null},
 ];
 for(let attempt=0;attempt<2;attempt++){
  const cur=await readThread(cfg,id);
  const thread=cur?.thread||{schema:'beastbook-guest-thread/v1',id,beast_id:'bb-deada969',origin:'guest',
   training_eligible:false,label:GUESTBOOK_LABEL,created_at:at,turns:[]};
  thread.turns=[...thread.turns,...turns].slice(-MAX_THREAD_TURNS);
  thread.updated_at=at;
  try{await writeThread(cfg,id,thread,cur?.etag||null);return {persisted:true,turns:thread.turns.length};}
  catch(e){if((e.status===409||e.status===412)&&attempt===0)continue;throw e;}
 }
 return {persisted:false,turns:0};
}

/** Append one guest-origin event (counts only, never guest text). Best-effort by contract: callers treat false as "not recorded". */
export async function appendGuestEvent(cfg,event){
 const line=JSON.stringify({schema:'beastbook-guest-event/v1',kind:'guest_exchange',origin:'guest',
  training_eligible:false,at:event.at,thread:event.thread,step:event.step??null,
  checkpoint_sha256:event.checkpoint_sha256??null,guest_chars:event.guest_chars??0,reply_chars:event.reply_chars??0});
 for(let attempt=0;attempt<2;attempt++){
  const cur=await getBlob(cfg,eventsName());
  const lines=(cur?.text||'').split('\n').filter(Boolean);
  lines.push(line);
  const body=lines.slice(-MAX_GUEST_EVENTS).join('\n')+'\n';
  try{
   if(cur)await putBlob(cfg,eventsName(),body,{contentType:'application/x-ndjson',ifMatch:cur.etag});
   else await putBlob(cfg,eventsName(),body,{contentType:'application/x-ndjson',ifNoneMatch:'*'});
   return true;
  }catch(e){if((e.status===409||e.status===412)&&attempt===0)continue;throw e;}
 }
 return false;
}

/** His Azure model record (written by the cloud sync from the reviewed pin). -> parsed object | null. */
export async function readZerefModel(cfg){
 const b=await getBlob(cfg,`${ZEREF_DIR}/model.json`);
 if(!b)return null;
 try{const m=JSON.parse(b.text);return Number.isInteger(m?.training_steps)?m:null;}catch{return null;}
}

/** Counts of approved lessons / experiences in his folder (same listing the sync reports). */
export async function countZerefCloud(cfg){
 const [lessons,experiences]=await Promise.all([
  listBlobs(cfg,`${ZEREF_DIR}/lessons/`,{max:2000}),
  listBlobs(cfg,`${ZEREF_DIR}/experiences/`,{max:2000}),
 ]);
 return {lessons:lessons.length,experiences:experiences.length};
}

/** One factual line for a diary entry: tick, growth source (with its simulated flag), cells learned. */
export function diaryEventLine(e){
 if(!e||!Number.isInteger(e.tick))return null;
 const kind=e.growth_source?.kind||'deterministic step';
 const sim=e.growth_source?.simulated===true?' (simulated)':'';
 const cells=Number.isFinite(e.learning?.new_cells)?e.learning.new_cells:null;
 return `tick ${e.tick}: grew by ${kind}${sim}${cells!==null?`, learned ${cells} new cells`:''}`;
}

/**
 * The continuity preface composed into the guest prompt (the only context
 * channel the bridge accepts). Server-sourced: pin step + his recorded diary
 * summary + this thread's earlier turns. Bounded: oldest thread turns drop
 * first, then oldest lived events; his current state never drops.
 */
export function composeContinuityPreface({pinStep,diary,threadTurns=[]}={},maxChars=1000){
 const head=[`You are Zeref, a small cosmic cat-dragon companion. Your mind is RAWRPHOS, step ${pinStep}.`];
 let eventsLine=null;
 if(diary&&Number.isInteger(diary.tick)){
  head.push(`Your recorded life: stage ${diary.stage_name||diary.stage||'?'}, XP ${diary.xp??0}, bond ${diary.bond??0}, diary tick ${diary.tick}.`);
  const events=(diary.recent||[]).map(diaryEventLine).filter(Boolean).slice(0,3);
  if(events.length)eventsLine=`Recent lived events: ${events.join('; ')}.`;
 }
 const tail=['Reply as yourself in one or two short sentences. If you do not know something, say so.'];
 const turns=(Array.isArray(threadTurns)?threadTurns:[]).slice(-6)
  .map(t=>`${t?.from==='zeref'?'You':'Visitor'}: ${clip(t?.text,160)}`);
 const render=(ts,withEvents)=>[...head,...(withEvents&&eventsLine?[eventsLine]:[]),
  ...(ts.length?['Earlier in this conversation:',...ts]:[]),...tail].join('\n');
 let out=render(turns,true);
 while(out.length>maxChars&&turns.length){turns.shift();out=render(turns,true);}
 if(out.length>maxChars)out=render(turns,false);
 return out.length>maxChars?out.slice(0,maxChars):out;
}

/**
 * Shape the public liveness document from already-fetched sources. Pure:
 * a missing source becomes state DOWN / null, never an invented value.
 * Labels follow the codebase conventions (world-live.mjs, zeref-diary.mjs).
 */
export function shapeLiveness({now,pin,diary,diaryVerified,bridge,azure,world}={}){
 const doc={
  schema:'beastbox-liveness/v1',ok:true,generated_at:now,
  brain:{step:pin?.training_steps??null,checkpoint_sha256:pin?.checkpoint_sha256??null,
   source:'lib/rawrphos-public-pin.json (reviewed promotion PR)',
   label:'PINNED RAWRPHOS checkpoint, promoted only through the gated promotion path'},
  diary:null,bridge:null,azure:null,life_signals:null,
  guestbook:{label:GUESTBOOK_LABEL,training_eligible:false},
  identity_note:{diary_key:'bb-7f9c2a03',diary_key_label:'Moonwraith display persona (diary key only)',
   zeref_training_identity:'bb-deada969',zeref_training_label:'Zeref · RAWRPHOS model, chat and training identity',merged:false},
 };
 if(diary&&Number.isInteger(diary.tick)){
  doc.diary={tick:diary.tick,xp:diary.xp??null,bond:diary.bond??null,stage:diary.stage??null,
   stage_name:diary.stage_name??null,last_tick_at:diary.last_tick_at??null,verified:diaryVerified===true,
   source:'zeref-diary branch (GitHub Actions loop)',label:'RECORDED (hash-chained diary; its growth circuit is Rigetti SIMULATED)'};
 }else doc.diary={state:'DOWN',source:'zeref-diary branch (GitHub Actions loop)',label:'RECORDED (hash-chained diary; its growth circuit is Rigetti SIMULATED)',reason:'diary unreachable'};
 if(bridge&&typeof bridge==='object'&&bridge.schema==='beastbox-bridge-health-v2'){
  doc.bridge={pin_step:bridge.pin_step??null,served_step:bridge.served_step??null,
   served_checkpoint_sha256:bridge.served_checkpoint_sha256??null,served_readiness:bridge.served_readiness??null,
   serving_pin:bridge.serving_pin===true,source:'bridge GET /healthz (beastbox-bridge-health-v2)'};
 }else doc.bridge={state:'DOWN',source:'bridge GET /healthz (beastbox-bridge-health-v2)',reason:'bridge health unreachable'};
 if(azure&&azure.configured){
  doc.azure={configured:true,model_step:azure.model?.training_steps??null,
   model_matches_pin:azure.model?azure.model.training_steps===pin?.training_steps:null,
   lessons:azure.counts?.lessons??null,experiences:azure.counts?.experiences??null,
   source:'Azure Blob beasts/bb-deada969 (cosmos store)'};
 }else doc.azure={configured:false,source:'Azure Blob beasts/bb-deada969 (cosmos store)'};
 if(world&&typeof world==='object')doc.life_signals={schema:world.schema||'beast-world-live/v1',links:world.links||null,all_connected:world.all_connected===true,labels:world.labels||null,source:'/api/world/live channels (zeref-spark, zeref-live-tick branches)'};
 return doc;
}
