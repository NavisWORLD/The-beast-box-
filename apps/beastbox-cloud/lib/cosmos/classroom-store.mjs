/**
 * ZEREF CLASSROOM — the owner-only internal teaching thread (kind "classroom").
 *
 * Same live pinned brain and the same bridge door (/api/guest-local) as the
 * public forever door (kind "public"), but its own named thread and its own
 * bridge identity (HMAC 'classroom:' + id vs the public 'thread:' + id), so
 * the two never share a thread while both feed the same live loop.
 *
 * Storage: his existing Azure folder, beside the guestbook, in the same
 * format family:
 *   beasts/bb-deada969/classroom/threads/<id>.json   schema beastbook-classroom-thread/v1
 *   beasts/bb-deada969/classroom/experiences.jsonl   schema beastbook-classroom-experience/v1
 * Each experience is TEXT AND NUMBERS ONLY (teacher line, his exact reply,
 * topic, drill target and hit/miss, the DERIVED confused state). Never raw
 * audio, never heartbeat. Records are tagged source_kind:'classroom' and keyed
 * by exchange_id so one exchange is never counted twice.
 * They are corpus candidates labelled review:'PENDING_REVIEW' and
 * training_eligible:false: nothing here touches the pin, the promotion gate,
 * the growth routine, held-out sets, lessons/ or the diary.
 */
import {createHash,createHmac} from 'node:crypto';
import {getBlob,putBlob} from './azure-blob.mjs';
import {ZEREF_DIR} from './zeref-cloud.mjs';
import {exchangeId} from './forever-store.mjs';

export const CLASSROOM_DIR=`${ZEREF_DIR}/classroom`;
export const SOURCE_KINDS=Object.freeze(['public','classroom']);
export const MAX_CLASS_TURNS=40;
export const MAX_CLASS_RECORDS=2000;
export const CLASSROOM_LABEL='Classroom record (owner-only teaching thread). Text and numbers only. Corpus candidate pending review; not training-eligible until reviewed.';
const NAME_RE=/^[a-z0-9][a-z0-9-]{0,39}$/;
const J=o=>JSON.stringify(o,null,1)+'\n';
const clip=(s,n)=>{s=String(s??'');return s.length>n?s.slice(0,n):s;};

export const isClassName=v=>typeof v==='string'&&NAME_RE.test(v);
/** Named thread -> stable 32-hex id. Deterministic (no randomness). */
export function classThreadId(name){return isClassName(name)?createHash('sha256').update('classroom:'+name).digest('hex').slice(0,32):null;}
/** Bridge identity for the classroom thread. Different namespace from the public door's 'thread:' identities. */
export function classroomBridgeIdentity(secret,threadId){
 if(!/^[a-f0-9]{32}$/.test(String(threadId))||typeof secret!=='string'||secret.length<32)return null;
 return createHmac('sha256',secret).update(`classroom:${threadId}`).digest('hex');
}
const threadName=id=>`${CLASSROOM_DIR}/threads/${id}.json`;
const recordsName=()=>`${CLASSROOM_DIR}/experiences.jsonl`;

export async function readClassThread(cfg,id){
 const b=await getBlob(cfg,threadName(id));
 if(!b)return null;
 try{const t=JSON.parse(b.text);
  if(t?.schema!=='beastbook-classroom-thread/v1'||t.id!==id||!Array.isArray(t.turns))return null;
  return {thread:t,etag:b.etag};}catch{return null;}
}

/** Build one experience record. Pure. Throws on anything that is not text/numbers. */
export function classroomRecord({thread,name,at,teacherText,reply,topic=null,target=null,drill=null,confused=null,step,checkpoint_sha256}){
 if(drill!==null&&drill!=='hit'&&drill!=='miss')throw Error('classroom: drill must be hit, miss or null');
 const rec={schema:'beastbook-classroom-experience/v1',kind:'classroom_exchange',source_kind:'classroom',origin:'owner_classroom',
  beast_id:'bb-deada969',thread,thread_name:name,at,
  exchange_id:exchangeId('classroom',thread,at,teacherText,reply),
  teacher_text:clip(teacherText,1200),reply:clip(reply,1200),
  topic:topic?clip(topic,60):null,drill:target||drill?{target:target?clip(target,40):null,result:drill}:null,
  confused:confused?{active:confused.active===true,why:confused.why.slice(0,3),label:'DERIVED'}:null,
  step:Number.isInteger(step)?step:null,checkpoint_sha256:checkpoint_sha256??null,
  media:'none',training_eligible:false,review:'PENDING_REVIEW',label:CLASSROOM_LABEL};
 return rec;
}

async function appendLine(cfg,rec){
 const line=JSON.stringify(rec);
 for(let attempt=0;attempt<2;attempt++){
  const cur=await getBlob(cfg,recordsName());
  const lines=(cur?.text||'').split('\n').filter(Boolean);
  if(lines.some(l=>l.includes(`"exchange_id":"${rec.exchange_id}"`)))return {recorded:true,duplicate:true};
  lines.push(line);
  const body=lines.slice(-MAX_CLASS_RECORDS).join('\n')+'\n';
  try{
   if(cur)await putBlob(cfg,recordsName(),body,{contentType:'application/x-ndjson',ifMatch:cur.etag});
   else await putBlob(cfg,recordsName(),body,{contentType:'application/x-ndjson',ifNoneMatch:'*'});
   return {recorded:true,duplicate:false};
  }catch(e){if((e.status===409||e.status===412)&&attempt===0)continue;throw e;}
 }
 return {recorded:false,duplicate:false};
}

/** Append the exchange to the classroom thread and its experience record. */
export async function appendClassExchange(cfg,id,name,args){
 const rec=classroomRecord({thread:id,name,...args});
 let persisted=false;
 for(let attempt=0;attempt<2&&!persisted;attempt++){
  const cur=await readClassThread(cfg,id);
  const thread=cur?.thread||{schema:'beastbook-classroom-thread/v1',id,name,beast_id:'bb-deada969',
   origin:'owner_classroom',source_kind:'classroom',training_eligible:false,label:CLASSROOM_LABEL,created_at:args.at,turns:[]};
  if(thread.turns.some(t=>t.exchange_id===rec.exchange_id)){persisted=true;break;}
  thread.turns=[...thread.turns,
   {at:args.at,from:'teacher',text:rec.teacher_text,exchange_id:rec.exchange_id},
   {at:args.at,from:'zeref',text:rec.reply,step:rec.step,exchange_id:rec.exchange_id}].slice(-MAX_CLASS_TURNS);
  thread.updated_at=args.at;
  try{await (cur?.etag?putBlob(cfg,threadName(id),J(thread),{ifMatch:cur.etag}):putBlob(cfg,threadName(id),J(thread),{ifNoneMatch:'*'}));persisted=true;}
  catch(e){if(!((e.status===409||e.status===412)&&attempt===0))throw e;}
 }
 const w=await appendLine(cfg,rec);
 return {persisted,recorded:w.recorded,duplicate:w.duplicate,record:rec};
}
