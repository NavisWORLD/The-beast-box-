// Teacher distillation intake (opt-in) + approved export for Zeref training.
// Visitors' teacher pairs stay on their device unless they explicitly opt in.
// Contributions are filtered (secrets/PII), rate-limited and provenance-labeled.
// Non-owner pairs land as PENDING_REVIEW and are never trained on until approved;
// owner-authenticated pairs (Cory's own Ollama / Brain Bay) are auto-approved.
import {createHash,randomUUID,timingSafeEqual} from 'node:crypto';
import {isOwner,safeJson} from '@/lib/security';
import {storageConfig,putBlob,getBlob,listBlobs} from '@/lib/cosmos/azure-blob.mjs';
import {screenText,clean,isTeacherRoute,MAX_PROMPT,MAX_REPLY} from '@/lib/companion/teacher-distill.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const PREFIX='teacher-distill/';
const PER_CLIENT_HOUR=12,PER_INSTANCE_DAY=400;
const hits=new Map<string,number[]>();let day='',dayCount=0;
function limited(client:string){
 const now=Date.now(),today=new Date(now).toISOString().slice(0,10);
 if(today!==day){day=today;dayCount=0;}
 const recent=(hits.get(client)||[]).filter(t=>now-t<3_600_000);
 if(recent.length>=PER_CLIENT_HOUR||dayCount>=PER_INSTANCE_DAY)return true;
 recent.push(now);hits.set(client,recent);dayCount++;
 if(hits.size>5000)hits.clear();
 return false;
}
export async function POST(request:Request){
 if(request.headers.get('origin')!==new URL(request.url).origin)return safeJson(403,{error:'Same-origin request required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{error:'JSON required'});
 const raw=await request.text();
 if(raw.length>4000)return safeJson(413,{error:'Too large'});
 let body:Record<string,unknown>;
 try{const v=JSON.parse(raw);if(!v||typeof v!=='object'||Array.isArray(v))throw 0;body=v;}catch{return safeJson(400,{error:'Invalid JSON'});}
 const keys=Object.keys(body).sort().join(',');
 if(keys!=='consent,model,prompt,provider,teacher_reply'||body.consent!==true)
  return safeJson(400,{error:'Explicit opt-in consent and one teacher pair required'});
 const provider=String(body.provider||'');
 if(!isTeacherRoute(provider))return safeJson(400,{error:'Only teacher providers can contribute'});
 const prompt=clean(body.prompt,MAX_PROMPT),reply=clean(body.teacher_reply,MAX_REPLY),model=clean(body.model,150)||null;
 if(!prompt||!reply)return safeJson(400,{error:'Empty pair'});
 for(const t of [prompt,reply,model||'']){const s=screenText(t||'x');if(!s.ok)return safeJson(422,{error:'Pair rejected by privacy filter: '+s.reason+'. It stays on your device only.'});}
 const fwd=(request.headers.get('x-forwarded-for')||'').split(',')[0].trim();
 const client=createHash('sha256').update('teacher:'+fwd).digest('hex').slice(0,24);
 if(limited(client))return safeJson(429,{error:'Contribution limit reached; try again later.'});
 const cfg=storageConfig();
 if(!cfg)return safeJson(503,{error:'Shared training intake is not configured. Your pair stays on your device.'});
 const owner=await isOwner();
 const status=owner?'OWNER_AUTO_APPROVED':'PENDING_REVIEW';
 const id=randomUUID(),date=new Date().toISOString().slice(0,10);
 const record={schema:'beastbox-teacher-pair-contribution-v1',id,prompt,teacher_reply:reply,provider,model,
  role:'TEACHER_NOT_BEAST_VOICE',review_status:status,source:owner?'owner-bridge':'visitor-opt-in',
  consent:'explicit-opt-in',privacy_filter:'secrets+pii-regex-v1',client_ref_not_stored:true,received_at:new Date().toISOString()};
 const name=`${PREFIX}${owner?'approved':'pending'}/${date}/${id}.json`;
 try{const etag=await putBlob(cfg,name,JSON.stringify(record),{contentType:'application/json',ifNoneMatch:'*'});if(!etag)throw 0;}
 catch{return safeJson(502,{error:'Could not store the pair. It stays on your device.'});}
 return safeJson(201,{ok:true,id,review_status:status});
}
/** Approved pairs as JSONL for the training workflow. Bearer ZEREF_DISTILL_EXPORT_TOKEN only. */
export async function GET(request:Request){
 const want=process.env.ZEREF_DISTILL_EXPORT_TOKEN||'';
 const got=(request.headers.get('authorization')||'').replace(/^Bearer\s+/i,'');
 const a=Buffer.from(createHash('sha256').update(want).digest('hex')),b=Buffer.from(createHash('sha256').update(got).digest('hex'));
 if(want.length<32||!timingSafeEqual(a,b))return safeJson(401,{error:'Unauthorized'});
 const cfg=storageConfig();if(!cfg)return safeJson(503,{error:'Storage not configured'});
 const names=(await listBlobs(cfg,PREFIX+'approved/',{max:2000})).sort().slice(-1500);
 const rows:string[]=[];
 for(const n of names){const blob=await getBlob(cfg,n).catch(()=>null);if(!blob)continue;try{const r=JSON.parse(blob.text);if(r.review_status==='OWNER_AUTO_APPROVED'||r.review_status==='APPROVED')rows.push(JSON.stringify(r));}catch{/* skip */}}
 return new Response(rows.join('\n')+(rows.length?'\n':''),{headers:{'Content-Type':'application/x-ndjson','Cache-Control':'no-store'}});
}
