/** Public adapters only. Provider choice reuses unsigned session growth.
 * This module never mutates the session, probes a host, or calls owner APIs. */
import {guestBody,interpretModelResult} from './brain.mjs';
import {isKidSafe,replyFromMind} from './learn.mjs';
import {shownName,swapBrain} from './session.mjs';
import {loopbackOnly} from '../companion-local.mjs';

export const PUBLIC_BRAINS=['local-mind','guest-rawrphos','loopback-ollama'];
const OLLAMA='http://127.0.0.1:11434/api/chat';
const MODEL_TAG=/^[A-Za-z0-9][A-Za-z0-9_.:/-]*$/;

export function publicBrainProvider(session){
 const provider=session?.beast?.localGrowth?.model?.provider;
 return PUBLIC_BRAINS.includes(provider)?provider:'local-mind';
}
export function setPublicBrain(session,provider){
 if(!PUBLIC_BRAINS.includes(provider))throw Error('Choose a public provider');
 return swapBrain(session,provider);
}
function pattern(session,text,failure=''){
 return {ok:true,reply:replyFromMind(session.mind,text,shownName(session.beast)),source:'local-mind',
  label:failure?'On-device pattern fallback · not a model answer.':'On-device pattern memory · no language model connected.',
  moduleReady:!failure,fallback:Boolean(failure),failure};
}
async function boundedJson(response){
 if(Number(response.headers.get('content-length')||0)>32000||!response.body)throw Error('Invalid response size');
 const reader=response.body.getReader(),chunks=[];
 let bytes=0;
 try{
  while(true){
   const next=await reader.read();if(next.done)break;
   bytes+=next.value.byteLength;
   if(bytes>32000){await reader.cancel();throw Error('Response too large');}
   chunks.push(next.value);
  }
 }finally{reader.releaseLock();}
 const raw=new Uint8Array(bytes);let at=0;
 for(const chunk of chunks){raw.set(chunk,at);at+=chunk.byteLength;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
}
/** Execute only when the caller submits a message. No history or identity is transmitted.
 * @param {any} session
 * @param {string} text
 * @param {{fetcher?:typeof fetch,ollamaModel?:string,signal?:AbortSignal}} [options]
 */
export async function runPublicBrain(session,text,{fetcher=globalThis.fetch,ollamaModel='',signal=undefined}={}){
 const saying=String(text||'').trim().slice(0,400);
 if(!session?.beast||!saying)return {ok:false,reason:!session?.beast?'Meet a Beast first.':'Enter a short message.'};
 const provider=publicBrainProvider(session);
 if(provider==='local-mind'||!isKidSafe(saying))return pattern(session,saying);
 const local=provider==='loopback-ollama',model=String(ollamaModel||'').trim();
 if(local&&(!MODEL_TAG.test(model)||model.includes('://')||model.length>80))return pattern(session,saying,'Enter your installed local Ollama model tag before sending.');
 try{
  if(typeof fetcher!=='function')throw Error('Fetch unavailable');
  if(local&&!loopbackOnly(OLLAMA))throw Error('Loopback required');
  const response=await fetcher(local?OLLAMA:'/api/guest',{
   method:'POST',credentials:local?'omit':'same-origin',redirect:'error',mode:local?'cors':'same-origin',
   headers:{'Content-Type':'application/json'},signal,
   body:JSON.stringify(local?{model,stream:false,messages:[{role:'user',content:saying}],options:{num_predict:128,temperature:.3}}:guestBody(saying)),
  });
  if(!response.ok)throw Error('Provider unavailable');
  const payload=await boundedJson(response);
  if(local){
   const reply=typeof payload?.message?.content==='string'?payload.message.content.trim():'';
   if(payload?.done!==true||typeof payload?.model!=='string'||!payload.model.trim()||payload.model.length>80||!reply||reply.length>6000)throw Error('Unverified local response');
   return {ok:true,reply,source:'loopback-ollama',model:payload.model,label:`Local Ollama · ${payload.model}`,moduleReady:true,fallback:false,failure:''};
  }
  const result=interpretModelResult('guest-rawrphos',payload);
  if(!result.ok||!result.reply||result.reply.length>6000)throw Error('Unverified guest response');
  return {...result,label:'RAWRPHØS guest · verified stateless native 14K response',moduleReady:true,fallback:false,failure:''};
 }catch{
  return pattern(session,saying,local?'Local Ollama is unavailable, or the browser blocked its loopback connection.':'RAWRPHØS guest is unavailable or returned unverified text.');
 }
}
