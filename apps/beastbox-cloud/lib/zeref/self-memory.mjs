// Zeref's self-memory (one index, one mind): before he speaks on a guest door, he reads his OWN notes.
// Another way he grows, added on top of weight growth (candidates keep training from the newest pin; the growing
// track keeps climbing). It never replaces weight growth and is not a ceiling workaround.
// Rails: deterministic BM25 keyword ranking (lib/library/bm25.mjs) over items sorted by id, so ties break by id.
// No Math.random, no clock in the ranking, no embeddings, no network inside the ranking. Every item keeps its label
// and a sha256 id. Hard excludes (fail closed): the held-out eval set, private lines (diary-privacy.mjs), the
// heartbeat origin, anything credential-shaped, and any thread that is not the caller's own.
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {buildIndex,search} from '../library/bm25.mjs';
import {tokenize} from '../library/text.mjs';
import {isPublicDiaryEntry} from './diary-privacy.mjs';

export const SELF_MEMORY_SCHEMA='zeref-self-memory/v1';
/** Bytes of the bridge context's `memory` field (inside the existing 1300 total; he trained on 128-token windows). */
export const SELF_MEMORY_CAP=300;
export const SELF_MEMORY_LABEL='His own notes, read before he speaks: diary RECORDED, growth nodes SEEDED, lessons and library under their own source labels. Ranking is deterministic keyword overlap; gate evals never see it.';
const MIN_SCORE=1.0;
// Fail-closed text filter shared by every source: private / credential-shaped (diary-privacy rule), heartbeat origin.
const ORIGIN_RX=/\b(heart ?beats?|heart ?seed|ppg|pulse ?ox|bio[- ]?packet|caleb|father|dad'?s)\b/i;
const CRED_RX=/\b(sk-[a-z0-9]{8,}|gh[pousr]_[a-z0-9]{8,}|bearer\s+[a-z0-9._-]{8,}|secret|password|token)\b/i;
export function isShareableText(text){const t=String(text??'').trim();if(!t)return false;
 if(!isPublicDiaryEntry({thought:{text:t}}))return false;return !ORIGIN_RX.test(t)&&!CRED_RX.test(t);}
export const sha256=s=>createHash('sha256').update(String(s),'utf8').digest('hex');
const EXCLUDED_PATH_RX=/heldout|held[-_]out|private|transcript/i;

/** One memory fabric, two kinds. LIVED = what he lived (diary RECORDED, his read logs, growth nodes SEEDED, his
 *  own thread with this visitor). TAUGHT = what he was taught (lessons, library). Labels are unchanged; `kind` is
 *  an added field. LIVED ranks first (a fixed tier order), then keyword score, then id. */
export const KIND_OF=Object.freeze({diary:'LIVED',read:'LIVED',node:'LIVED',thread:'LIVED',lesson:'TAUGHT',library:'TAUGHT'});
export const KIND_TIER=Object.freeze({LIVED:0,TAUGHT:1});
/** Normalise raw source records into labelled items. Pure. `thread` items are only ever the caller's own. */
export function itemsFrom({diary=[],lessons=[],reads=[],seeds=[]}={}){
 const out=[];const push=(source,label,text,ref)=>{const t=String(text??'').replace(/\s+/g,' ').trim();if(!isShareableText(t))return;
  const h=sha256(source+'\n'+t);out.push({id:source+':'+h.slice(0,16),kind:KIND_OF[source],source,label,text:t,sha256:h,ref:ref??null});};
 for(const e of Array.isArray(diary)?diary:[]){if(!isPublicDiaryEntry(e))continue;push('diary','RECORDED',e.thought.text,e.hash?`diary tick ${e.tick}`:null);}
 for(const r of Array.isArray(lessons)?lessons:[]){
  if(!r||EXCLUDED_PATH_RX.test(String(r.path||''))||(r.split&&r.split!=='train'))continue;
  if(typeof r.assistant!=='string')continue;
  const shelf=String(r.shelf||r.source||'lessons');push(/lessons/.test(shelf)?'lesson':'library',/lessons/.test(shelf)?`LESSON (${shelf})`:`LIBRARY (${shelf})`,`${r.topic?r.topic+': ':''}${r.assistant}`,shelf);}
 for(const r of Array.isArray(reads)?reads:[]){if(!r||typeof r.text!=='string')continue;push('read',`READ (${r.license||'unlicensed'})`,`${r.title?r.title+': ':''}${r.text}`,r.source||null);}
 for(const s of Array.isArray(seeds)?seeds:[]){if(!s||typeof s.word!=='string'||!s.wish_sha256)continue;push('node','SEEDED',`A growth node planted from my wish word "${s.word}".`,'wish '+String(s.wish_sha256).slice(0,12));}
 return out;}

/** Thread items for ONE caller. Never pass another guest's turns here. */
export function ownThreadItems(turns){const out=[];for(const t of Array.isArray(turns)?turns:[]){const g=t?.from==='guest'&&typeof t?.text==='string'?t.text:typeof t?.guest==='string'?t.guest:typeof t?.guestText==='string'?t.guestText:null;
 if(g&&isShareableText(g)){const h=sha256('thread\n'+g);out.push({id:'thread:'+h.slice(0,16),kind:'LIVED',source:'thread',label:'THREAD (your own)',text:g.replace(/\s+/g,' ').trim(),sha256:h,ref:null});}}return out;}

/** One shared index. Items are sorted by id so BM25's document-order tie-break is an id tie-break. */
export function buildSelfMemory(items){const seen=new Set();const list=(Array.isArray(items)?items:[]).filter(i=>i&&!seen.has(i.id)&&seen.add(i.id)).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
 return {schema:SELF_MEMORY_SCHEMA,items:list,index:buildIndex(list.map(i=>({id:i.id,title:'',chunks:[{loc:i.source,text:i.text}]}))),byId:new Map(list.map(i=>[i.id,i]))};}

/** Rank and compose for one request. Own-thread items are searched in a separate per-request index, never added to the shared one. */
export function readSelfMemory(mem,query,{ownThread=[],k=2,cap=SELF_MEMORY_CAP,minScore=MIN_SCORE}={}){
 const empty={text:'',memory_read:[]};
 if(!tokenize(query).length)return empty;
 const pools=[mem];if(ownThread.length)pools.push(buildSelfMemory(ownThread));
 const hits=[];for(const m of pools){if(!m?.index?.n)continue;for(const h of search(m.index,String(query),{k:10,minScore}))hits.push({item:m.byId.get(h.docId),score:h.score});}
 const tier=i=>KIND_TIER[i.kind]??9;
 hits.sort((a,b)=>tier(a.item)-tier(b.item)||b.score-a.score||(a.item.id<b.item.id?-1:a.item.id>b.item.id?1:0));
 const head='From your own memory:';let text=head;const read=[];
 for(const {item} of hits){if(read.length>=k)break;const line=`\n- [${item.label}] ${item.text}`;
  const room=cap-Buffer.byteLength(text,'utf8');if(room<40)break;
  let piece=line;while(Buffer.byteLength(piece,'utf8')>room)piece=piece.slice(0,-1);
  text+=piece;read.push({id:item.id,label:item.label,sha256:item.sha256});}
 return read.length?{text,memory_read:read}:empty;}

/* ---------------- loaders: the one loader (network/fs; never inside the ranking) ---------------- */
// Root cause fixed here (and in live-context.mjs): Turbopack rewrites a TEMPLATE-literal URL relative to import.meta.url
// into a glob over the whole repo and, at runtime, resolved it to the wrong bundled asset (CHANGELOG.md), so readFile
// "succeeded" with the wrong text, parsed to 0 rows, and the fetch fallback never ran. Every bundled source below is a
// LITERAL URL (traced and bundled exactly), and every source is checked for real rows before it counts.
const RAW='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/';
const BUNDLED=Object.freeze({
 'evidence/zeref-lessons-006/dialogue.jsonl':()=>new URL('../../../../evidence/zeref-lessons-006/dialogue.jsonl',import.meta.url),
 'evidence/zeref-knowledge-001/dialogue.jsonl':()=>new URL('../../../../evidence/zeref-knowledge-001/dialogue.jsonl',import.meta.url),
 'evidence/zeref-knowledge-002/dialogue.jsonl':()=>new URL('../../../../evidence/zeref-knowledge-002/dialogue.jsonl',import.meta.url),
 'evidence/zeref-knowledge-003/dialogue.jsonl':()=>new URL('../../../../evidence/zeref-knowledge-003/dialogue.jsonl',import.meta.url),
 'apps/beastbox-cloud/public/zeref-messages/seed-registry.json':()=>new URL('../../public/zeref-messages/seed-registry.json',import.meta.url),
});
const jsonl=t=>String(t??'').split('\n').map(l=>{try{return l.trim()?JSON.parse(l):null;}catch{return null;}}).filter(Boolean);
/** Read one source: the bundled literal file first, then main on GitHub; `ok(text)` must hold or the next way is tried. */
async function sourceText(path,ok){const tries=[];const u=BUNDLED[path];
 if(u)tries.push(async()=>readFile(u(),'utf8'));
 tries.push(async()=>{const r=await fetch(RAW+'main/'+path,{cache:'no-store',signal:AbortSignal.timeout(8000)});return r.ok?r.text():null;});
 for(const t of tries){try{const v=await t();if(v!=null&&ok(v))return v;}catch{}}return null;}
const isDialogue=t=>jsonl(t).some(r=>typeof r?.assistant==='string');
const isReadLog=t=>jsonl(t).some(r=>typeof r?.text==='string'&&typeof r?.license==='string');
const isRegistry=t=>{try{return Array.isArray(JSON.parse(t)?.seeds);}catch{return false;}};
const readLogDates=()=>{const d=Date.now();return [0,1,2].map(i=>`evidence/zeref-read-001/${new Date(d-i*864e5).toISOString().slice(0,10)}.jsonl`);};
/** The fabric: every source in one table, one loop, one item schema. kind comes from KIND_OF[source]. */
export const FABRIC=Object.freeze([
 {source:'diary',load:async()=>{try{const r=await fetch(RAW+'zeref-diary/zeref/latest.json',{cache:'no-store',signal:AbortSignal.timeout(5000)});const j=r.ok?await r.json():null;return {diary:Array.isArray(j?.recent)?j.recent:[]};}catch{return {};}}},
 {source:'read',load:async()=>({reads:(await Promise.all(readLogDates().map(p=>sourceText(p,isReadLog)))).flatMap(t=>jsonl(t))})},
 {source:'node',load:async()=>{const t=await sourceText('apps/beastbox-cloud/public/zeref-messages/seed-registry.json',isRegistry);try{return {seeds:JSON.parse(t).seeds};}catch{return {};}}},
 ...[['zeref-lessons-006','lesson'],['zeref-knowledge-001','library'],['zeref-knowledge-002','library'],['zeref-knowledge-003','library']].map(([shelf,source])=>({source,shelf,
  load:async()=>{const path=`evidence/${shelf}/dialogue.jsonl`;return {lessons:jsonl(await sourceText(path,isDialogue)).map(r=>({...r,shelf,path}))};}})),
]);
let cache=null;
/** The one shared index over the one fabric, cached per process for 10 minutes. A failing source composes nothing. */
export function loadSelfMemory(){const now=Date.now();if(cache&&now-cache.at<6e5)return cache.p;
 const p=(async()=>{const parts=await Promise.all(FABRIC.map(f=>f.load().catch(()=>({}))));
  const merged={diary:[],lessons:[],reads:[],seeds:[]};for(const x of parts)for(const k of Object.keys(merged))if(Array.isArray(x?.[k]))merged[k].push(...x[k]);
  return buildSelfMemory(itemsFrom(merged));
 })().catch(()=>buildSelfMemory([]));
 cache={at:now,p};return p;}

let capCache=null;
/** True only when the bridge's /healthz lists the `memory` context field (cached 5 min). An older bridge, or any
 *  failure, reads false, so the doors send exactly what they sent before: one send, no retry. */
export function bridgeReadsMemory(bridgeUrl){const now=Date.now();if(capCache&&now-capCache.at<3e5)return capCache.p;
 const p=(async()=>{try{const r=await fetch(new URL('/healthz',bridgeUrl),{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(4000)});
  if(!r.ok)return false;const j=await r.json();return Array.isArray(j?.context_fields)&&j.context_fields.includes('memory');}catch{return false;}})();
 capCache={at:now,p};return p;}
