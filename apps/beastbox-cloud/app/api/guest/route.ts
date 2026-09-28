import {createHmac} from 'node:crypto';
import {bridgeConfigured,safeJson} from '@/lib/security';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const HF_ENDPOINT='https://router.huggingface.co/v1/chat/completions';
const MAX_PROMPT=700;
const MODEL_ID=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?$/;

async function boundedJson(response:Response,max:number):Promise<unknown>{
 if(Number(response.headers.get('content-length')||0)>max||!response.body)
  throw new Error('invalid upstream size');
 const reader=response.body.getReader(); const chunks:Uint8Array[]=[];let total=0;
 try{
  while(true){
   const next=await reader.read();if(next.done)break;
   total+=next.value.byteLength;
   if(total>max){await reader.cancel();throw new Error('upstream response too large');}
   chunks.push(next.value);
  }
 }finally{reader.releaseLock();}
 const raw=new Uint8Array(total);let at=0;
 for(const c of chunks){raw.set(c,at);at+=c.byteLength;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
}

export async function POST(request:Request){
 if(request.headers.get('origin')!==new URL(request.url).origin)
  return safeJson(403,{error:'Same-origin guest request required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))
  return safeJson(415,{error:'JSON required'});
 if(Number(request.headers.get('content-length')||0)>1800)
  return safeJson(413,{error:'Guest request exceeds the size limit'});
 let data:unknown;
 try{
  const raw=await request.text();
  if(raw.length>1800)return safeJson(413,{error:'Guest request exceeds the size limit'});
  data=JSON.parse(raw);
 }catch{return safeJson(400,{error:'Invalid guest JSON'});}
 if(!data||typeof data!=='object'||Array.isArray(data))
  return safeJson(400,{error:'Invalid guest request'});
 const item=data as Record<string,unknown>;
 const provider=item.provider;
 if(!['rawrphos-local','huggingface-byok'].includes(String(provider)))
  return safeJson(400,{error:'Choose a supported guest model'});
 if(typeof item.text!=='string'||item.text.trim().length<1||item.text.length>MAX_PROMPT||
    /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(item.text))
  return safeJson(400,{error:'Guest message must contain 1–700 characters'});
 const text=item.text.trim();
 if(provider==='rawrphos-local'){
  if(Object.keys(item).sort().join(',')!=='provider,text')
   return safeJson(400,{error:'Local guest mode only accepts a message'});
  if(!bridgeConfigured())return safeJson(503,{error:'Guest model host is not configured'});
  const secret=process.env.BEASTBOX_CLOUD_AUTH_SECRET;
  if(!secret||secret.length<32)return safeJson(503,{error:'Guest identity signing unavailable'});
  // This opaque hash is only a quota bucket. It grants no access and is never
  // re-used as an owner credential or associated with COSMOS owner memory.
  const forwarded=request.headers.get('x-vercel-forwarded-for')||
    request.headers.get('x-forwarded-for')||'unknown';
  const identity=createHmac('sha256',secret).update(forwarded.slice(0,256)).digest('hex');
  const host=new URL('/api/guest-local',process.env.BEASTBOX_CLOUD_BRIDGE_URL!);
  try{
   const res=await fetch(host,{method:'POST',redirect:'error',cache:'no-store',
    headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,
      'Content-Type':'application/json'},
    body:JSON.stringify({text,guest_identity:identity}),signal:AbortSignal.timeout(55_000)});
   const parsed=await boundedJson(res,16000);
   if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
    return safeJson(502,{error:'Invalid guest host response'});
   const result=parsed as Record<string,unknown>;
   if(!res.ok)
    return safeJson([400,403,429,503].includes(res.status)?res.status:502,
      {error:typeof result.error==='string'&&result.error.length<128?result.error:'Local guest inference unavailable'});
   if(result.schema!=='beastbox-guest-local-v1'||result.model!=='rawrphos-native'||
      result.step!==14000||result.memory_used!==false||result.owner_tools_used!==false||
      result.provider_key_shared!==false||typeof result.reply!=='string'||result.reply.length>6000)
    return safeJson(502,{error:'Unverified guest model response'});
   return safeJson(200,{provider:'rawrphos-local',model:'rawrphos-native',
    step:14000,checkpoint_sha256:result.checkpoint_sha256,reply:result.reply,
    guest_stateless:true});
  }catch{return safeJson(502,{error:'Local guest inference unavailable or timed out'});}
 }
 if(Object.keys(item).sort().join(',')!=='hf_key,model,provider,spend_confirmed,text'||
    item.spend_confirmed!==true||typeof item.hf_key!=='string'||item.hf_key.length<20||
    item.hf_key.length>300||!/^[A-Za-z0-9_-]+$/.test(item.hf_key)||
    typeof item.model!=='string'||item.model.length>150||!MODEL_ID.test(item.model))
  return safeJson(400,{error:'Enter a valid personal Hugging Face token, model ID, and approve possible charges'});
 // Explicit guest BYOK: only this incoming key is forwarded to the FIXED HF
 // router. No owner HF_TOKEN, provider vault, Railway bearer or memory is read.
 try{
  const res=await fetch(HF_ENDPOINT,{method:'POST',redirect:'error',cache:'no-store',
   headers:{Authorization:'Bearer '+item.hf_key,'Content-Type':'application/json'},
   body:JSON.stringify({model:item.model,messages:[{role:'user',content:text}],
     max_tokens:128,temperature:0.3,stream:false}),signal:AbortSignal.timeout(30_000)});
  if(!res.ok){
   // Never return a provider body/header, which may contain user data or secrets.
   return safeJson(res.status===401||res.status===403?401:res.status===429?429:res.status===404?404:502,
    {error:res.status===401||res.status===403?'Hugging Face rejected this guest key or model access':
     res.status===429?'Your Hugging Face account was rate-limited':
     res.status===404?'This Hugging Face model is unavailable to the selected account':'Hugging Face did not complete this inference'});
  }
  const parsed=await boundedJson(res,64000);
  if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
   throw new Error('invalid response');
  const object=parsed as Record<string,unknown>,choices=object.choices;
  if(!Array.isArray(choices)||!choices[0]||typeof choices[0]!=='object')
   throw new Error('missing response');
  const message=(choices[0] as Record<string,unknown>).message;
  if(!message||typeof message!=='object'||Array.isArray(message))
   throw new Error('missing message');
  const answer=(message as Record<string,unknown>).content;
  if(typeof answer!=='string'||!answer.trim()||answer.length>6000)
   throw new Error('invalid text');
  return safeJson(200,{provider:'huggingface-byok',model:item.model,reply:answer,
    guest_stateless:true,charged_to:'guests_own_huggingface_key'});
 }catch{return safeJson(502,{error:'Hugging Face guest inference failed or timed out; no fallback'});}
}
