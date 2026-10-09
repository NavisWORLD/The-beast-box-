/** One completed Azure simulator receipt enters the existing classical core once. */
import {advanceCreature} from './behavior.mjs';
import {canonicalJson} from './qpack/canon.mjs';
import {sha256Hex} from './qpack/sha.mjs';
const JOB='dc9a1e78-c423-11f1-ae67-e4fade257188';
const DIGEST='b3b53db7eb47e7c70fa94aeea1f7c1532a8db7bf5215b3f324cbf339e9d69370';
const MARKER='beastbox-recorded-qvm-input-v1';
const sameKeys=(object,keys)=>object&&typeof object==='object'&&!Array.isArray(object)&&canonicalJson(Object.keys(object).sort())===canonicalJson([...keys].sort());
export function validateRecordedQvmStimulus(receipt){
 if(!sameKeys(receipt,['schema','source_class','target','job_id','shots','counts','counts_sha256','source_run_id','receipt_origin'])||receipt.schema!=='beastbox-recorded-azure-qvm-stimulus-v1'||receipt.source_class!=='RECORDED_AZURE_CLOUD_SIMULATOR'||receipt.target!=='rigetti.sim.qvm'||receipt.job_id!==JOB||receipt.source_run_id!==37989851630||receipt.receipt_origin!=='SANITIZED_ACTIONS_RESULT_LOG')throw Error('Unapproved recorded Azure simulator receipt.');
 if(!sameKeys(receipt.counts,['00','11'])||receipt.shots!==512||Object.values(receipt.counts).some(n=>!Number.isSafeInteger(n)||n<0)||Object.values(receipt.counts).reduce((a,b)=>a+b,0)!==receipt.shots||receipt.counts_sha256!==DIGEST||sha256Hex(canonicalJson(receipt.counts))!==DIGEST)throw Error('Recorded simulator counts or digest changed.');
 return receipt;
}
export function validateQvmStimulusMarker(marker,beast){
 if(!sameKeys(marker,['schema','source_class','job_id','counts_sha256','qbeast_id','seed','tick'])||marker.schema!==MARKER||marker.source_class!=='RECORDED_AZURE_CLOUD_SIMULATOR'||marker.job_id!==JOB||marker.counts_sha256!==DIGEST||marker.qbeast_id!==beast?.qbeast?.profile?.id||marker.seed!==beast?.seed||!Number.isSafeInteger(marker.tick)||marker.tick<0||marker.tick>=1e12)throw Error('Invalid recorded simulator replay marker.');
 return marker;
}
export function applyRecordedQvmStimulus(session,receipt){
 validateRecordedQvmStimulus(receipt);
 const b=session?.beast;if(!b?.qbeast?.profile?.id)throw Error('Select a verified QBEAST before applying a simulator stimulus.');
 if(b.qvmStimulus){validateQvmStimulusMarker(b.qvmStimulus,b);return {ok:true,duplicate:true,marker:structuredClone(b.qvmStimulus)};}
 const p00=receipt.counts['00']/receipt.shots,p11=receipt.counts['11']/receipt.shots;
 const entropy=-[p00,p11].reduce((sum,p)=>sum+(p?p*Math.log2(p):0),0)/2;
 // Explicit heuristic mapping of recorded simulator statistics, not quantum dynamics.
 const environment={place:'observatory',sound:entropy,toy:p11,attention:p00+p11,comfort:p00};
 const result=advanceCreature(session,environment);
 if(!result.ok)throw Error('Existing behavior core refused the simulator input.');
 b.qvmStimulus={schema:MARKER,source_class:receipt.source_class,job_id:JOB,counts_sha256:DIGEST,qbeast_id:b.qbeast.profile.id,seed:b.seed,tick:result.event.tick};
 return {...result,duplicate:false,environment,marker:structuredClone(b.qvmStimulus)};
}
