// Idle teacher lessons (Cory, 2026-10-16): while nobody is chatting, Cory's Ollama
// teachers answer varied prompts; screened pairs feed teacher-distill + Zeref's
// Azure lessons. Teachers are NOT Zeref's voice; training gates still decide promotion.
// Key: ZEREFS_TEACHERS (never printed). Cap: IDLE_TEACHER_CAP per run (default 24).
import {randomUUID} from 'node:crypto';
import {storageConfig,putBlob} from '../lib/cosmos/azure-blob.mjs';
import {storeLesson} from '../lib/cosmos/zeref-cloud.mjs';
import {screenText,clean,MAX_PROMPT,MAX_REPLY} from '../lib/companion/teacher-distill.mjs';
import {pickTeachers} from '../lib/companion/teacher-router.mjs';
const key=process.env.ZEREFS_TEACHERS;
if(!key){console.log('ZEREFS_TEACHERS not set; skipping.');process.exit(0);}
const cfg=storageConfig();
if(!cfg){console.log('Azure storage not configured; skipping.');process.exit(0);}
const cap=Math.max(1,Math.min(60,Number(process.env.IDLE_TEACHER_CAP)||24));
const TOPICS=['the moon','water','stars','friendship','being kind','rain','music','cats','dragons','sleep','colors','the ocean','wind','light and shadow','gravity','trees','being brave','saying sorry','sharing','quantum entanglement','numbers','dreams','home','learning','patience'];
const FORMS=['What is {t}?','Explain {t} to a curious little creature in two sentences.','Why does {t} matter?','Say something kind about {t}.','How does {t} work?','Tell me one fun fact about {t}.'];
const SYSTEM="You are a kind, patient TEACHER helping a young cosmic creature named Zeref learn. You are not Zeref. Answer in 1-3 short, factual, friendly sentences.";
const pick=a=>a[Math.floor(Math.random()*a.length)];
let names=[];
try{const r=await fetch('https://ollama.com/api/tags',{headers:{Authorization:'Bearer '+key},signal:AbortSignal.timeout(10000)});const j=await r.json();names=(j?.models||[]).map(m=>clean(m?.name||m?.model,80)).filter(Boolean);}catch{}
console.log('teacher models available:',names.length||'(fallback only)');
const day=new Date().toISOString().slice(0,10);let stored=0;const used={};
for(let i=0;i<cap;i++){
 const prompt=clean(pick(FORMS).replace('{t}',pick(TOPICS)),MAX_PROMPT);
 const plan=pickTeachers(prompt,names,{preferred:process.env.BEASTBOX_SHARED_OLLAMA_MODELS||'',fallback:'gpt-oss:20b'});
 let reply='',taught='';const tried=[];
 for(const m of plan.order.slice(0,3)){tried.push(m);
  try{const r=await fetch('https://ollama.com/api/chat',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({model:m,stream:false,messages:[{role:'system',content:SYSTEM},{role:'user',content:prompt}],options:{num_predict:200,temperature:0.6}}),signal:AbortSignal.timeout(45000)});
   const j=await r.json().catch(()=>null);const t=r.ok?clean(j?.message?.content,MAX_REPLY):'';if(t){reply=t;taught=m;break;}}catch{}
 }
 if(!reply||!screenText(reply).ok)continue;
 const id=randomUUID();
 const record={schema:'beastbox-teacher-pair-contribution-v1',id,prompt,teacher_reply:reply,provider:'shared-ollama',model:taught,
  teacher_route:{kind:plan.kind,explored:plan.explored,tried},role:'TEACHER_NOT_BEAST_VOICE',review_status:'SHARED_TEACHER_AUTO',
  source:'idle-teacher-actions',consent:'generated-no-visitor-data',privacy_filter:'secrets+pii-regex-v1',received_at:new Date().toISOString()};
 const ok=await putBlob(cfg,`teacher-distill/approved/${day}/${id}.json`,JSON.stringify(record),{ifNoneMatch:'*'}).catch(()=>null);
 if(ok){stored++;used[taught]=(used[taught]||0)+1;await storeLesson(cfg,record).catch(()=>false);}
}
console.log(JSON.stringify({stored,cap,models_used:used}));
