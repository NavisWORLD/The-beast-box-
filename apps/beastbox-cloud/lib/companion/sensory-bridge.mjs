/**
 * Consent-gated, bounded bridge from the EXISTING Brain Bay sensor adapters to
 * the existing Beast session and behavior engine. No new identity or storage.
 *
 * Source labels describe inference, not ground truth. Nothing here authorizes
 * a model call, camera capture, native game progress, or signing a QBEAST.
 */
import {beastIdentity} from './session.mjs';
import {advanceCreature} from './behavior.mjs';

export const SENSE_RECORD_SCHEMA='beastbox-local-sense-v1';
const RAW_KEYS=new Set(['image','images','frame','frames','pixels','jpeg','png','webp','base64','blob','audio','pcm','wav','sample','samples','token','api_key','password']);
const privateText=/(?:api[_\s-]?key|password|bearer\s|-----BEGIN|data:image|data:audio|base64,|sk-[a-z0-9_-]{8,})/i;
const safeText=(value,max)=>String(value).replace(/[\u0000-\u001f\u007f]/g,' ').replace(/\s+/g,' ').trim().slice(0,max);
const finiteLevel=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0&&n<=1;
const allowedEngines=new Set(['loudness-only','whisper.cpp','transformers.js','web-speech-fallback']);

export function normalizeSensedEvent(event){
 if(!event||typeof event!=='object'||Array.isArray(event))throw Error('Sensor event must be an object.');
 for(const key of Object.keys(event)){if(RAW_KEYS.has(key))throw Error('Raw sensor media and credentials are not accepted.');}
 const string=JSON.stringify(event);
 if(string.length>1600||privateText.test(string))throw Error('Sensor event contains unsafe or private data.');
 if(event.schema==='companion-vision-event-v1'){
  const model=String(event.model||'');
  if(!/^(moondream|llava)(?::[a-z0-9._-]{1,48})?$/i.test(model)||typeof event.text!=='string'||!event.text.trim()||event.text.length>400)
   throw Error('Invalid local vision summary.');
  if(event.raw_frame_stored!==false)throw Error('Vision summary must declare the frame discarded.');
  return {kind:'vision_summary',source:'LOCAL_VISION_MODEL_INTERPRETATION',engine:model,summary:safeText(event.text,160),sound:0,attention:.6};
 }
 if(event.schema==='companion-hearing-event-v1'){
  if(!allowedEngines.has(event.engine)||!finiteLevel(event.loudness)||typeof event.onset!=='boolean'
     ||typeof event.transcript!=='string'||event.transcript.length>400||event.raw_audio_stored!==false)
   throw Error('Invalid non-media hearing summary.');
  if(event.engine==='loudness-only'&&event.transcript.trim())throw Error('Loudness-only does not transcribe speech.');
  const transcript=safeText(event.transcript,160);
  return {kind:transcript?'speech_summary':'sound_level',
    source:event.engine==='web-speech-fallback'?'BROWSER_SPEECH_MAY_USE_REMOTE_SERVICE':'LOCAL_SOUND_OR_SPEECH',
    engine:event.engine,summary:transcript||'Sound amplitude '+Math.round(event.loudness*100)+'/100',
    sound:event.loudness,attention:event.onset?1:0};
 }
 throw Error('Unrecognized sensor event schema.');
}

/** The UI supplies consent + expected currently selected Beast identity. */
export function applySensedEvent(session,event,{consented=false,expectedId='',nowMs=0,place='grove'}={}){
 if(!consented)return {ok:false,reason:'consent_required'};
 const b=session?.beast,id=beastIdentity(b);
 if(!id||id!==expectedId)return {ok:false,reason:'identity_changed'};
 if(!/^[0-9a-f]{16,128}$/i.test(String(b?.genome?.seed||b?.seed||'')))
  return {ok:false,reason:'verified_seed_required'};
 const record=normalizeSensedEvent(event);
 const now=Number(nowMs);
 if(!Number.isSafeInteger(now)||now<0)return {ok:false,reason:'invalid_time'};
 const old=Array.isArray(b.senseNotes)?b.senseNotes:[];
 // A live microphone can emit every 250ms. Bound persistence and CPU work.
 if(old.length&&now-Number(old[old.length-1].atMs)<8000)
  return {ok:false,reason:'rate_limited'};
 const chosenPlace=['grove','shore','observatory','nest'].includes(place)?place:'grove';
 const note={schema:SENSE_RECORD_SCHEMA,atMs:now,kind:record.kind,source:record.source,engine:record.engine,summary:record.summary};
 const priorXp=b.xp,priorBond=b.bond,priorStage=b.stage,priorNative=b.nativeStage;
 const tick=advanceCreature(session,{place:chosenPlace,sound:record.sound,attention:record.attention,toy:0,comfort:.5});
 if(!tick.ok)return tick;
 b.senseNotes=[...old,note].slice(-8);
 if(beastIdentity(b)!==id||b.xp!==priorXp||b.bond!==priorBond||b.stage!==priorStage||b.nativeStage!==priorNative)
  throw Error('Sensor event crossed creature or game authority boundaries.');
 return {ok:true,kind:record.kind,source:record.source,qbeast_id:id,behavior:tick.event.action,stored:'text-summary-only'};
}

/** Model-facing sensory context requires separate, explicit sharing approval. */
export function modelSensedContext(session,{approved=false}={}){
 if(!approved)return [];
 return (Array.isArray(session?.beast?.senseNotes)?session.beast.senseNotes:[])
  .filter(x=>x?.schema===SENSE_RECORD_SCHEMA&&typeof x.summary==='string')
  .slice(-3).map(x=>('Untrusted '+x.source+' observation: '+safeText(x.summary,100)));
}
