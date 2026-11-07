/** Zeref's Azure teacher lessons (beasts/bb-deada969/lessons/<date>/<id>.json, kind APPROVED_TEACHER_LESSON) as TAUGHT
 *  self-memory, behind the SAME fail-closed screen as every other source, BEFORE the index:
 *   (a) held-out: exact normalised prompt, normalised answer (3+ words), near-duplicate (word-bigram Jaccard >= 0.6)
 *       or containment of a held-out prompt's bigrams, against lib/zeref/heldout-screen.json (hashes of every
 *       held-out gate item, built read-only by scripts/build_heldout_screen.py);
 *   (b) duplicate of a source already in (or of another teacher lesson);
 *   (c) the excludes: private lines, the heartbeat origin, credentials (isShareableText), and any record that is
 *       not an approved teacher lesson (other guests' threads never live under lessons/ and are refused by shape).
 *  If the screen cannot run (held-out screen missing/empty, Azure unreadable or incomplete), NONE go in.
 *  Read only. The label kept is the record's own kind: APPROVED_TEACHER_LESSON. */
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';

export const TEACHER_LABEL='APPROVED_TEACHER_LESSON';
export const TEACHER_PREFIX='beasts/bb-deada969/lessons/';
const h16=s=>createHash('sha256').update(s).digest('hex').slice(0,16);
export const normText=s=>String(s??'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim().split(/\s+/).filter(Boolean).join(' ');
const bigrams=n=>{const w=n.split(' ').filter(Boolean);const s=new Set();for(let i=0;i+1<w.length;i++)s.add(h16(w[i]+' '+w[i+1]));return s;};

/** Prepare the held-out screen. Returns null when it is unusable (fail closed). */
export function prepareHeldout(screen){
 const rows=Array.isArray(screen?.rows)?screen.rows:[];
 if(screen?.schema!=='zeref-heldout-screen/v1'||!rows.length||rows.length!==screen.items)return null;
 return {p:new Set(rows.map(r=>r.p)),a:new Set(rows.map(r=>r.a).filter(Boolean)),pb:rows.map(r=>new Set(r.pb)).filter(s=>s.size>0)};}

function heldoutHit(H,prompt,reply){
 const np=normText(prompt),na=normText(reply);
 if(H.p.has(h16(np)))return true;
 if(na.split(' ').length>=3&&H.a.has(h16(na)))return true;
 const lp=bigrams(np),all=bigrams(np+' '+na);
 for(const s of H.pb){let inter=0;for(const x of s)if(lp.has(x))inter++;
  const union=s.size+lp.size-inter;if(union&&inter/union>=0.6)return true;
  if(s.size>=2){let c=0;for(const x of s)if(all.has(x))c++;if(c===s.size)return true;}}
 return false;}

/** Pure screen. -> {items:[{prompt,reply,id}], report:{total,in,excluded:{heldout,duplicate,exclude},examples:{...}}} */
export function screenTeacherLessons(records,{heldout,existingTexts=[],isShareable}){
 const H=prepareHeldout(heldout);
 const total=Array.isArray(records)?records.length:0;
 const report={total,in:0,excluded:{heldout:0,duplicate:0,exclude:0},examples:{heldout:[],duplicate:[],exclude:[]},screen_ran:!!H};
 if(!H||typeof isShareable!=='function'){report.excluded.screen_unavailable=total;return {items:[],report};}
 const seen=new Set(existingTexts.map(normText));const items=[];
 const out=(why,id)=>{report.excluded[why]++;if(report.examples[why].length<5)report.examples[why].push(id);};
 for(const r of records){
  const id=typeof r?.id==='string'&&/^[0-9a-f-]{8,64}$/i.test(r.id)?r.id:'invalid';
  if(!r||r.kind!==TEACHER_LABEL||r.role!=='TEACHER_NOT_BEAST_VOICE'||typeof r.prompt!=='string'||typeof r.teacher_reply!=='string'){out('exclude',id);continue;}
  const prompt=r.prompt.replace(/\s+/g,' ').trim(),reply=r.teacher_reply.replace(/\s+/g,' ').trim();
  if(!prompt||!reply||!isShareable(prompt)||!isShareable(reply)){out('exclude',id);continue;}
  if(heldoutHit(H,prompt,reply)){out('heldout',id);continue;}
  const key=normText(`${prompt} ${reply}`),keyR=normText(reply);
  if(seen.has(key)||seen.has(keyR)){out('duplicate',id);continue;}
  seen.add(key);seen.add(keyR);items.push({id,prompt,reply});report.in++;}
 return {items,report};}

const HELDOUT_URL=()=>new URL('./heldout-screen.json',import.meta.url);
export async function loadHeldoutScreen(){try{return JSON.parse(await readFile(HELDOUT_URL(),'utf8'));}catch{return null;}}

/** Read every lesson blob (bounded concurrency, hard deadline). Any failure -> null (fail closed: none go in).
 *  `why` (optional object) receives a content-free cause: no_storage | list_failed | read_failed | deadline. */
export async function readTeacherRecords({storageConfig,listBlobs,getBlob,deadlineMs=45000,concurrency=32,why={}}){
 const cfg=storageConfig();if(!cfg){why.cause='no_storage';return null;}
 const t0=Date.now();
 let names;try{names=(await listBlobs(cfg,TEACHER_PREFIX,{max:20000})).filter(n=>n.endsWith('.json')).sort();}catch{why.cause='list_failed';return null;}
 const recs=new Array(names.length);let i=0,failed=null;
 const worker=async()=>{while(!failed&&i<names.length){const k=i++;if(Date.now()-t0>deadlineMs){failed='deadline';return;}
  try{const b=await getBlob(cfg,names[k]);recs[k]=b?JSON.parse(b.text):null;}catch{failed='read_failed';}}};
 await Promise.all(Array.from({length:Math.min(concurrency,names.length)},worker));
 why.listed=names.length;why.ms=Date.now()-t0;
 if(failed){why.cause=failed;return null;}
 return recs;}
