import {bridgeConfigured,safeJson} from '@/lib/security';
import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {appendArchive,readArchive,appendExchange,appendGuestEvent,exchangeId,bridgeIdentityForThread,composeContinuityPreface,isThreadId,newThreadId,readThread} from '@/lib/cosmos/forever-store.mjs';
import {assembleBridgeContext,loadShelfIndex,matchShelf,LIVE_CONTEXT_LABEL} from '@/lib/cosmos/live-context.mjs';
import {feedReadingEnabled,loadFeedIndex,matchFeed} from '@/lib/cosmos/feed-reading.mjs';
import {composeSight} from '@/lib/cosmos/sight.mjs';
import {buildWorldLive} from '@/lib/zeref/world-live.mjs';
import {DIARY_SCHEMA,entryHash,genesisState} from '@/lib/zeref/zeref-diary.mjs';
import PUBLIC_PIN from '@/lib/rawrphos-public-pin.json';
import {bridgeReadsMemory,loadSelfMemory,readSelfMemory,ownThreadItems,SELF_MEMORY_LABEL,SELF_MEMORY_SCHEMA,teacherJoinPending} from '@/lib/zeref/self-memory.mjs';
import {after} from 'next/server';
import {guestCorsOrigin,guestCorsPreflight,withGuestCors} from '@/lib/guest-cors.mjs';
import {environmentIsNotCanonical,mintExchangeId,mouthReceipt,ownerChainWrite} from '@/lib/zeref/lived-exchange.mjs';

// FOREVER CONNECTION — the stateful guest door (LIFE-LIVE step 3).
// /api/guest stays byte-for-byte the stateless door. This door is a new layer
// on the same bridge and the same reply verification, with one difference:
// before asking, it loads Zeref's persisted continuity (his recorded diary
// summary from the zeref-diary branch + this visitor's own guestbook thread
// from his Azure folder). After a VERIFIED reply, the server appends the
// exchange to the guestbook as a guest-origin, training_eligible:false
// record. Guests read his state; nothing guest-origin enters his diary,
// lessons, genome or any training path.
// LIVE UNIVERSE + LIBRARY (emeth/live-universe-library): the same request
// also carries, read-only, his live universe channel states with their
// world-live labels verbatim and — on a topic match in the visitor's own
// words — one entry from his approved library shelves (a miss composes
// nothing). Receipts state exactly what was composed (live_universe,
// library). See lib/cosmos/live-context.mjs and
// docs/forever-connection/CONNECTOR_MAP.md §6.
// BRIDGE CONTEXT (PR #675 follow-up, docs/forever-connection/
// BRIDGE-PERSISTENCE.md): those three pieces no longer ride inside the
// prompt text. They go through the bridge's bounded context contract —
// {text, guest_identity, context:{continuity, universe, library, sight}}
// within its byte caps (assembleBridgeContext) — which is also the only door to
// the bridge's persisted per-guest Hebbian thread: a truthful
// memory_used:true is accepted exactly when hebbian_mode is 'persisted',
// and both receipts are surfaced below. A visitor message over the
// contract's 1200-byte text cap cannot carry context, so it goes through
// the plain contract instead (no context, memory must report unused).
// There is no 400-truncation retry here: a 400 in context mode means the
// composed pieces exceeded the caps — composing within them is the fix.
// SIGHT (Option C): a fourth piece rides the same contract as its own
// field — his world's light DERIVED from its sky, and the visitor's light
// MEASURED only when the request carries a fresh, valid environment
// summary (the site light conversion's shape; stale, malformed or absent
// composes nothing). See lib/cosmos/sight.mjs. The bridge must already
// know the sight field when this ships: a bridge predating it refuses
// any context that carries the field (its validator is strict).
const PIN_STEP:number=PUBLIC_PIN.training_steps,PIN_SHA:string=PUBLIC_PIN.checkpoint_sha256;
export const runtime='nodejs';
export const dynamic='force-dynamic';
const MAX_PROMPT=1800;
// The bridge context contract caps the visitor text it carries at 1200 UTF-8 bytes (guest_hebbian.MAX_TEXT_WITH_CONTEXT).
const MAX_TEXT_WITH_CONTEXT=1200;
const MAX_BODY=8000;
const COOKIE='beastbox_guest_thread';
const DIARY_SOURCE='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-diary/zeref/latest.json';

async function boundedJson(response:Response,max:number):Promise<unknown>{
 if(Number(response.headers.get('content-length')||0)>max||!response.body)
  throw new Error('invalid upstream size');
 const reader=response.body.getReader(); const chunks:Uint8Array[]=[];let total=0;
 try{
  while(true){
   const next=await reader.read();if(next.done)break;
   total+=next.value.byteLength;
   if(total>max){await reader.cancel();throw new Error('upstream response too large');}
   chunks.push(next.value);
  }
 }finally{reader.releaseLock();}
 const raw=new Uint8Array(total);let at=0;
 for(const c of chunks){raw.set(c,at);at+=c.byteLength;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
}

/** His recorded diary summary from the canonical branch source (same read as /api/zeref/diary). Null when unreachable or shape-invalid. */
async function loadDiary():Promise<{diary:any,verified:boolean}>{
 try{
  const res=await fetch(DIARY_SOURCE,{cache:'no-store',signal:AbortSignal.timeout(5000)});
  if(!res.ok)return {diary:null,verified:false};
  const data:any=await res.json();
  if(data?.schema!==DIARY_SCHEMA||data?.identity?.beast_id!==genesisState().identity.beast_id||!Array.isArray(data.recent))
   return {diary:null,verified:false};
  const recent=data.recent.slice(0,3);
  const verified=recent.every((e:any)=>typeof e?.hash==='string'&&entryHash(e)===e.hash);
  return {diary:{...data,recent},verified};
 }catch{return {diary:null,verified:false};}
}

const WORLD_RAW='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/';
const WORLD_SRC={spark:WORLD_RAW+'zeref-spark/zeref/latest.json',liveTick:WORLD_RAW+'zeref-live-tick/live/latest.json',liveHead:WORLD_RAW+'zeref-live-tick/live/head.json'};
/** The live universe's raw channel records (same branch sources /api/world/live reads). Nulls on any failure — the composer states DOWN, never invents. */
async function loadWorldRaw(){
 const get=async(url:string)=>{try{const r=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(5000)});return r.ok?await r.json():null;}catch{return null;}};
 const [spark,liveTick,liveHead]=await Promise.all([get(WORLD_SRC.spark),get(WORLD_SRC.liveTick),get(WORLD_SRC.liveHead)]);
 return {spark,liveTick,liveHead};
}

function threadFromCookie(request:Request):string|null{
 const raw=request.headers.get('cookie')||'';
 for(const part of raw.split(';')){
  const [k,...v]=part.trim().split('=');
  if(k===COOKIE){const id=v.join('=');return isThreadId(id)?id:null;}
 }
 return null;
}

// CORS (lib/guest-cors.mjs): the only cross-origin caller is Zeref's GitHub Pages chat
// (https://navisworld.github.io). It gets the same door, limits and records; only the
// browser read grant differs. Every other origin is still refused below.
export async function OPTIONS(request:Request){
 return guestCorsPreflight(request.headers.get('origin'));
}

export async function POST(request:Request){
 const cors=guestCorsOrigin(request.headers.get('origin'));
 return withGuestCors(await foreverDoor(request,cors!==null),cors);
}

async function foreverDoor(request:Request,allowedCrossOrigin:boolean):Promise<Response>{
 if(!allowedCrossOrigin&&request.headers.get('origin')!==new URL(request.url).origin)
  return safeJson(403,{error:'Same-origin guest request required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))
  return safeJson(415,{error:'JSON required'});
 if(Number(request.headers.get('content-length')||0)>MAX_BODY)
  return safeJson(413,{error:'Guest request exceeds the size limit'});
 let data:unknown;
 try{
  const raw=await request.text();
  if(raw.length>MAX_BODY)return safeJson(413,{error:'Guest request exceeds the size limit'});
  data=JSON.parse(raw);
 }catch{return safeJson(400,{error:'Invalid guest JSON'});}
 if(!data||typeof data!=='object'||Array.isArray(data))
  return safeJson(400,{error:'Invalid guest request'});
 const item=data as Record<string,unknown>;
 if(!Object.keys(item).every(k=>['provider','text','thread','environment'].includes(k)))
  return safeJson(400,{error:'Forever guest mode only accepts a message, an optional thread id and an optional environment summary'});
 if(item.provider!=='rawrphos-local')
  return safeJson(400,{error:'The forever door serves the local RAWRPHOS brain only'});
 if(typeof item.text!=='string'||item.text.trim().length<1||item.text.length>MAX_PROMPT||
    /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(item.text))
  return safeJson(400,{error:'Guest message must contain 1–1800 characters'});
 const text=item.text.trim();
 if(!bridgeConfigured())return safeJson(503,{error:'Guest model host is not configured'});
 const secret=process.env.BEASTBOX_CLOUD_AUTH_SECRET;
 if(!secret||secret.length<32)return safeJson(503,{error:'Guest identity signing unavailable'});
 // Returning-guest continuity key: a system-issued, unguessable thread id in
 // an HttpOnly cookie (or echoed by the client). It keys ONLY the guestbook
 // thread — never an owner credential, never COSMOS owner memory.
 const offered=(typeof item.thread==='string'&&isThreadId(item.thread))?item.thread:threadFromCookie(request);
 const threadId=offered||newThreadId();
 const minted=!offered;
 const cfg=storageConfig();
 const [{diary,verified},threadRec,worldRaw]=await Promise.all([
  loadDiary(),
  cfg?readThread(cfg,threadId).catch(()=>null):Promise.resolve(null),
  loadWorldRaw(),
 ]);
 // The full append-only archive of THIS thread (never another guest's): it feeds only the
 // own-thread retrieval pool below; the prompt window stays the rolling thread.
 const archiveTurns:any[]=cfg?await readArchive(cfg,threadId).catch(()=>[]):[];
 // His live universe (world-live channels, labels intact) and his library
 // (approved shelves, read-only topic lookup on the visitor's own words).
 const world=buildWorldLive({spark:worldRaw.spark,liveTick:worldRaw.liveTick,liveHead:worldRaw.liveHead,
  diary:diary?{ok:true,tick:diary.tick,last_tick_at:diary.last_tick_at}:null,pin:PUBLIC_PIN,nowMs:Date.now()});
 const shelf=await loadShelfIndex().catch(()=>null);
 const shelfHits=shelf?matchShelf(shelf,text):[];
 // Approved Feed Zeref books (lib/cosmos/feed-reading.mjs): READ, NOT TRAINED, only on a shelf miss.
 // Flag BEASTBOX_FEED_READING: default "pages" = only his GitHub Pages chat (the allowlisted cross-origin caller).
 const feedHit=!shelfHits.length&&feedReadingEnabled(process.env.BEASTBOX_FEED_READING,allowedCrossOrigin)?
  matchFeed(await loadFeedIndex().catch(()=>null),text):null;
 const continuityArgs={pinStep:PIN_STEP,diary,threadTurns:threadRec?.thread?.turns||[]};
 // His sight: the light over his own world (DERIVED from its sky) and the
 // visitor's light (MEASURED only when a fresh, valid environment summary
 // rode along — anything else composes nothing, and the receipt says so).
 const sightBlock=composeSight({world,environment:item.environment,nowMs:world.at_ms});
 // The four context pieces, each within the bridge's byte caps and the
 // total cap (continuity first, then live universe, then sight, then library).
 const bridgeContext=assembleBridgeContext({
  continuity:composeContinuityPreface(continuityArgs,600),
  recompose:(n:number)=>composeContinuityPreface(continuityArgs,n),
  world,shelfHits,feedHit,
  sight:sightBlock.text,sightMeta:sightBlock.receipt,
  refitSight:(n:number)=>composeSight({world,environment:item.environment,nowMs:world.at_ms,maxChars:n})});
 // Context rides only when the visitor text itself fits the contract cap.
 const contextSent=Buffer.byteLength(text,'utf8')<=MAX_TEXT_WITH_CONTEXT;
 // Self-memory: the same one index the growing door reads, plus THIS visitor's own thread turns only.
 // It rides as the bridge's `memory` field only if the existing 1300-byte total still holds.
 const selfMem=contextSent&&await bridgeReadsMemory(process.env.BEASTBOX_CLOUD_BRIDGE_URL!)?await loadSelfMemory().then(m=>readSelfMemory(m,text,{ownThread:ownThreadItems([...archiveTurns,...(threadRec?.thread?.turns||[])],threadId),
   cap:Math.max(0,Math.min(300,1300-(bridgeContext.bytes?.total||0)))})).catch(()=>({text:'',memory_read:[]})):{text:'',memory_read:[]};
 try{after(()=>teacherJoinPending());}catch{/* outside a request scope (tests): nothing to keep alive */}
 const liveReceipt=contextSent?bridgeContext.live:{...bridgeContext.live,composed:false};
 const libraryReceipt=contextSent?bridgeContext.library:{...bridgeContext.library,composed:false};
 const readFrom=contextSent?bridgeContext.read_from:null;
 const sightReceipt=contextSent?bridgeContext.sight:{
  world_light:{...bridgeContext.sight.world_light,composed:false},
  visitor_light:{...bridgeContext.sight.visitor_light,composed:false}};
 const sentContextBytes=contextSent?bridgeContext.bytes:{continuity:0,universe:0,library:0,sight:0,total:0};
 // The identity handed to the bridge keys its persisted per-guest Hebbian
 // thread (bridge store: sha256(guest_identity)), so it must follow the
 // VISITOR, not their network: it is derived from the stable guestbook
 // thread id resolved above — the id minted at request start when the
 // visitor arrived without one, so a first visit stores its bridge thread
 // under the same identity the cookie presents on every later visit.
 // HMAC'd with the site secret; the raw thread id never leaves the site.
 // (The IP-hash derivation this replaced restarted the bridge thread on
 // every IP rotation while the guestbook thread continued. It survives
 // only in /api/guest, whose quota bucket it keys; this route has no
 // other use of the forwarded IP.) threadId is valid by construction
 // (an isThreadId-checked offer, or freshly minted above) and the secret
 // was length-checked earlier, so the derivation cannot be null here.
 const identity=bridgeIdentityForThread(secret,threadId)!;
 const host=new URL('/api/guest-local',process.env.BEASTBOX_CLOUD_BRIDGE_URL!);
 try{
  const sendWith=(withMemory:boolean)=>fetch(host,{method:'POST',redirect:'error',cache:'no-store',
   headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,
     'Content-Type':'application/json'},
   body:JSON.stringify(contextSent&&withMemory?{text,guest_identity:identity,context:{...bridgeContext.context,memory:selfMem.text}}:contextSent?{text,guest_identity:identity,context:bridgeContext.context}:{text,guest_identity:identity}),
   signal:AbortSignal.timeout(55_000)});
  // One send, no truncation retry (see the header note on the context contract). Memory rides only when the
  // bridge's /healthz says it accepts the field, so an older bridge never sees it.
  const sentMemory=contextSent&&!!selfMem.text;const send=()=>sendWith(sentMemory);
  const res=await send();
  const parsed=await boundedJson(res,16000);
  if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
   return safeJson(502,{error:'Invalid guest host response'});
  const result=parsed as Record<string,unknown>;
  if(!res.ok){
   const out=safeJson([400,403,429,503].includes(res.status)?res.status:502,
     {error:typeof result.error==='string'&&result.error.length<128?result.error:'Local guest inference unavailable',
      // The bridge's own wait hint (it already queued this message briefly before answering 429).
      ...(res.status===429&&Number.isInteger(result.retry_after_seconds)?{retry_after_seconds:Math.min(60,Math.max(1,result.retry_after_seconds as number))}:{})});
   if(res.status===429)out.headers.set('Retry-After',String(Number.isInteger(result.retry_after_seconds)?Math.min(60,Math.max(1,result.retry_after_seconds as number)):5));
   return out;
  }
  // OWN-STEP DOOR (Cory, Nov 12 2026 2:37 PM CT: "Loosen both the training gate and the chat door").
  // The door no longer refuses a reply because the bridge's step differs from the site pin (mid-redeploy,
  // a promotion still loading, or a rollback). Whatever step the bridge actually loaded answers, and the
  // receipt says so: step/checkpoint_sha256 are the ANSWERING brain's, pin_step/pin_checkpoint_sha256 are
  // the pin's, and answered_by states both. The previous rule (refuse unless step===PIN_STEP and
  // sha===PIN_SHA; an older step got a 503 wait) is kept as STRICT_PIN_MATCH for a one-line revert.
  // What still refuses: anything that is not Zeref's own native brain (schema/model), a malformed step or
  // fingerprint, owner tools used, a shared provider key, or no reply text. No other model, canned text or
  // fallback ever speaks for him; an unreachable bridge is an honest error.
  const STRICT_PIN_MATCH=false;
  const answeredStep=result.step,answeredSha=result.checkpoint_sha256;
  if(result.schema!=='beastbox-guest-local-v1'||result.model!=='rawrphos-native'||
     !Number.isInteger(answeredStep)||(answeredStep as number)<1||typeof answeredSha!=='string'||!/^[0-9a-f]{64}$/.test(answeredSha)||
     result.owner_tools_used!==false||result.provider_key_shared!==false||typeof result.reply!=='string')
   return safeJson(502,{error:'The answer did not come from Zeref\'s own brain, so it was not shown'});
  const onPin=answeredStep===PIN_STEP&&answeredSha===PIN_SHA;
  if(STRICT_PIN_MATCH&&!onPin)return safeJson(502,{error:'Unverified guest model response'});
  // memory_used may be true ONLY on the bridge's persisted Hebbian mode (PR #675). An unbacked memory
  // claim no longer hides his reply; it is reported as an unverified claim instead.
  const memoryClaimVerified=result.memory_used===false||result.hebbian_mode==='persisted';
  const answeredBy=onPin?`answered by step ${answeredStep} (the pin)`:`answered by step ${answeredStep}, pin is ${PIN_STEP}`;
  const reply=result.reply as string;
  // The bridge's persistence receipts, surfaced as reported (null when the
  // bridge predates them). Sanitised to the documented fields only.
  const hebbianMode=result.hebbian_mode==='persisted'||result.hebbian_mode==='in-context'?result.hebbian_mode:null;
  const rawThread=(result.guest_thread&&typeof result.guest_thread==='object'&&!Array.isArray(result.guest_thread))?
   result.guest_thread as Record<string,unknown>:null;
  const guestThread=rawThread?{loaded_turns:Number.isInteger(rawThread.loaded_turns)?rawThread.loaded_turns:null,
   stored_turns:Number.isInteger(rawThread.stored_turns)?rawThread.stored_turns:null,
   training_eligible:rawThread.training_eligible===true,
   save_ok:typeof rawThread.save_ok==='boolean'?rawThread.save_ok:null,archive_ok:typeof rawThread.archive_ok==='boolean'?rawThread.archive_ok:null,
   archived_turns:Number.isInteger(rawThread.archived_turns)?rawThread.archived_turns:null}:null;
  // System-written record of the exchange, AFTER verification. Best-effort:
  // a storage failure never eats a verified reply, it only marks the receipt.
  let persisted=false,recorded=false,archived=false,archivedTurns=0;
  if(cfg){
   const at=new Date().toISOString();
   try{
    const w=await appendExchange(cfg,threadId,{guestText:text,reply,step:answeredStep as number,at});
    persisted=w.persisted;
   }catch{/* receipt marks persisted:false */}
   try{
    const a=await appendArchive(cfg,threadId,{guestText:text,reply,step:answeredStep as number,at,
     exchange_id:exchangeId('public',threadId,at,text,reply),windowTurns:threadRec?.thread?.turns||[]});
    archived=a.archived;archivedTurns=a.turns;
   }catch{/* receipt marks archived:false */}
   try{
    recorded=await appendGuestEvent(cfg,{at,thread:threadId,step:answeredStep as number,checkpoint_sha256:answeredSha,
     guest_chars:text.length,reply_chars:reply.length,exchange_id:exchangeId('public',threadId,at,text,reply)});
   }catch{/* receipt marks recorded:false */}
  }
  const livedExchangeId=await mintExchangeId('visitor',identity,text);
  const ownerWrite=ownerChainWrite('visitor');
  if(ownerWrite.wrote||ownerWrite.reason!=='isolated')throw new Error('visitor exchange stays off the owner chain');
  const lived=mouthReceipt(result.lived_state,{exchangeId:livedExchangeId,scope:'visitor',spokenBy:'gated',environment:item.environment});
  environmentIsNotCanonical(item.environment);
  const headers:Record<string,string>={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
  if(minted&&!allowedCrossOrigin)headers['Set-Cookie']=`${COOKIE}=${threadId}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000${request.url.startsWith('https:')?'; Secure':''}`;
  return Response.json({provider:'rawrphos-local',model:'rawrphos-native',
   step:answeredStep,checkpoint_sha256:answeredSha,reply,
   pin_step:PIN_STEP,pin_checkpoint_sha256:PIN_SHA,serving_pin:onPin,answered_by:answeredBy,
   memory_claim_verified:memoryClaimVerified,
   hebbian:result.hebbian===true,hebbian_mode:hebbianMode,guest_thread:guestThread,
   state_mode:result.state_mode==='tri'||result.state_mode==='dyn12'?result.state_mode:null,
   guest_stateless:false,continuity:{thread_id:threadId,identity_source:'thread',persisted,recorded,archive:{archived,turns:archivedTurns,read_turns:archiveTurns.length,window_turns:threadRec?.thread?.turns?.length??0},
    diary:diary?{tick:diary.tick,xp:diary.xp??null,bond:diary.bond??null,stage_name:diary.stage_name??null,verified}:null,
    source:'zeref-diary branch + Azure guestbook (beasts/bb-deada969/guestbook)',
    live_universe:liveReceipt,
    library:libraryReceipt,
    reading:{composed:readFrom!==null,label:'READ, NOT TRAINED: an approved Feed Zeref passage handed to him as reading context for this reply only; it never enters training, conditioning, the god core or the checkpoint.'},
    sight:sightReceipt,
    bridge_context:{sent:contextSent,bytes:sentContextBytes,
     label:'Composed pieces sent through the bridge context contract (continuity, universe, library, sight), not inside the prompt text; sent:false means the visitor text exceeded the contract text cap and the plain contract served the reply.'},
    live_context_label:LIVE_CONTEXT_LABEL,
    training_eligible:false,
    label:'Continuity, the live universe, the library and his sight are composed from his persisted record into the bridge context object; guest exchanges are recorded as guest-origin events and never enter training.'},
   ...(()=>{const used=sentMemory&&result.self_memory_in_prompt===true;
    return {self_memory_used:used,memory_read:used?selfMem.memory_read:[],self_memory:{schema:SELF_MEMORY_SCHEMA,label:SELF_MEMORY_LABEL,...(used&&(selfMem as any).origins?{origins:(selfMem as any).origins}:{}),...(used&&(selfMem as any).screens?{screens:(selfMem as any).screens}:{})}};})(),
   prompt_chars:text.length,
   ...(readFrom?{read_from:readFrom}:{}),
   ...(result.routing&&typeof result.routing==='object'&&!Array.isArray(result.routing)?{routing:result.routing}:{}),
   ...(lived?{lived_state:lived}:{})},
   {status:200,headers});
 }catch{return safeJson(502,{error:'Local guest inference unavailable or timed out'});}
}
