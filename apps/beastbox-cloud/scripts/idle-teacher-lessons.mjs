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
// 2026-10-22 dedupe fix: 24 topics x 6 forms = 144 prompts, so 633 stored lessons collapsed to ~172
// unique prompts in teacher-distill (461 dropped as duplicates). More topics/forms, and prompts now walk
// a shuffled grid by time slot so a prompt does not repeat until the whole grid has been used.
TOPICS.push('sunflowers','butterflies','volcanoes','snow','the desert','bees','honey','owls','fireflies','comets','the sun','planets','black holes','rainbows','thunder','seeds','mushrooms','frogs','whales','penguins','mountains','rivers','clouds','fog','echoes','magnets','electricity','batteries','computers','robots','maps','compasses','telescopes','time','clocks','calendars','birthdays','patience','gratitude','honesty','forgiveness','teamwork','listening','curiosity','mistakes','practice','laughing','hugs','pets','grandparents','cooking','bread','gardens','bridges','boats','trains','kites','drums','guitars','singing','dancing','painting','poems','stories','libraries','the alphabet','counting','shapes','circles','triangles','fractions','the heart','breathing','bones','teeth','the brain','eyes','ears');
FORMS.push('What would a kitten notice first about {t}?','Give one gentle tip about {t}.','What is a surprising thing about {t}?','How would you explain {t} using a toy?','What question should a curious creature ask about {t}?','Describe {t} in one cozy sentence.','What is one safe way to learn about {t}?','Why might {t} make someone smile?','What is the simplest true thing about {t}?','Compare {t} to something in nature.');
const GRID=[];for(const t of TOPICS)for(const f of FORMS)GRID.push(f.replace('{t}',t));
{let h=2166136261;for(let k=GRID.length-1;k>0;k--){h=Math.imul(h^k,16777619)>>>0;const j=h%(k+1);[GRID[k],GRID[j]]=[GRID[j],GRID[k]];}}
const slot=Math.floor(Date.now()/(30*60e3));
const SYSTEM="You are a kind, patient TEACHER helping a young cosmic creature named Zeref learn. You are not Zeref. Answer in 1-3 short, factual, friendly sentences.";
const pick=a=>a[Math.floor(Math.random()*a.length)];
let names=[];
try{const r=await fetch('https://ollama.com/api/tags',{headers:{Authorization:'Bearer '+key},signal:AbortSignal.timeout(10000)});const j=await r.json();names=(j?.models||[]).map(m=>clean(m?.name||m?.model,80)).filter(Boolean);}catch{}
console.log('teacher models available:',names.length||'(fallback only)');
const day=new Date().toISOString().slice(0,10);let stored=0;const used={};
for(let i=0;i<cap;i++){
 const prompt=clean(GRID[(slot*cap+i)%GRID.length],MAX_PROMPT);
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
