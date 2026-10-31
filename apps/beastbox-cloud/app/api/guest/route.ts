import {createHmac} from 'node:crypto';
import {bridgeConfigured,safeJson} from '@/lib/security';
import PUBLIC_PIN from '@/lib/rawrphos-public-pin.json';
import {chooseOneVoice,ONE_VOICE_SCHEMA,ONE_VOICE_RULE} from '@/lib/zeref/one-voice.mjs';
// Reviewed public checkpoint pin (14000 unless a chat-not-worse promotion PR changed it).
const PIN_STEP:number=PUBLIC_PIN.training_steps,PIN_SHA:string=PUBLIC_PIN.checkpoint_sha256;
export const runtime='nodejs';
export const dynamic='force-dynamic';
const HF_ENDPOINT='https://router.huggingface.co/v1/chat/completions';
// 1800 characters ~ 630 tokens of the native brain's 2048-token context (see lib/library/limits.mjs).
const MAX_PROMPT=1800;
// A bridge deployed before this limit existed refuses more than this; we then retry once with the tail.
const LEGACY_BRIDGE_PROMPT=700;
const MAX_BODY=8000;
const MODEL_ID=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?$/;

const GROWING_LABEL='Growing Zeref · not the pin';
// Two minds, one voice (Cory 2026-10-31): the growing branch drafts beside the pin. Its draft is checked the same way
// /api/guest-growing checks it; any failure just leaves the gated draft alone (growing = ABSENT, null).
async function growingDraft(text:string,identity:string):Promise<{reply:string;tag:string;checkpoint_sha256:string}|null>{
 try{
  const res=await fetch(new URL('/api/guest-growing',process.env.BEASTBOX_CLOUD_BRIDGE_URL!),{method:'POST',redirect:'error',cache:'no-store',
   headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,'Content-Type':'application/json'},
   body:JSON.stringify({text,guest_identity:identity}),signal:AbortSignal.timeout(55_000)});
  if(!res.ok)return null;
  const r=await boundedJson(res,16000) as Record<string,unknown>;
  if(!r||r.schema!=='beastbox-guest-growing-v1'||r.model!=='rawrphos-native'||r.is_public_pin!==false||r.label!==GROWING_LABEL||
     typeof r.checkpoint_sha256!=='string'||r.checkpoint_sha256===PIN_SHA||typeof r.reply!=='string'||r.reply.length>6000||
     typeof r.tag!=='string'||!/^zeref-growing-\d{3,}$/.test(r.tag))return null;
  return {reply:r.reply,tag:r.tag,checkpoint_sha256:r.checkpoint_sha256};
 }catch{return null;}
}

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
 if(Number(request.headers.get('content-length')||0)>MAX_BODY)
  return safeJson(413,{error:'Guest request exceeds the size limit'});
 let data:unknown;
 try{
  const raw=await request.text();
  if(raw.length>MAX_BODY)return safeJson(413,{error:'Guest request exceeds the size limit'});
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
  return safeJson(400,{error:'Guest message must contain 1–1800 characters'});
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
   const send=(prompt:string)=>fetch(host,{method:'POST',redirect:'error',cache:'no-store',
    headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,
      'Content-Type':'application/json'},
    body:JSON.stringify({text:prompt,guest_identity:identity}),signal:AbortSignal.timeout(55_000)});
   let sent=text;
   const growingP=growingDraft(text,identity);
   let res=await send(sent);
   if(res.status===400&&text.length>LEGACY_BRIDGE_PROMPT){
    // Older bridge: keep the END (the keeper's question and the speaker cue) and say so in the reply metadata.
    sent=text.slice(-LEGACY_BRIDGE_PROMPT).trim();
    res=await send(sent);
   }
   const parsed=await boundedJson(res,16000);
   if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
    return safeJson(502,{error:'Invalid guest host response'});
   const result=parsed as Record<string,unknown>;
   if(!res.ok)
    return safeJson([400,403,429,503].includes(res.status)?res.status:502,
      {error:typeof result.error==='string'&&result.error.length<128?result.error:'Local guest inference unavailable'});
   if(result.schema!=='beastbox-guest-local-v1'||result.model!=='rawrphos-native'||
      result.step!==PIN_STEP||result.checkpoint_sha256!==PIN_SHA||result.memory_used!==false||result.owner_tools_used!==false||
      result.provider_key_shared!==false||typeof result.reply!=='string'||result.reply.length>6000)
    return safeJson(502,{error:'Unverified guest model response'});
   const growing=await growingP;
   const voice=chooseOneVoice(text,{reply:result.reply},growing);
   return safeJson(200,{provider:'rawrphos-local',model:'rawrphos-native',
    step:PIN_STEP,checkpoint_sha256:PIN_SHA,reply:voice.reply||result.reply,
    one_voice:{schema:ONE_VOICE_SCHEMA,rule:ONE_VOICE_RULE,spoken_by:voice.chosen,scores:voice.scores,
     minds:[{role:'gated',label:'GATED (reviewed pin)',step:PIN_STEP,checkpoint_sha256:PIN_SHA},
      {role:'growing',label:'NOT GATED (growing branch)',tag:growing?growing.tag:null,checkpoint_sha256:growing?growing.checkpoint_sha256:null,drafted:growing!==null}]},
    hebbian:result.hebbian===true,state_mode:result.state_mode==='tri'||result.state_mode==='dyn12'?result.state_mode:null,
    guest_stateless:true,prompt_chars:sent.length,
    ...(result.routing&&typeof result.routing==='object'&&!Array.isArray(result.routing)?{routing:result.routing}:{})});
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
