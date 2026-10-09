/** The public Spark view selects the existing QBEAST and shared care session.
 * No owner state, sensor samples or model permissions belong in these records. */
import {buildGenome} from './genome.mjs';
import {buildQbeast,loadQbeast,serializeQbeast} from './qbeast.mjs';
import {canonicalJson} from './genome.mjs';
import {sha256Hex} from './sha.mjs';
import {adoptBeast,createSession,exportSession,importSession} from './shared/session.mjs';
export const SESSION_KEY='beastbox-companion-session-v1';
export const QBEAST_KEY='beastbox-quantum-beast-public-v1';
export const PROFILE_KEY='beastbox-active-creature-v1';
const PRIVATE=/(?:api[_ -]?key|password|credential|authorization|biometric|owner[_ -]?memory|private[_ -]?(?:key|state)|-----BEGIN|\bBearer\s|\bsk-[a-z0-9_-]{8,})/i;
const hash=value=>sha256Hex(`QBEAST1\0${canonicalJson(value)}`);
export function checkedSpark(text){
 const {snapshot,card}=loadQbeast(text);
 if(snapshot.events.length<1||snapshot.events.length>2048)throw Error('Spark history is outside its public limits.');
 let head=hash({domain:'genesis',profile:snapshot.profile,public_state:snapshot.public_state,progress:snapshot.progress});
 for(let i=0;i<snapshot.events.length;i++){
  const e=snapshot.events[i];
  if(e.kind!=='memory'||e.generation!==i+1||e.parent!==head||typeof e.payload?.summary!=='string'||e.payload.summary.length>256||PRIVATE.test(e.payload.summary)||typeof e.payload.source_ref!=='string'||!e.payload.source_ref.startsWith('public:')||Object.keys(e.payload).some(k=>!['summary','source_ref'].includes(k)))throw Error('Spark history is not bounded public game memory.');
  const expected=hash({domain:'event',generation:e.generation,parent:e.parent,proposal_id:e.proposal_id,kind:e.kind,payload:e.payload});
  if(e.hash!==expected)throw Error('Spark history checksum failed.');head=e.hash;
 }
 if(head!==snapshot.lineage_head)throw Error('Spark history head mismatch.');
 return {snapshot,card};
}
export function replaySpark(text,byKey){
 const {snapshot,card}=checkedSpark(text),run=byKey.get(card.run);
 if(!run)throw Error('Recorded Spark run is not available.');
 if(Object.values(card.traits).some(v=>!Number.isInteger(v)||v<0||v>100))throw Error('Spark traits are outside 0–100.');
 const gen=buildGenome(card.traits,run,card.user_id,10);
 if(gen.seed!==snapshot.profile.seed||gen.names[2]!==card.name)throw Error('Spark recipe does not reproduce this identity.');
 return {snapshot,gen,run,entry:{traits:card.traits,run:card.run,user:card.user_id}};
}
function stored(raw){if(!raw)return null;const value=JSON.parse(raw);if(value.trustedPublicKey)throw Error('Keep this signed Beast in its trusted host.');return checkedSpark(value.text).snapshot;}
function continuation(next,old){
 if(!old||next.profile.id!==old.profile.id)return;
 if(canonicalJson(next.profile)!==canonicalJson(old.profile)||canonicalJson(next.public_state)!==canonicalJson(old.public_state)||canonicalJson(next.progress)!==canonicalJson(old.progress)||next.generation<old.generation||canonicalJson(next.events.slice(0,old.generation))!==canonicalJson(old.events))throw Error('This selection would rewind or fork the saved Beast.');
}
export function readSparkSession(storage){
 const raw=storage.getItem(SESSION_KEY);const s=importSession(raw?JSON.parse(raw):null);
 if(s.beast?.qbeast){const snap=checkedSpark(serializeQbeast(s.beast.qbeast)).snapshot;if(s.beast.seed!==snap.profile.seed||s.beast.genome?.seed!==snap.profile.seed)throw Error('Saved creature recipe mismatch.');}
 return s;
}
// Caller holds the existing Web Lock when used in a browser.
export function selectSpark(storage,gen,{snapshot=null}={}){
 const raw=storage.getItem(QBEAST_KEY),old=raw?stored(raw):null;
 const genesis=buildQbeast(gen),index=QBEAST_KEY+'-creature-'+genesis.profile.id;
 const knownRaw=storage.getItem(index),known=knownRaw?stored(knownRaw):null;
 const next=snapshot||known||(old?.profile.id===genesis.profile.id?old:genesis);
 const {card}=checkedSpark(serializeQbeast(next));
 if(next.profile.seed!==gen.seed||card.name!==gen.names[2]||card.run!==gen.inputs.quantum_run||canonicalJson(card.traits)!==canonicalJson(gen.inputs.traits)||card.user_id!==(gen.inputs.user_id||null))throw Error('Saved Spark is a different recipe.');
 continuation(next,known);continuation(next,old);
 let session=readSparkSession(storage);
 const previous=session.beast?.qbeast;
 const saved=storage.getItem(SESSION_KEY+'-creature-'+next.profile.id);
 if(session.beast?.seed!==gen.seed){
  session=saved?importSession(JSON.parse(saved)):createSession();
  if(session.beast?.seed!==gen.seed)adoptBeast(session,gen,gen.names[1]);
 }
 session.beast.genome=gen;session.beast.qbeast=next;session.beast.nativeStage=session.beast.nativeStage||1;session.beast.stage=session.beast.nativeStage;
 const updates=new Map([[index,JSON.stringify({text:serializeQbeast(next)})],[QBEAST_KEY,JSON.stringify({text:serializeQbeast(next)})],[PROFILE_KEY,JSON.stringify(next.profile)],[SESSION_KEY,JSON.stringify(exportSession(session))]]);
 if(previous&&previous.profile.id!==next.profile.id)updates.set(SESSION_KEY+'-creature-'+previous.profile.id,storage.getItem(SESSION_KEY));
 if(old&&old.profile.id!==next.profile.id&&!storage.getItem(QBEAST_KEY+'-creature-'+old.profile.id))updates.set(QBEAST_KEY+'-creature-'+old.profile.id,raw);
 const before=new Map([...updates.keys()].map(k=>[k,storage.getItem(k)]));
 try{for(const [k,v] of updates){storage.setItem(k,v);if(storage.getItem(k)!==v)throw Error('The browser could not confirm the device selection. Download your Beast file before leaving.');}}catch(err){for(const [k,v] of before)try{v===null?storage.removeItem(k):storage.setItem(k,v)}catch{}throw err;}
 return session;
}
export function saveSparkSession(storage,session,{metadata={}}={}){
 const current=readSparkSession(storage);
 if(!session.beast?.qbeast||current.beast?.seed!==session.beast.seed)throw Error('Another page changed the selected Beast. Reload before caring for it.');
 const active=stored(storage.getItem(QBEAST_KEY));
 if(active?.profile.id!==session.beast.qbeast.profile.id)throw Error('Another page changed this identity.');
 session.beast.qbeast=active;
 const safeMetadata=Object.fromEntries(['place','trail','sensorLog'].filter(k=>Object.hasOwn(metadata,k)).map(k=>[k,metadata[k]]));
 const text=JSON.stringify({...exportSession(session),...safeMetadata});
 storage.setItem(SESSION_KEY,text);
 if(storage.getItem(SESSION_KEY)!==text)throw Error('The browser could not confirm the device save. Download your Beast file before leaving.');
 return session;
}
export async function withSparkLock(work){
 if(!navigator.locks)throw Error('Saving this Beast needs a browser with Web Locks. You can still download its .qbeast.');
 return navigator.locks.request(QBEAST_KEY,work);
}
