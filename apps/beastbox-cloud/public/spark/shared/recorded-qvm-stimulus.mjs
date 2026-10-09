/** One completed Azure simulator receipt enters the existing classical core once. */
import {advanceCreature} from './behavior.mjs';
import {canonicalJson} from './qpack/canon.mjs';
import {sha256Hex} from './qpack/sha.mjs';
const APPROVED=[
 {job:'dc9a1e78-c423-11f1-ae67-e4fade257188',digest:'b3b53db7eb47e7c70fa94aeea1f7c1532a8db7bf5215b3f324cbf339e9d69370',run:37989851630,keys:['00','11']},
 {job:'32d6fc6c-c42d-11f1-ae67-000d3ad41960',digest:'0960953da112ef2ba6e769354d42842b584e7cd3913d02c2d33461fdadfbf347',run:37996938703,keys:['00','01','10','11']},
 {job:'71cf7c02-c435-11f1-ae67-7ced8d52b5e1',digest:'e559902784bf212d9cd86e1a887bbb69bac908c195133ff3e026b7e695a8db82',run:38002300373,keys:['00','01','10','11']},
 {job:'e26d2fc1-c43a-11f1-ae67-7c1e523ea660',digest:'8c2ee491e0d2518c7d187972e53ee89f4663185137ee9713773904ba2d9d094f',run:38005563477,keys:['00','01','10','11']},
];
const MARKER='beastbox-recorded-qvm-input-v1';
const sameKeys=(object,keys)=>object&&typeof object==='object'&&!Array.isArray(object)&&canonicalJson(Object.keys(object).sort())===canonicalJson([...keys].sort());
export function recordedQvmStimulusPath(beast){
 const source=beast?.genome?.inputs?.quantum_run||'';
 if(/^db4nlt2mb58s7389er6g:bell-(xx|zz)$/.test(source))return '/spark/azure-third-final-ibm-qvm-20261009.json';
 if(/^db4n37g4qg6s73c2de00:bell-(xx|zz)$/.test(source))return '/spark/azure-second-final-ibm-qvm-20261009.json';
 return /^db4m3bslf4us73c2ui9g:bell-(xx|zz)$/.test(source)?'/spark/azure-final-ibm-qvm-20261009.json':'/spark/azure-rigetti-qvm-20261009.json';
}
export function validateRecordedQvmStimulus(receipt){
 const spec=APPROVED.find(row=>row.job===receipt?.job_id);
 if(!spec||!sameKeys(receipt,['schema','source_class','target','job_id','shots','counts','counts_sha256','source_run_id','receipt_origin'])||receipt.schema!=='beastbox-recorded-azure-qvm-stimulus-v1'||receipt.source_class!=='RECORDED_AZURE_CLOUD_SIMULATOR'||receipt.target!=='rigetti.sim.qvm'||receipt.source_run_id!==spec.run||receipt.receipt_origin!=='SANITIZED_ACTIONS_RESULT_LOG')throw Error('Unapproved recorded Azure simulator receipt.');
 if(!sameKeys(receipt.counts,spec.keys)||receipt.shots!==512||Object.values(receipt.counts).some(n=>!Number.isSafeInteger(n)||n<0)||Object.values(receipt.counts).reduce((a,b)=>a+b,0)!==receipt.shots||receipt.counts_sha256!==spec.digest||sha256Hex(canonicalJson(receipt.counts))!==spec.digest)throw Error('Recorded simulator counts or digest changed.');
 return receipt;
}
export function validateQvmStimulusMarker(marker,beast){
 const spec=APPROVED.find(row=>row.job===marker?.job_id);
 if(!spec||!sameKeys(marker,['schema','source_class','job_id','counts_sha256','qbeast_id','seed','tick'])||marker.schema!==MARKER||marker.source_class!=='RECORDED_AZURE_CLOUD_SIMULATOR'||marker.counts_sha256!==spec.digest||marker.qbeast_id!==beast?.qbeast?.profile?.id||marker.seed!==beast?.seed||!Number.isSafeInteger(marker.tick)||marker.tick<0||marker.tick>=1e12)throw Error('Invalid recorded simulator replay marker.');
 return marker;
}
export function applyRecordedQvmStimulus(session,receipt){
 validateRecordedQvmStimulus(receipt);
 const b=session?.beast;if(!b?.qbeast?.profile?.id)throw Error('Select a verified QBEAST before applying a simulator stimulus.');
 if(b.qvmStimulus){validateQvmStimulusMarker(b.qvmStimulus,b);return {ok:true,duplicate:true,marker:structuredClone(b.qvmStimulus)};}
 const p00=receipt.counts['00']/receipt.shots,p11=receipt.counts['11']/receipt.shots;
 const entropy=-Object.values(receipt.counts).map(n=>n/receipt.shots).reduce((sum,p)=>sum+(p?p*Math.log2(p):0),0)/2;
 // Explicit heuristic mapping of recorded simulator statistics, not quantum dynamics.
 const environment={place:'observatory',sound:entropy,toy:p11,attention:p00+p11,comfort:p00};
 const result=advanceCreature(session,environment);
 if(!result.ok)throw Error('Existing behavior core refused the simulator input.');
 b.qvmStimulus={schema:MARKER,source_class:receipt.source_class,job_id:receipt.job_id,counts_sha256:receipt.counts_sha256,qbeast_id:b.qbeast.profile.id,seed:b.seed,tick:result.event.tick};
 return {...result,duplicate:false,environment,marker:structuredClone(b.qvmStimulus)};
}
