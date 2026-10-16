// Cory's shared Ollama TEACHER for every visitor, guests included (2026-10-16).
// Server-side only: OLLAMA_API_KEY never reaches the browser. The reply is a
// labeled teacher hint, never Zeref's voice (RAWRPHØS stays his voice). Each
// screened pair auto-feeds teacher-distill with provenance; training still only
// promotes through the normal chat gates. Per-visitor + daily caps protect quota.
import {createHash,randomUUID} from 'node:crypto';
import {safeJson} from '@/lib/security';
import {storageConfig,getBlob,putBlob} from '@/lib/cosmos/azure-blob.mjs';
import {storeLesson} from '@/lib/cosmos/zeref-cloud.mjs';
import {pickTeachers} from '@/lib/companion/teacher-router.mjs';
import {screenText,clean,MAX_PROMPT,MAX_REPLY} from '@/lib/companion/teacher-distill.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const PER_VISITOR_HOUR=20;
const dailyCap=()=>Math.max(1,Math.min(5000,Number(process.env.BEASTBOX_SHARED_OLLAMA_DAILY_CAP)||300));
const model=()=>clean(process.env.BEASTBOX_SHARED_OLLAMA_MODEL||'gpt-oss:20b',80);
let catalog:{at:number;names:string[]}={at:0,names:[]};
async function available(key:string){
 // Models the key can use (ollama.com /api/tags), cached 1h; falls back to the configured default.
 if(Date.now()-catalog.at<3_600_000&&catalog.names.length)return catalog.names;
 try{const r=await fetch('https://ollama.com/api/tags',{headers:{Authorization:'Bearer '+key},signal:AbortSignal.timeout(8000)});const j=await r.json();
  const names=(Array.isArray(j?.models)?j.models:[]).map((m:{name?:unknown;model?:unknown})=>clean(m?.name||m?.model,80)).filter(Boolean);
  if(names.length)catalog={at:Date.now(),names};}catch{/* keep cache */}
 return catalog.names.length?catalog.names:[model()];
}
const hits=new Map<string,number[]>();let day='',local=0;
const SYSTEM='You are a kind, patient TEACHER helping a young cosmic creature named Zeref learn. You are not Zeref. Answer the visitor\'s message in 1-3 short, factual, friendly sentences. Never ask for or repeat personal information.';
async function globalCount(today:string){
 // Best-effort shared counter in Azure so the cap holds across serverless instances.
 const cfg=storageConfig();if(!cfg)return null;const name=`teacher-distill/shared-ollama-usage/${today}.json`;
 for(let i=0;i<3;i++){
  const cur=await getBlob(cfg,name).catch(()=>null);const n=cur?Number(JSON.parse(cur.text).count)||0:0;
  if(n>=dailyCap())return n;
  try{await putBlob(cfg,name,JSON.stringify({count:n+1,day:today}),cur?.etag?{ifMatch:cur.etag}:{ifNoneMatch:'*'});return n;}catch{/* retry on race */}
 }
 return dailyCap();
}
export async function GET(){return safeJson(200,{teacher:'Ollama',configured:!!(process.env.ZEREFS_TEACHERS||process.env.OLLAMA_API_KEY),model:model(),role:'TEACHER_NOT_BEAST_VOICE'});}
export async function POST(req:Request){
 if(req.headers.get('origin')!==new URL(req.url).origin)return safeJson(403,{error:'Same-origin request required'});
 const key=process.env.ZEREFS_TEACHERS||process.env.OLLAMA_API_KEY;
 if(!key)return safeJson(503,{error:'The shared Ollama teacher is resting right now.'});
 const raw=await req.text();if(raw.length>2000)return safeJson(413,{error:'Too large'});
 let prompt='';try{prompt=clean(JSON.parse(raw)?.prompt,MAX_PROMPT);}catch{return safeJson(400,{error:'Invalid JSON'});}
 if(!prompt)return safeJson(400,{error:'Type a message first.'});
 const screened=screenText(prompt);
 const ip=(req.headers.get('x-forwarded-for')||'').split(',')[0].trim();
 const visitor=createHash('sha256').update('shared-ollama:'+ip).digest('hex').slice(0,24);
 const now=Date.now(),today=new Date(now).toISOString().slice(0,10);
 if(today!==day){day=today;local=0;}
 const recent=(hits.get(visitor)||[]).filter(t=>now-t<3_600_000);
 if(recent.length>=PER_VISITOR_HOUR||local>=dailyCap())return safeJson(429,{error:'The Ollama teacher needs a rest; try again later.'});
 const used=await globalCount(today);if(used!==null&&used>=dailyCap())return safeJson(429,{error:'The Ollama teacher hit today\'s limit; back tomorrow.'});
 recent.push(now);hits.set(visitor,recent);local++;if(hits.size>5000)hits.clear();
 let reply='',taught='',kind='',tried:string[]=[];
 const plan=pickTeachers(prompt,await available(key),{preferred:process.env.BEASTBOX_SHARED_OLLAMA_MODELS||'',fallback:model()});
 kind=plan.kind;
 for(const m of plan.order.slice(0,3)){
  tried.push(m);
  try{
   const r=await fetch('https://ollama.com/api/chat',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({model:m,stream:false,messages:[{role:'system',content:SYSTEM},{role:'user',content:prompt}],options:{num_predict:200,temperature:0.5}}),signal:AbortSignal.timeout(20000)});
   const j=await r.json().catch(()=>null);
   const text=r.ok?clean(j?.message?.content,MAX_REPLY):'';
   if(text){reply=text;taught=m;break;}
  }catch{/* try next teacher */}
 }
 if(!reply)return safeJson(502,{error:'The Ollama teachers could not answer right now.'});
 // Auto-feed distillation only when both sides pass the secret/PII filter.
 let fed=false;const cfg=storageConfig();
 if(cfg&&screened.ok&&screenText(reply).ok){
  const id=randomUUID();
  const record={schema:'beastbox-teacher-pair-contribution-v1',id,prompt,teacher_reply:reply,provider:'shared-ollama',model:taught,teacher_route:{kind,explored:plan.explored,tried},
   role:'TEACHER_NOT_BEAST_VOICE',review_status:'SHARED_TEACHER_AUTO',source:'cory-shared-ollama',consent:'site-shared-teacher',
   privacy_filter:'secrets+pii-regex-v1',client_ref_not_stored:true,received_at:new Date().toISOString()};
  fed=!!(await putBlob(cfg,`teacher-distill/approved/${today}/${id}.json`,JSON.stringify(record),{ifNoneMatch:'*'}).catch(()=>null));
  // Lesson also joins Zeref's Azure cloud memory folder.
  if(fed)await storeLesson(cfg,record).catch(()=>false);
 }
 return safeJson(200,{ok:true,reply,model:taught,teacher:'Ollama',role:'TEACHER_NOT_BEAST_VOICE',distill:fed?'queued':'skipped'});
}
