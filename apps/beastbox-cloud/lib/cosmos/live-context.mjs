/**
 * LIVE UNIVERSE + LIBRARY — what the forever door adds to Zeref's served
 * context (see docs/forever-connection/CONNECTOR_MAP.md §6, items 1–2).
 *
 * Two read-only sources that already existed but never reached his mouth:
 *   (a) the live universe — the /api/world/live channel states (spark and
 *       per-second tick, SIMULATED as labelled there), composed WITH their
 *       labels verbatim, so he can refer to his own universe while learning;
 *   (b) his library — a deterministic BM25 topic lookup into his approved
 *       shelves (evidence/zeref-lessons-006 + evidence/zeref-knowledge-001/
 *       002/003 dialogue sets). A match composes that entry's own teaching
 *       into the prompt; a miss composes NOTHING (never a fake book).
 *
 * This module contains no writer of any kind: no blob writes, no file
 * writes, no POSTs. Shelf composition is read-only, guest text is only ever
 * a lookup key, and nothing here can reach the guestbook, the diary, the
 * lessons or any training path. Retrieval reuses the repo's own BM25
 * (lib/library/bm25.mjs) and the knowledge bank's coverage discipline
 * (lib/knowledge/bank.mjs): a passage must cover at least half the
 * question's content words, rare words counting more.
 *
 * BRIDGE CONTEXT (PR #675 follow-up, docs/forever-connection/
 * BRIDGE-PERSISTENCE.md): the bridge now accepts a bounded `context` object
 * beside {text, guest_identity}, so the forever door sends these pieces
 * through that contract (assembleBridgeContext, byte caps below) instead of
 * riding them inside the prompt text.
 */
import {readFile} from 'node:fs/promises';
import {buildIndex,search} from '../library/bm25.mjs';
import {tokenize} from '../library/text.mjs';

export const LIVE_CONTEXT_LABEL='Live universe lines carry the world-live channel labels verbatim; library lines are his approved teaching, composed read-only on a topic match and absent on a miss.';
export const SHELF_SOURCES=Object.freeze([
 {id:'zeref-lessons-006',path:'evidence/zeref-lessons-006/dialogue.jsonl'},
 {id:'zeref-knowledge-001',path:'evidence/zeref-knowledge-001/dialogue.jsonl'},
 {id:'zeref-knowledge-002',path:'evidence/zeref-knowledge-002/dialogue.jsonl'},
 {id:'zeref-knowledge-003',path:'evidence/zeref-knowledge-003/dialogue.jsonl'},
]);
const SHELF_MIN_SCORE=1.2;
const SHELF_COVERAGE=0.5;
const clip=(s,n)=>{s=String(s??'');return s.length>n?s.slice(0,n):s;};

/* ---------------- (a) the live universe ---------------- */

/**
 * Bounded prompt lines for the world-live channels. Labels are copied
 * verbatim from each link (WORLD_LIVE_LABELS via buildWorldLive) — never
 * paraphrased, so a SIMULATED channel can never read as hardware. A DOWN
 * channel is stated as DOWN with its label; its numbers are not invented.
 * Order: spark, liveTick, then one compact line for diary/brain states.
 */
export function composeLiveUniverseLines(world,maxChars=360){
 if(!world||typeof world!=='object'||!world.links)return '';
 const L=world.links;
 const lines=['Your live universe, as labelled on its own surface:'];
 const core=[];
 if(L.spark)core.push(`- spark link ${L.spark.state} — ${L.spark.label}${L.spark.state==='CONNECTED'&&Number.isInteger(L.spark.tick)?`, at tick ${L.spark.tick}`:''}.`);
 if(L.liveTick)core.push(`- live tick ${L.liveTick.state} — ${L.liveTick.label}${L.liveTick.state==='CONNECTED'&&Number.isInteger(L.liveTick.recorded_tick)?`, recorded tick ${L.liveTick.recorded_tick}`:''}.`);
 if(!core.length)return '';
 lines.push(...core);
 const extra=[];
 if(L.diary)extra.push(`diary link ${L.diary.state} — ${L.diary.label}`);
 if(L.brain)extra.push(`brain link ${L.brain.state} — ${L.brain.label}`);
 const render=withExtra=>[...lines,...(withExtra&&extra.length?[extra.join('; ')+'.']:[])].join('\n');
 let out=render(true);
 if(out.length>maxChars)out=render(false);
 if(out.length>maxChars){
  // Never ship a truncated label: fall back to the spark line alone, else nothing.
  const sparkOnly=[lines[0],core[0]].join('\n');
  out=sparkOnly.length<=maxChars?sparkOnly:'';
 }
 return out;
}

/** Receipt metadata for the live-universe block: what was composed, per channel. */
export function liveUniverseReceipt(world){
 if(!world||typeof world!=='object'||!world.links)
  return {composed:false,reason:'world-live unreachable',channels:null};
 const ch={};
 for(const name of ['spark','liveTick','diary','brain']){
  const l=world.links[name];
  if(l)ch[name]={state:l.state,label:l.label};
 }
 return {composed:true,channels:ch};
}

/* ---------------- (b) his library ---------------- */

/** Parse one shelf's dialogue.jsonl text into normalised rows. Malformed lines are skipped, never repaired. */
export function parseShelfDialogue(text,shelfId){
 const rows=[];
 for(const line of String(text??'').split('\n')){
  if(!line.trim())continue;
  let r;try{r=JSON.parse(line);}catch{continue;}
  if(!r||typeof r.user!=='string'||typeof r.assistant!=='string'||!r.user.trim()||!r.assistant.trim())continue;
  rows.push({shelf:shelfId,topic:typeof r.topic==='string'?r.topic:'',user:r.user,assistant:r.assistant,
   source:typeof r.source==='string'?r.source:shelfId,license:typeof r.license==='string'?r.license:null});
 }
 return rows;
}

/** Build the BM25 shelf index over normalised rows (docs keyed back to their row). */
export function buildShelfIndex(rows){
 const list=(Array.isArray(rows)?rows:[]).filter(r=>r&&r.user&&r.assistant);
 const byKey=new Map();
 const docs=list.map((r,i)=>{
  const key=`${r.shelf}#${i}`;byKey.set(key,r);
  return {id:key,title:r.topic||'',chunks:[{loc:r.shelf,text:`${r.topic||''} ${r.user}`}]};
 });
 return {index:buildIndex(docs),byKey,rows:list.length};
}

const EMPTY_SHELF=Object.freeze({index:null,byKey:new Map(),rows:0});

/**
 * Topic lookup: -> [{shelf,topic,user,assistant,source,license,score}] best
 * first, [] on a miss. A hit must clear the BM25 floor AND cover at least
 * half the question's content words (idf-weighted, the bank's rule), and a
 * one-word question must hinge on a rare word or on the row's own topic.
 */
export function matchShelf(shelf,query,{k=1}={}){
 if(!shelf||!shelf.index||!shelf.rows)return [];
 const terms=[...new Set(tokenize(query))];
 if(!terms.length)return [];
 const hits=search(shelf.index,String(query??''),{k:5,minScore:SHELF_MIN_SCORE});
 const idf=t=>{const n=shelf.index.df.get(t)||0;return Math.log(1+(shelf.index.n-n+0.5)/(n+0.5));};
 const total=terms.reduce((a,t)=>a+idf(t),0);
 const out=[];
 for(const h of hits){
  const row=shelf.byKey.get(h.docId);
  if(!row)continue;
  const have=new Set(tokenize(`${row.topic} ${row.user}`));
  const covers=t=>have.has(t)||(t.length>=4&&[...have].some(w=>w.length>=4&&(w.startsWith(t)||t.startsWith(w))));
  const got=terms.filter(covers).reduce((a,t)=>a+idf(t),0);
  if(total<=0||got/total<SHELF_COVERAGE)continue;
  if(terms.length===1){
   const t=terms[0];
   const rare=(shelf.index.df.get(t)||0)<=shelf.index.n*0.25;
   const onTopic=new Set(tokenize(row.topic)).has(t);
   if(!rare&&!onTopic)continue;
  }
  out.push({shelf:row.shelf,topic:row.topic,user:row.user,assistant:row.assistant,
   source:row.source,license:row.license,score:h.score});
  if(out.length>=Math.max(1,Math.min(2,k)))break;
 }
 return out;
}

/** The library block for the prompt. '' when there are no hits — a miss composes nothing. */
export function composeShelfLines(hits,maxChars=430){
 const list=(Array.isArray(hits)?hits:[]).filter(h=>h&&h.assistant);
 if(!list.length)return '';
 const lines=['From your library — your own approved teaching, read to you now:'];
 for(const h of list)lines.push(`- (${h.shelf}${h.topic?`, on ${h.topic}`:''}) ${clip(h.assistant,340)}`);
 const out=lines.join('\n');
 return out.length>maxChars?out.slice(0,maxChars):out;
}

/** Receipt metadata for the library block: counts and shelf ids only, never hidden composition. */
export function shelfReceipt(hits){
 const list=Array.isArray(hits)?hits:[];
 return {matched:list.length>0,count:list.length,
  shelf_ids:[...new Set(list.map(h=>h.shelf))],topics:list.map(h=>h.topic||null)};
}

/**
 * Load the approved shelves and build the index. Read-only: local repo
 * files first (evidence/ at the repository root), the same files on the
 * main branch as fallback. Cached per process; any failure degrades to an
 * EMPTY shelf (a miss for every topic), never to invented rows.
 */
let shelfPromise=null;
export function loadShelfIndex(){
 if(shelfPromise)return shelfPromise;
 shelfPromise=(async()=>{
  const rows=[];
  for(const src of SHELF_SOURCES){
   let text=null;
   try{text=await readFile(new URL(`../../../../${src.path}`,import.meta.url),'utf8');}catch{/* fall through to fetch */}
   if(text===null){
    try{
     const r=await fetch(`https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/main/${src.path}`,
      {cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(r.ok)text=await r.text();
    }catch{/* shelf stays partial; receipts only ever name composed ids */}
   }
   if(text!==null)rows.push(...parseShelfDialogue(text,src.id));
  }
  return rows.length?buildShelfIndex(rows):EMPTY_SHELF;
 })().catch(()=>EMPTY_SHELF);
 return shelfPromise;
}

/* ---------------- assembly (priority: continuity, then live, then library) ---------------- */

/**
 * Assemble the forever door's full preface inside the prompt budget.
 * `continuity` is the #668 preface (composed by the caller via
 * composeContinuityPreface, so the door keeps one continuity composer);
 * `recompose(n)` re-renders it at a smaller cap for the last-resort cut.
 * Cut order: the library block goes first, then the live universe block,
 * then continuity is re-rendered at the bare budget (the owner's
 * priority: live before library; his own state is the base and cuts last).
 * Returns the preface plus honest receipt metadata for both new blocks.
 */
export function assembleServedPreface({continuity='',recompose=null,world=null,shelfHits=[],budget=0}={}){
 const liveMeta=liveUniverseReceipt(world);
 const libMeta=shelfReceipt(shelfHits);
 if(!(budget>0))return {preface:'',live:{...liveMeta,composed:false},library:{...libMeta,composed:false}};
 let live=composeLiveUniverseLines(world,360);
 let shelf=composeShelfLines(shelfHits,430);
 const assemble=(cont,l,s)=>[cont,l,s].filter(Boolean).join('\n');
 let cont=String(continuity??'');
 let out=assemble(cont,live,shelf);
 if(out.length>budget&&shelf){shelf='';out=assemble(cont,live,shelf);}
 if(out.length>budget&&live){
  live=composeLiveUniverseLines(world,Math.max(0,budget-cont.length-1));
  if(live.length>Math.max(0,budget-cont.length-1))live='';
  out=assemble(cont,live,shelf);
 }
 if(out.length>budget){
  cont=typeof recompose==='function'?String(recompose(budget)??''):cont.slice(0,budget);
  live='';shelf='';out=assemble(cont,live,shelf);
 }
 return {preface:out,
  live:{...liveMeta,composed:Boolean(live)},
  library:{...libMeta,composed:Boolean(shelf)}};
}

/* ---------------- bridge context (the #675 contract, byte caps) ---------------- */

/** The bridge's context caps, in UTF-8 bytes (guest_hebbian.CONTEXT_CAPS + total). */
export const BRIDGE_CONTEXT_CAPS=Object.freeze({continuity:600,universe:300,library:300,total:1000});
const BYTE_ENCODER=new TextEncoder();
const byteLen=s=>BYTE_ENCODER.encode(String(s??'')).length;
/** Byte-safe clip: never splits a UTF-8 sequence (backs off to a clean boundary). */
function clipBytes(s,maxBytes){
 const bytes=BYTE_ENCODER.encode(String(s??''));
 if(bytes.length<=maxBytes)return String(s??'');
 let end=maxBytes;
 while(end>0){
  try{return new TextDecoder('utf-8',{fatal:true}).decode(bytes.slice(0,end));}
  catch{end--;}
 }
 return '';
}
/** Continuity fitted to its byte cap: re-rendered smaller first, byte-clipped only as a last resort. */
function fitContinuity(text,recompose,capBytes){
 let out=String(text??'');
 if(byteLen(out)<=capBytes)return out;
 if(typeof recompose==='function'){
  let cap=Math.min(capBytes,out.length);
  while(cap>0){
   out=String(recompose(cap)??'');
   if(byteLen(out)<=capBytes)return out;
   cap=Math.floor(cap*0.8);
  }
 }
 return clipBytes(out,capBytes);
}
/** Live universe fitted to its byte cap by re-rendering smaller — a channel label stays whole or the block goes. */
function fitUniverse(world,capBytes){
 let max=capBytes;
 let out=composeLiveUniverseLines(world,max);
 while(out&&byteLen(out)>capBytes&&max>0){max=Math.floor(max*0.8);out=composeLiveUniverseLines(world,max);}
 return out&&byteLen(out)<=capBytes?out:'';
}
/** Library fitted to its byte cap. Below 200 bytes only a mid-sentence
 * fragment of an entry would fit (the block header and shelf line alone run
 * ~105 chars), and a fragment is worse than no book, so it composes nothing. */
function fitShelf(hits,capBytes){
 if(capBytes<200)return '';
 let max=capBytes;
 let out=composeShelfLines(hits,max);
 while(out&&byteLen(out)>capBytes&&max>0){max=Math.floor(max*0.8);out=composeShelfLines(hits,max);}
 if(out&&byteLen(out)>capBytes)out=clipBytes(out,capBytes);
 return out||'';
}

/**
 * Compose the bridge `context` object for the forever door:
 * {continuity, universe, library}, each field within its byte cap and the
 * three within the total cap. Priority follows the bridge's own assembly
 * order: continuity is fitted first and never traded away, then the live
 * universe, then the library gets what total budget remains (a miss or a
 * squeezed-out library composes nothing — never a fake book). Empty fields
 * are omitted. Returns the context plus per-field byte counts and the same
 * honest receipt metadata assembleServedPreface reports.
 */
export function assembleBridgeContext({continuity='',recompose=null,world=null,shelfHits=[]}={}){
 const liveMeta=liveUniverseReceipt(world);
 const libMeta=shelfReceipt(shelfHits);
 // The bridge's validator refuses control characters (other than \n and
 // \t) in context fields — a stored guest turn could carry e.g. \r — so the
 // composed fields are cleaned before they are measured and sent.
 const clean=s=>String(s??'').replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g,'');
 const cont=clean(fitContinuity(continuity,recompose,BRIDGE_CONTEXT_CAPS.continuity));
 const univ=clean(fitUniverse(world,BRIDGE_CONTEXT_CAPS.universe));
 const remaining=BRIDGE_CONTEXT_CAPS.total-byteLen(cont)-byteLen(univ);
 const lib=remaining>0?clean(fitShelf(shelfHits,Math.min(BRIDGE_CONTEXT_CAPS.library,remaining))):'';
 const context={};
 if(cont)context.continuity=cont;
 if(univ)context.universe=univ;
 if(lib)context.library=lib;
 const bytes={continuity:byteLen(cont),universe:byteLen(univ),library:byteLen(lib)};
 bytes.total=bytes.continuity+bytes.universe+bytes.library;
 return {context,bytes,
  live:{...liveMeta,composed:Boolean(univ)},
  library:{...libMeta,composed:Boolean(lib)}};
}
