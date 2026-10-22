/** Identity-checked handoff to the existing native cartridge.
 * Device battery bytes remain unsigned game state, separate from QBEAST genesis.
 * Portable journeyNative data stays quarantined until explicit recovery.
 */
import {serializeQbeast} from '../../public/spark/qbeast.mjs';
import {checkedSpark} from '../../public/spark/identity.mjs';
import {parseSave,profileFromBcp1,profileFromBeastJson} from './lcx1.mjs';
import {injectLatestGrowth} from './lc-ecosystem.mjs';

/* V12.3: when the beast's cosmos diary (beast.cosmos.diary.recent, or opts.growthRecent) has a
   Rigetti QVM SIMULATED growth tick, its LCQ1 record is attached to the native save automatically. */
export function createGameHandoff(beast,opts={}){
 if(!beast?.qbeast)throw Error('Choose a verified Spark Beast before sending it to Lost COSMOS.');
 const text=serializeQbeast(beast.qbeast),{snapshot,card}=checkedSpark(text);
 const {id,seed}=snapshot.profile;
 if(beast.seed!==seed||beast.genome&&beast.genome.seed!==seed)throw Error('The selected Beast seed does not match its canonical identity.');
 const handoff={type:'sol-spark-qbeast',text};
 const states=[beast.game,beast.localGrowth?.game].filter(state=>state&&Object.hasOwn(state,'native_save'));
 if(!states.length)return handoff;
 if(states.length===2&&states[0].native_save!==states[1].native_save)throw Error('Conflicting native saves need recovery before sending this Beast.');
 const growth=beast.localGrowth;
 if(growth?.game&&Object.hasOwn(growth.game,'native_save')&&
    (growth.qbeast_id!==undefined&&growth.qbeast_id!==id||growth.seed!==undefined&&growth.seed!==seed))throw Error('The saved game namespace does not match this Beast identity.');
 const saved=states[0].native_save;
 if(typeof saved!=='string'||saved.length!==43692||!/^[A-Za-z0-9+/]{43691}=$/.test(saved))throw Error('The saved native journey is not a complete 32 KB battery. Recover its original save before continuing.');
 let raw;try{raw=Uint8Array.from(atob(saved),value=>value.charCodeAt(0));}catch{throw Error('The saved native battery encoding is invalid.');}
 const mail=parseSave(raw),expected=profileFromBeastJson(snapshot.profile,card.traits);
 profileFromBcp1(mail.bcp1,{gameSeed:mail.gameSeed});
 if(mail.publicId!==expected.publicId||mail.gameSeed!==expected.gameSeed||!mail.bcp1.every((v,i)=>v===expected.bcp1[i]))throw Error('The saved native journey belongs to another Beast identity.');
 handoff.native_save=saved;
 const recent=opts.growthRecent||beast.cosmos?.diary?.recent||beast.diary?.recent;
 if(recent){const {save,lcq1}=injectLatestGrowth(raw,mail.publicId,recent);
  if(lcq1){let bin='';for(let i=0;i<save.length;i+=8192)bin+=String.fromCharCode(...save.subarray(i,i+8192));handoff.native_save=btoa(bin);handoff.lcq1=lcq1;}}
 return handoff;
}
