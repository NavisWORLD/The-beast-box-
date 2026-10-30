import {bridgeConfigured,isOwner,safeJson} from '@/lib/security';
import {storageConfig} from '@/lib/cosmos/azure-blob.mjs';
import {appendClassExchange,classThreadId,classroomBridgeIdentity,isClassName,readClassThread} from '@/lib/cosmos/classroom-store.mjs';
import {confusedState} from '@/lib/companion/emotion.mjs';
import PUBLIC_PIN from '@/lib/rawrphos-public-pin.json';

// ZEREF CLASSROOM (owner-only, kind "classroom"). Same pinned brain, same
// bridge door (/api/guest-local) and the same reply verification as the
// public forever door (kind "public"), in its own named thread with its own
// bridge identity. See lib/cosmos/classroom-store.mjs.
const PIN_STEP:number=PUBLIC_PIN.training_steps,PIN_SHA:string=PUBLIC_PIN.checkpoint_sha256;
export const runtime='nodejs';
export const dynamic='force-dynamic';
const MAX_TEXT=1200,MAX_BODY=6000,DEFAULT_THREAD='zeref-class';
const NOT_OWNER={error:'The classroom is owner-only. Sign in as the owner to teach Zeref here.',owner:false};

export async function GET(request:Request){
 if(!(await isOwner()))return safeJson(403,NOT_OWNER);
 const name=new URL(request.url).searchParams.get('thread')||DEFAULT_THREAD;
 if(!isClassName(name))return safeJson(400,{error:'Invalid thread name'});
 const id=classThreadId(name)!;const cfg=storageConfig();
 const cur=cfg?await readClassThread(cfg,id).catch(()=>null):null;
 return safeJson(200,{owner:true,kind:'classroom',thread:name,step:PIN_STEP,turns:cur?.thread?.turns||[],storage:!!cfg});
}

export async function POST(request:Request){
 if(!(await isOwner()))return safeJson(403,NOT_OWNER);
 if(request.headers.get('origin')!==new URL(request.url).origin)return safeJson(403,{error:'Same-origin request required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{error:'JSON required'});
 let item:Record<string,unknown>;
 try{const raw=await request.text();if(raw.length>MAX_BODY)return safeJson(413,{error:'Too large'});
  const v=JSON.parse(raw);if(!v||typeof v!=='object'||Array.isArray(v))throw 0;item=v;}
 catch{return safeJson(400,{error:'Invalid JSON'});}
 if(!Object.keys(item).every(k=>['text','thread','topic','target','drill'].includes(k)))
  return safeJson(400,{error:'Classroom accepts text, and optional thread, topic, target, drill'});
 const text=typeof item.text==='string'?item.text.trim():'';
 if(!text||text.length>MAX_TEXT||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text))return safeJson(400,{error:'Teacher line must contain 1–1200 characters'});
 const name=item.thread===undefined?DEFAULT_THREAD:item.thread;
 if(!isClassName(name))return safeJson(400,{error:'Invalid thread name'});
 const str=(v:unknown,n:number)=>v===undefined||v===null?null:(typeof v==='string'&&v.trim().length>0&&v.length<=n?v.trim():undefined);
 const topic=str(item.topic,60),target=str(item.target,40);
 if(topic===undefined||target===undefined)return safeJson(400,{error:'Invalid topic or target'});
 const drill=item.drill===undefined||item.drill===null?null:item.drill;
 if(drill!==null&&drill!=='hit'&&drill!=='miss')return safeJson(400,{error:'drill must be "hit" or "miss"'});
 if(!bridgeConfigured())return safeJson(503,{error:'Brain host is not configured'});
 const secret=process.env.BEASTBOX_CLOUD_AUTH_SECRET;
 if(!secret||secret.length<32)return safeJson(503,{error:'Identity signing unavailable'});
 const id=classThreadId(name as string)!;
 const identity=classroomBridgeIdentity(secret,id)!;
 try{
  const res=await fetch(new URL('/api/guest-local',process.env.BEASTBOX_CLOUD_BRIDGE_URL!),{method:'POST',redirect:'error',cache:'no-store',
   headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,'Content-Type':'application/json'},
   body:JSON.stringify({text,guest_identity:identity}),signal:AbortSignal.timeout(55_000)});
  const raw=await res.text();if(raw.length>16000)return safeJson(502,{error:'Invalid brain host response'});
  const result=JSON.parse(raw) as Record<string,unknown>;
  if(!res.ok)return safeJson([400,403,429,503].includes(res.status)?res.status:502,{error:typeof result.error==='string'&&result.error.length<128?result.error:'Brain unavailable'});
  if(result.schema!=='beastbox-guest-local-v1'||result.model!=='rawrphos-native'||result.step!==PIN_STEP||result.checkpoint_sha256!==PIN_SHA||
     (result.memory_used!==false&&result.hebbian_mode!=='persisted')||result.owner_tools_used!==false||result.provider_key_shared!==false||
     typeof result.reply!=='string'||result.reply.length>6000)
   return safeJson(502,{error:'Unverified brain response'});
  const reply=result.reply;
  const confused=confusedState({reply,target,drill},{confused:true});
  const cfg=storageConfig();const at=new Date().toISOString();
  let w={persisted:false,recorded:false,duplicate:false,exchange_id:null as string|null};
  if(cfg){try{const r=await appendClassExchange(cfg,id,name as string,{at,teacherText:text,reply,topic,target,drill:drill as 'hit'|'miss'|null,confused,step:PIN_STEP,checkpoint_sha256:PIN_SHA});
   w={persisted:r.persisted,recorded:r.recorded,duplicate:r.duplicate,exchange_id:r.record.exchange_id};}catch{/* receipt shows false */}}
  return safeJson(200,{kind:'classroom',thread:name,model:'rawrphos-native',step:PIN_STEP,checkpoint_sha256:PIN_SHA,reply,
   hebbian_mode:result.hebbian_mode==='persisted'||result.hebbian_mode==='in-context'?result.hebbian_mode:null,
   confused_state:confused,record:{...w,source_kind:'classroom',training_eligible:false,review:'PENDING_REVIEW'}});
 }catch{return safeJson(502,{error:'Brain unavailable or timed out'});}
}
