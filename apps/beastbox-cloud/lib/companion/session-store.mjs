/** Serializable, identity-checked update for the ONE existing browser Beast store.
 * The caller must hold the existing QBEAST Web Lock; this helper never acquires one.
 */
import {exportSession,importSession} from './session.mjs';
import {SESSION_KEY,QBEAST_KEY,PROFILE_KEY,readSparkSession,saveSparkSession,selectSpark,replaySpark} from '../../public/spark/identity.mjs';
import {serializeQbeast} from '../../public/spark/qbeast.mjs';
/** Recover only an empty local store, under the same lock as ordinary updates. */
export function recoverMirroredSession(storage,raw,byKey){
 if(storage.getItem(SESSION_KEY)!==null)return readSparkSession(storage);
 const next=importSession(raw);if(!next.beast)return next;
 const metadata={place:typeof raw?.place==='string'?raw.place:'grove',trail:raw?.trail||null,sensorLog:Array.isArray(raw?.sensorLog)?raw.sensorLog.filter(x=>typeof x==='string').slice(-8):[]};
 const replay=next.beast.qbeast?replaySpark(serializeQbeast(next.beast.qbeast),byKey):null;
 const keys=[SESSION_KEY,QBEAST_KEY,PROFILE_KEY,...(replay?[QBEAST_KEY+'-creature-'+replay.snapshot.profile.id]:[])];
 const before=new Map(keys.map(k=>[k,storage.getItem(k)]));
 try{
  if(replay){selectSpark(storage,replay.gen,{snapshot:replay.snapshot});next.beast.genome=replay.gen;saveSparkSession(storage,next,{metadata});}
  else {const text=JSON.stringify({...exportSession(next),...metadata});storage.setItem(SESSION_KEY,text);if(storage.getItem(SESSION_KEY)!==text)throw Error('The browser could not confirm the recovered device save.');}
  return next;
 }catch(error){for(const[k,v]of before)try{v===null?storage.removeItem(k):storage.setItem(k,v);}catch{}throw error;}
}
export function selectedIdentity(session){
 const b=session?.beast;
 return b?.qbeast?.profile?.id || (b?.seed ? 'seed:'+b.seed : null);
}
export function updateDeviceSession(storage,expectedId,mutate,extra={},options={}){
 const before=storage.getItem(SESSION_KEY);
 const current=readSparkSession(storage);
 if(selectedIdentity(current)!==expectedId)throw Error('Another page changed the selected Beast. Reload before updating.');
 const draft=importSession(JSON.parse(JSON.stringify(exportSession(current))));
 mutate(draft);
 const selectingUnsigned = options.allowUnsignedAdoption===true && !current.beast?.qbeast && !draft.beast?.qbeast;
 if(selectedIdentity(draft)!==expectedId && !selectingUnsigned)
  throw Error('An ordinary state update cannot replace the Beast identity.');
 if(!selectingUnsigned && (draft.beast?.seed!==current.beast?.seed || draft.beast?.genome?.seed!==current.beast?.genome?.seed))
  throw Error('An ordinary state update cannot replace the original genesis or lineage.');
 // Preserve UI-only trail and sensor metadata without letting a stale React snapshot replace care.
 const metadata={
  place:typeof extra.place==='string'?extra.place:'grove',
  trail:extra.trail||null,
  sensorLog:Array.isArray(extra.sensorLog)?extra.sensorLog.slice(-8):[]};
 if(storage.getItem(SESSION_KEY)!==before)throw Error('The device save changed while this update was being prepared. Try again.');
 if(draft.beast?.qbeast)saveSparkSession(storage,draft,{metadata});
 else {
  const text=JSON.stringify({...exportSession(draft),...metadata});storage.setItem(SESSION_KEY,text);
  if(storage.getItem(SESSION_KEY)!==text)throw Error('The browser could not confirm the device save.');
 }
 return draft;
}
