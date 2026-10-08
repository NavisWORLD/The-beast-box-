/** Serializable, identity-checked update for the ONE existing browser Beast store.
 * The caller must hold the existing QBEAST Web Lock; this helper never acquires one.
 */
import {exportSession,importSession} from './session.mjs';
import {SESSION_KEY,readSparkSession,saveSparkSession} from '../../public/spark/identity.mjs';
export function selectedIdentity(session){
 const b=session?.beast;
 return b?.qbeast?.profile?.id || (b?.seed ? 'seed:'+b.seed : null);
}
export function updateDeviceSession(storage,expectedId,mutate,extra={}){
 const current=readSparkSession(storage);
 if(selectedIdentity(current)!==expectedId)throw Error('Another page changed the selected Beast. Reload before updating.');
 const draft=importSession(JSON.parse(JSON.stringify(exportSession(current))));
 mutate(draft);
 if(selectedIdentity(draft)!==expectedId)throw Error('An ordinary state update cannot replace the Beast identity.');
 if(draft.beast?.seed!==current.beast?.seed || draft.beast?.genome?.seed!==current.beast?.genome?.seed)
  throw Error('An ordinary state update cannot replace the original genesis or lineage.');
 if(draft.beast?.qbeast)saveSparkSession(storage,draft);
 else storage.setItem(SESSION_KEY,JSON.stringify(exportSession(draft)));
 // Preserve UI-only trail and sensor metadata without letting a stale React snapshot replace care.
 storage.setItem(SESSION_KEY,JSON.stringify({...exportSession(draft),
  place:typeof extra.place==='string'?extra.place:'grove',
  trail:extra.trail||null,
  sensorLog:Array.isArray(extra.sensorLog)?extra.sensorLog.slice(-8):[]}));
 return draft;
}
