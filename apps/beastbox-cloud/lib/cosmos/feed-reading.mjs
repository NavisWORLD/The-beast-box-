/**
 * FEED READING — approved books from the "Feed Zeref" drop box on his GitHub
 * profile (NavisWORLD/NavisWORLD zeref/feed/), READ at chat time, NOT TRAINED.
 *
 * The profile's workflow builds zeref/feed/index/index.json from items Cory
 * approved with /approve (pending and rejected items are never in it). This
 * module reads that static index read-only, finds the best-matching passage
 * for the visitor's own words with the same deterministic BM25 as his
 * library shelves (lib/library/bm25.mjs: no model, no embeddings, no paid
 * compute), and composes it for the bridge context contract's existing
 * `library` field within its byte cap. Nothing here writes anywhere: it never
 * touches training, conditioning, the god core, the pin or the checkpoint,
 * and the exchange stays training_eligible:false like every guest chat.
 *
 * Flag (BEASTBOX_FEED_READING): "pages" (default) reads only for Zeref's
 * GitHub Pages chat (the allowlisted cross-origin caller), "all" for every
 * forever-door visitor, "off" never. His own approved shelves always win the
 * library slot; a book passage is composed only on a shelf miss.
 */
import {buildIndex,search} from '../library/bm25.mjs';
import {tokenize} from '../library/text.mjs';

export const FEED_INDEX_URL='https://raw.githubusercontent.com/NavisWORLD/NavisWORLD/main/zeref/feed/index/index.json';
export const FEED_LABEL='READ, NOT TRAINED';
export const FEED_SCHEMA='navisworld-zeref-reading-index/v1';
const MAX_INDEX_BYTES=20_000_000;
const CACHE_MS=10*60_000;
// A book shelf can be tiny (one approved excerpt = one passage), where idf says little, so the
// gate is coverage, not an absolute score: the passage must hold >= 60% of the question's
// content words and at least two of them (one 6+ letter word for a one-word question).
const MIN_SCORE=0.05;
const COVERAGE=0.6;

/** The reading flag for one request. Unknown values fall back to the default ("pages"). */
export function feedReadingEnabled(flag,isPagesChat){
 const f=String(flag??'').trim().toLowerCase();
 if(f==='off')return false;
 if(f==='all')return true;
 return isPagesChat===true;
}

/** Validate the profile's static index and build the BM25 view. Anything malformed -> null (reads nothing). */
export function buildFeedIndex(raw){
 if(!raw||typeof raw!=='object'||raw.schema!==FEED_SCHEMA||!Array.isArray(raw.docs)||!Array.isArray(raw.chunks))return null;
 const docs=raw.docs.map(d=>d&&typeof d.id==='string'&&typeof d.title==='string'?
  {id:d.id,title:d.title.slice(0,200),source_url:typeof d.source_url==='string'?d.source_url:null,
   license:typeof d.license==='string'?d.license:null,sha256:typeof d.sha256==='string'?d.sha256:null}:null);
 const byDoc=new Map();
 for(const c of raw.chunks){
  if(!c||!Number.isInteger(c.doc)||!docs[c.doc]||typeof c.text!=='string'||!c.text.trim())continue;
  const d=docs[c.doc];
  if(!byDoc.has(d.id))byDoc.set(d.id,{id:d.id,title:d.title,chunks:[]});
  byDoc.get(d.id).chunks.push({loc:String(c.n??''),text:c.text.slice(0,2000)});
 }
 const list=[...byDoc.values()];
 if(!list.length)return {index:null,docs:new Map(),passages:0};
 return {index:buildIndex(list),docs:new Map(docs.filter(Boolean).map(d=>[d.id,d])),passages:list.reduce((a,d)=>a+d.chunks.length,0)};
}

/**
 * Best approved passage for the visitor's words, or null on a miss. Like his
 * shelves' discipline, but coverage-gated: cover at least 60% of the
 * question's content words, and match two or more of them.
 */
export function matchFeed(feed,query){
 if(!feed||!feed.index||!feed.index.n)return null;
 const terms=[...new Set(tokenize(query))];
 if(!terms.length)return null;
 for(const h of search(feed.index,String(query??''),{k:5,minScore:MIN_SCORE})){
  const text=h.text;
  if(typeof text!=='string')continue;
  const have=new Set(tokenize(text));
  const matched=terms.filter(t=>have.has(t));
  // Plain share of the question's words: on a tiny shelf idf would make every word the book
  // lacks outweigh the ones it has, so coverage counts words instead of weighting them.
  if(matched.length/terms.length<COVERAGE)continue;
  if(terms.length===1?matched[0].length<6:matched.length<2)continue;
  const d=feed.docs.get(h.docId);
  if(!d)continue;
  return {doc_id:d.id,title:d.title,source_url:d.source_url,license:d.license,sha256:d.sha256,passage:text,score:h.score,matched};
 }
 return null;
}

const enc=new TextEncoder();
const byteLen=s=>enc.encode(String(s??'')).length;

/**
 * The library block for one passage, fitted to capBytes. Returns {text, excerpt}:
 * `excerpt` is exactly the passage text that went into the block (shown to the
 * visitor as the citation), '' when nothing fits (a fragment under ~60 chars is
 * worse than no book).
 */
export function composeFeedBlock(hit,capBytes){
 if(!hit||!(capBytes>0))return {text:'',excerpt:''};
 const head=`From an approved book you are reading (${FEED_LABEL}), "${hit.title.slice(0,80)}":\n`;
 const room=capBytes-byteLen(head);
 if(room<60*1)return {text:'',excerpt:''};
 // The excerpt is the word window (within the cap) that holds the most matched words,
 // the middle of the tied windows, so the part of the passage that answered the visitor is what he is handed.
 const words=hit.passage.replace(/\s+/g,' ').trim().split(' ');
 const want=new Set(Array.isArray(hit.matched)?hit.matched:[]);
 const hits=words.map(w=>tokenize(w).some(t=>want.has(t))?1:0);
 let bestN=-1,tied=[];
 for(let i=0;i<words.length;i++){
  let j=i,bytes=0,n=0;
  while(j<words.length&&bytes+byteLen(words[j])+(j>i?1:0)<=room){bytes+=byteLen(words[j])+(j>i?1:0);n+=hits[j];j++;}
  if(j===i)continue;
  if(n>bestN){bestN=n;tied=[];}
  if(n===bestN)tied.push(words.slice(i,j).join(' '));
  if(j===words.length)break;
 }
 // Of the windows tied on matched words, the middle one keeps them away from the cut edges.
 const ex=tied.length?tied[Math.floor((tied.length-1)/2)]:'';
 if(byteLen(ex)<60)return {text:'',excerpt:''};
 return {text:head+ex,excerpt:ex};
}

let cache=null;
/** Fetch + build, cached per process for 10 minutes. Any failure -> an empty feed (reads nothing), never invented text. */
export function loadFeedIndex(nowMs=Date.now(),fetcher=fetch){
 if(cache&&nowMs-cache.at<CACHE_MS)return cache.promise;
 const promise=(async()=>{
  const r=await fetcher(FEED_INDEX_URL,{cache:'no-store',signal:AbortSignal.timeout(6000)});
  if(!r.ok)return null;
  const len=Number(r.headers?.get?.('content-length')||0);
  if(len>MAX_INDEX_BYTES)return null;
  const t=await r.text();
  if(t.length>MAX_INDEX_BYTES)return null;
  return buildFeedIndex(JSON.parse(t));
 })().catch(()=>null);
 cache={at:nowMs,promise};
 return promise;
}
export function _resetFeedCache(){cache=null;}
