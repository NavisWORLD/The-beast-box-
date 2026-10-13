/** Explicit adapter from an authorized private API read to existing behavior rules.
 * No model weights, native progression or immutable quantum genesis are changed.
 */
import {advanceCreature} from './behavior.mjs';
import {canonicalJson} from '../../public/spark/genome.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';
export function applyPrivateQvmStimulus(session,record,expectedOwner){
 const b=session?.beast,receipt=record?.simulationReceipts?.at(-1);
 if(!b?.qbeast?.profile.id||record?.owner!==expectedOwner||record.beastId!==b.qbeast.profile.id||record.profile?.provenance.seed!==b.seed)throw Error('Private quantum state belongs to another owner or creature.');
 if(receipt?.status!=='RIGETTI_QVM_REMOTE')return {ok:false,blocked:true};
 const {mac,receipt_hash,...unsigned}=receipt;
 if(receipt.owner!==expectedOwner||receipt.beast_id!==record.beastId||receipt.target!=='rigetti.sim.qvm'||receipt.shots<1||receipt.shots>256||!receipt.job_id||sha256Hex(canonicalJson(unsigned))!==receipt_hash)throw Error('Private simulator receipt integrity failed.');
 const counts=receipt.counts,keys=Object.keys(counts||{});if(!keys.length||keys.some(k=>!/^[01]{3}$/.test(k))||Object.values(counts).some(n=>!Number.isInteger(n)||n<0)||Object.values(counts).reduce((sum,n)=>sum+n,0)!==receipt.shots)throw Error('Private simulator counts failed validation.');
 if(b.privateCosmosStimulus?.owner===expectedOwner&&b.privateCosmosStimulus?.receiptHash===receipt_hash)return {ok:true,duplicate:true};
 const p=k=>(counts[k]||0)/receipt.shots,entropy=-Object.values(counts).reduce((sum,n)=>{const q=n/receipt.shots;return sum+(q?q*Math.log2(q):0);},0)/3;
 const environment={place:'observatory',sound:entropy,toy:p('111'),attention:p('000')+p('111'),comfort:p('000')};
 const result=advanceCreature(session,environment);if(!result.ok)throw Error('Existing behavior rules refused private simulator inputs.');
 b.privateCosmosStimulus={source:'authorized private API; remote simulator result mapped by classical rules',owner:expectedOwner,receiptHash:receipt_hash,qbeastId:record.beastId,seed:b.seed,behaviorTick:result.event.tick};
 return {...result,duplicate:false,environment};
}
