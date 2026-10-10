/** One completed Azure simulator receipt enters the existing classical core once. */
import {advanceCreature} from './behavior.mjs';
import {canonicalJson} from './qpack/canon.mjs';
import {sha256Hex} from './qpack/sha.mjs';
const APPROVED=[
 {job:'e8c296e8-c451-11f1-ae67-3833c5ea2281',digest:'04cb592a1984b8759e40225ceb69057fb740803566c05e075b2c9a0e0f35f7ac',run:38016882014,keys:['00','01','10','11']},
 {job:'dc9a1e78-c423-11f1-ae67-e4fade257188',digest:'b3b53db7eb47e7c70fa94aeea1f7c1532a8db7bf5215b3f324cbf339e9d69370',run:37989851630,keys:['00','11']},
 {job:'32d6fc6c-c42d-11f1-ae67-000d3ad41960',digest:'0960953da112ef2ba6e769354d42842b584e7cd3913d02c2d33461fdadfbf347',run:37996938703,keys:['00','01','10','11']},
 {job:'71cf7c02-c435-11f1-ae67-7ced8d52b5e1',digest:'e559902784bf212d9cd86e1a887bbb69bac908c195133ff3e026b7e695a8db82',run:38002300373,keys:['00','01','10','11']},
 {job:'e26d2fc1-c43a-11f1-ae67-7c1e523ea660',digest:'8c2ee491e0d2518c7d187972e53ee89f4663185137ee9713773904ba2d9d094f',run:38005563477,keys:['00','01','10','11']},
 {job:'d7c48ad5-c442-11f1-ae67-70a8a5253f9c',digest:'0263c31eaed46663ea1e83c759702e611b1d37ee2d0fbbd24d20ad2bcd308f5d',run:38009805252,keys:['00','01','10','11']},
 {job:'3c9e2a90-c45f-11f1-ae67-7ced8dda8a51',digest:'6e8fe47d1f53583623eb98eccd7715117d8dd2f889c0acabc12bef0c9e41f5ba',run:38022572501,keys:['00','01','10','11']},
 {job:'ce11385c-c467-11f1-ae67-6045bdae353a',digest:'29890c8daab6b5cfad8bde076ae1d918b7548db9c9f32b0ceee60f02b0d1c210',run:38025920199,keys:['00','01','10','11']},
 {job:'ea5d60c6-c471-11f1-ae67-e4fade1b1144',digest:'8f7a8a76ee2e7d458044bf27c13cf82078863ee44df0193f24e2598ed49534a8',run:38030239709,keys:['00','01','10','11']},
 {job:'f06449d1-c471-11f1-ae67-e4fade1b1144',digest:'018069d99acbb8af320ee2cf05fada3ba0f55a22c535fff123e44322f9d90117',run:38030239709,keys:['00','01','10','11']},
 {job:'f4e1e2e3-c471-11f1-ae67-e4fade1b1144',digest:'845b264d1d12f24ff745a1aedef5f8e928503009d2a83b854249b517268292ca',run:38030239709,keys:['00','01','10','11']},
 {job:'f9ae5f31-c471-11f1-ae67-e4fade1b1144',digest:'842b16442206eb0f5be795cc419cb58171e933ec7e10e9ef320243851662642b',run:38030239709,keys:['00','01','10','11']},
 {job:'fe224e3d-c471-11f1-ae67-e4fade1b1144',digest:'7b03a2e046c9d88bf695da11439e29c5a94c58b938b3574e04e58aee2f4269b1',run:38030239709,keys:['00','01','10','11']},
];
const MARKER='beastbox-recorded-qvm-input-v1';
const sameKeys=(object,keys)=>object&&typeof object==='object'&&!Array.isArray(object)&&canonicalJson(Object.keys(object).sort())===canonicalJson([...keys].sort());
export function recordedQvmStimulusPath(beast){
 const source=beast?.genome?.inputs?.quantum_run||'';
 if(/^db4tc8kvf2bc73cv3np0:bell-(xx|zz)$/.test(source))return '/spark/azure-zeref-nightcat-dragon-20261010.json';
 if(/^db4tdtkvf2bc73cv3qng:bell-(xx|zz)$/.test(source))return '/spark/azure-umbrascale-starseed-20261010.json';
 if(/^db4te084qg6s73c2m3lg:bell-(xx|zz)$/.test(source))return '/spark/azure-pistonwyrm-gearseed-20261010.json';
 if(/^db4te4g4qg6s73c2m470:bell-(xx|zz)$/.test(source))return '/spark/azure-heartflare-moonfire-20261010.json';
 if(/^db4te7slf4us73c3888g:bell-(xx|zz)$/.test(source))return '/spark/azure-moonwraith-cassette-kit-20261010.json';
 if(/^db4sba4lf4us73c36910:bell-(xx|zz)$/.test(source))return '/spark/azure-lumenwisp-20261010.json';
 if(/^db4rg5klf4us73c34tqg:bell-(xx|zz)$/.test(source))return '/spark/azure-wraith-20261010.json';
 if(/^db4q484vf2bc73cuuuag:bell-(xx|zz)$/.test(source))return '/spark/azure-zeref-heart-sound-20261010.json';
 if(/^db4og3slf4us73c319h0:bell-(xx|zz)$/.test(source))return '/spark/azure-real-song-cst12-umbralet-20261009.json';
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
