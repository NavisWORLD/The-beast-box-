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
import {createHash,createHmac,randomBytes} from 'node:crypto';
import {getBlob,putBlob,listBlobs} from './azure-blob.mjs';
import {ZEREF_DIR} from './zeref-cloud.mjs';
import {publicDiaryMood,publicDiaryLearning,publicPromotion,publicGate,publicFairGate,publicLivedState,publicTraining} from '../liveness-public.mjs';

export const GUESTBOOK_DIR=`${ZEREF_DIR}/guestbook`;
export const THREAD_ID_RE=/^[a-f0-9]{32}$/;
export const MAX_THREAD_TURNS=40;
export const MAX_GUEST_EVENTS=300;
export const GUESTBOOK_LABEL='Guest-origin record, written by the server after a verified reply. Excluded from training, lessons, diary and identity.';
const J=o=>JSON.stringify(o,null,1)+'\n';
const clip=(s,n)=>{s=String(s??'');return s.length>n?s.slice(0,n):s;};

/** Stable id for one exchange (kind|thread|at|texts) so a record is never counted twice. */
export function exchangeId(kind,thread,at,a,b){return createHash('sha256').update([kind,thread,at,a,b].map(String).join('\u0000')).digest('hex');}
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
  const thread=cur?.thread||{schema:'beastbook-guest-thread/v1',id,beast_id:'bb-deada969',origin:'guest',source_kind:'public',
   training_eligible:false,label:GUESTBOOK_LABEL,created_at:at,turns:[]};
  thread.turns=[...thread.turns,...turns].slice(-MAX_THREAD_TURNS);
  thread.updated_at=at;
  try{await writeThread(cfg,id,thread,cur?.etag||null);return {persisted:true,turns:thread.turns.length};}
  catch(e){if((e.status===409||e.status===412)&&attempt===0)continue;throw e;}
 }
 return {persisted:false,turns:0};
}

/**
 * FULL THREAD ARCHIVE (2026-11-06, Cory: memory is never lost; his memory of a
 * guest accumulates). threads/<id>.json above stays the short rolling window
 * (MAX_THREAD_TURNS) that feeds the prompt; this is the complete record of the
 * same thread, append-only: one JSON line per turn, existing lines are never
 * rewritten, reordered or removed (every write is verified to keep the old
 * body as an exact prefix, under an etag guard). Same guest-origin labels,
 * training_eligible:false, outside diary/lessons/experiences.
 */
export const ARCHIVE_SCHEMA='beastbook-guest-thread-archive/v1';
export const MAX_ARCHIVE_READ_BYTES=8_000_000;
const archiveName=id=>`${GUESTBOOK_DIR}/archive/${id}.jsonl`;
const archiveLine=(id,t,extra={})=>JSON.stringify({schema:ARCHIVE_SCHEMA,thread:id,origin:'guest',source_kind:'public',training_eligible:false,
 at:t.at??null,from:t.from==='zeref'?'zeref':'guest',text:String(t.text??''),...(Number.isInteger(t.step)?{step:t.step}:{}),...extra});

/** Parse archive lines. Foreign schemas and other threads are skipped, never trusted. */
export function parseArchiveLines(text,id){
 const out=[];
 for(const l of String(text??'').split('\n')){if(!l)continue;try{const r=JSON.parse(l);if(r?.schema===ARCHIVE_SCHEMA&&r.thread===id&&typeof r.text==='string')out.push(r);}catch{}}
 return out;
}
/**
 * Every archived turn for THIS thread, oldest first.
 * MAX_ARCHIVE_READ_BYTES remains the size at which a single response is larger than
 * the old hidden-record cutoff. Growing past it no longer returns []. [] only when
 * there is no archive, the id is foreign, or the blob cannot be read.
 */
export async function readArchive(cfg,id){
 if(!isThreadId(id))return [];
 const b=await getBlob(cfg,archiveName(id));
 if(!b)return [];
 return parseArchiveLines(b.text,id);
}

/**
 * Append one verified exchange to the archive. On the archive's first write,
 * the turns still in the rolling window are carried in first (marked
 * carried_from:'thread-window', their original timestamps kept) so nothing
 * that still exists is left out. Idempotent per exchange_id. -> {archived, turns}
 */
export async function appendArchive(cfg,id,{guestText,reply,step,at,exchange_id,windowTurns=[]}){
 if(!isThreadId(id))return {archived:false,turns:0};
 const fresh=[archiveLine(id,{at,from:'guest',text:guestText},{exchange_id}),archiveLine(id,{at,from:'zeref',text:reply,step},{exchange_id})];
 for(let attempt=0;attempt<2;attempt++){
  const cur=await getBlob(cfg,archiveName(id));
  const old=cur?.text||'';
  if(exchange_id&&old.includes(`"exchange_id":"${exchange_id}"`))return {archived:true,turns:old.split('\n').filter(Boolean).length};
  const carried=cur?[]:(Array.isArray(windowTurns)?windowTurns:[]).filter(t=>t&&typeof t.text==='string').map(t=>archiveLine(id,t,{carried_from:'thread-window'}));
  const body=old+[...carried,...fresh].join('\n')+'\n';
  if(!body.startsWith(old))return {archived:false,turns:0}; // append-only invariant
  try{
   if(cur)await putBlob(cfg,archiveName(id),body,{contentType:'application/x-ndjson',ifMatch:cur.etag});
   else await putBlob(cfg,archiveName(id),body,{contentType:'application/x-ndjson',ifNoneMatch:'*'});
   return {archived:true,turns:body.split('\n').filter(Boolean).length};
  }catch(e){if((e.status===409||e.status===412)&&attempt===0)continue;throw e;}
 }
 return {archived:false,turns:0};
}

/**
 * Append-only monthly shard (archive first, then window): every line written to a bounded
 * tail log is ALSO appended here, never trimmed. Existing body is kept as an exact prefix
 * (etag guard); a line whose dedupe key is already present is a no-op. -> boolean
 */
export const monthShard=(dir,stem,at)=>`${dir}/archive/${stem}-${/^\d{4}-\d{2}/.test(String(at))?String(at).slice(0,7):'undated'}.jsonl`;
export async function appendShardLine(cfg,name,line,dedupe){
 for(let attempt=0;attempt<2;attempt++){
  const cur=await getBlob(cfg,name);const old=cur?.text||'';
  if(dedupe&&old.includes(dedupe))return true;
  const body=old+line+'\n';
  if(!body.startsWith(old))return false;
  try{
   if(cur)await putBlob(cfg,name,body,{contentType:'application/x-ndjson',ifMatch:cur.etag});
   else await putBlob(cfg,name,body,{contentType:'application/x-ndjson',ifNoneMatch:'*'});
   return true;
  }catch(e){if((e.status===409||e.status===412)&&attempt===0)continue;throw e;}
 }
 return false;
}

const LIVED_REPLICA=`${ZEREF_DIR}/lived-replica/exchanges.jsonl`;

/** Hash-only replica of an owner exchange receipt. Not the chain root, and not the diary. */
export async function mirrorLivedExchange(cfg,receipt){
 if(!receipt||receipt.scope!=='owner'||receipt.status!=='lived'||receipt.canonical===true)return {mirrored:false,status:'skipped',canonical:false};
 if(receipt.text!=null||receipt.reply!=null||receipt.heard!=null||receipt.raw_video!=null||receipt.raw_audio!=null)return {mirrored:false,status:'unconfirmed',canonical:false};
 const exchangeId=receipt.exchange_id,role=receipt.role;
 if(typeof exchangeId!=='string'||!/^[0-9a-f]{32,64}$/.test(exchangeId))return {mirrored:false,status:'unconfirmed',canonical:false};
 const line=JSON.stringify({schema:'lived-exchange-replica-v1',canonical:false,scope:'owner',exchange_id:exchangeId,role:typeof role==='string'?role:null,
  event_id:typeof receipt.event_id==='string'?receipt.event_id:null,text_sha256:typeof receipt.text_sha256==='string'?receipt.text_sha256:null,
  state_sha256:typeof receipt.state_sha256==='string'?receipt.state_sha256:null,label:receipt.label==='RECORDED'?'RECORDED':null,
  counts:receipt.counts&&typeof receipt.counts==='object'?{chars:receipt.counts.chars??null,utf8_bytes:receipt.counts.utf8_bytes??null}:null});
 try{
  const ok=await appendShardLine(cfg,LIVED_REPLICA,line,`"exchange_id":${JSON.stringify(exchangeId)},"role":${JSON.stringify(typeof role==='string'?role:null)}`);
  return ok?{mirrored:true,status:'replica',canonical:false}:{mirrored:false,status:'unconfirmed',canonical:false};
 }catch{return {mirrored:false,status:'unconfirmed',canonical:false};}
}

/** Append one guest-origin event (counts only, never guest text). Best-effort by contract: callers treat false as "not recorded". */
export async function appendGuestEvent(cfg,event){
 const line=JSON.stringify({schema:'beastbook-guest-event/v1',kind:'guest_exchange',origin:'guest',source_kind:'public',
  ...(typeof event.exchange_id==='string'&&/^[a-f0-9]{64}$/.test(event.exchange_id)?{exchange_id:event.exchange_id}:{}),
  training_eligible:false,at:event.at,thread:event.thread,step:event.step??null,
  checkpoint_sha256:event.checkpoint_sha256??null,guest_chars:event.guest_chars??0,reply_chars:event.reply_chars??0});
 for(let attempt=0;attempt<2;attempt++){
  const cur=await getBlob(cfg,eventsName());
  const lines=(cur?.text||'').split('\n').filter(Boolean);
  // Never count one exchange twice: a retried append with the same exchange_id is a no-op.
  if(event.exchange_id&&lines.some(l=>l.includes(`"exchange_id":"${event.exchange_id}"`)))return true;
  // Archive first (append-only, monthly shard), then the bounded tail below.
  if(!await appendShardLine(cfg,monthShard(GUESTBOOK_DIR,'events',event.at),line,event.exchange_id?`"exchange_id":"${event.exchange_id}"`:null))return false;
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

/** Every guest-event line in the monthly shards, oldest shard first. The events.jsonl tail stays MAX_GUEST_EVENTS. */
export async function readGuestEventArchive(cfg){
 const prefix=`${GUESTBOOK_DIR}/archive/events-`;
 const names=(await listBlobs(cfg,prefix)).filter(n=>n.startsWith(prefix)&&n.endsWith('.jsonl')).sort();
 const out=[];
 for(const name of names){
  const b=await getBlob(cfg,name);
  if(!b)continue;
  for(const l of b.text.split('\n')){if(!l)continue;try{const r=JSON.parse(l);if(r?.schema==='beastbook-guest-event/v1')out.push(r);}catch{}}
 }
 return out;
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
export function shapeLiveness({now,pin,diary,diaryVerified,bridge,azure,world,pinCommit,training,livedState}={}){
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
  const mood=publicDiaryMood(diary);
  if(mood)doc.diary.mood=mood.mood;
  const learn=publicDiaryLearning(diary);
  if(learn)doc.diary.learning=learn;
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
 if(world&&typeof world==='object')doc.life_signals={schema:world.schema||'beast-world-live/v1',links:world.links||null,all_connected:world.all_connected===true,stalls:world.stalls??null,river:world.river??null,senses:Array.isArray(world.senses)?world.senses:null,labels:world.labels||null,source:'/api/world/live channels (zeref-spark, zeref-live-tick, zeref-diary branches)'};
 // Public-safe additions for the Pages profile card. Missing sources stay
 // unpublished / DOWN; thought text and guest data are never copied in.
 doc.promotion=publicPromotion(pin,pinCommit);
 doc.gate=publicGate(pin);
 doc.fair_gate=publicFairGate();
 doc.lived_state=publicLivedState(livedState);
 const learn=doc.diary&&doc.diary.learning?doc.diary.learning:publicDiaryLearning(diary);
 doc.learning={diary:learn||null,training:publicTraining(training,pin),pin_step:pin?.training_steps??null};
 return doc;
}
