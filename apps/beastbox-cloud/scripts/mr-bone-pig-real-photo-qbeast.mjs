/** Real IBM-measured Mr Bone Pig — native QBEAST engine, isolated from dragon experiments. */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {validateRun} from '../public/spark/runs.mjs';
import {renderBeast} from '../public/spark/draw.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {createSession,adoptBeast,advanceCreature,exportSession,importSession,talk} from '../lib/companion/session.mjs';
import {createBehavior} from '../lib/companion/behavior.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const folder=resolve(root,'apps/beastbox-cloud/experiment-evidence/mr-bone-pig-photo-ibm-azure-20261010');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const sha=x=>createHash('sha256').update(x).digest('hex');
const check=(v,msg)=>{if(!v)throw Error(msg)};
const receipt=read('_ibm_bone_pig_image_light12d_20261010/measurement_receipt.json');
const azure=read('_azure_bone_pig_image_light12d_20261010/result.json');
const packet=read('experiment-input/mr-bone-pig-original-image-light12d-20261010.json');
const sourceImage='956f9fe57bd80146dfba01f5683fe694daae26ebf9e498f377425be74b973475';
const sourceFeatures='766ee1954035205368387fb407bbe0d1c4fdc6ab96b91b27f0486f8d66e3b472';
check(receipt.schema==='navisworld-ibm-longer-onejob-physics-receipt-v1'&&receipt.job_id==='db4pa784qg6s73c2g5vg'&&receipt.backend_name==='ibm_marrakesh'&&receipt.source_class==='RECORDED_IBM_HARDWARE'&&receipt.job_status==='DONE'&&receipt.shot_count===16384,'Missing authentic physical IBM job');
check(sha(canonicalJson(receipt.measurements))===receipt.counts_digest_sha256&&receipt.counts_digest_sha256==='3d56c29500e4b010b70cc9abb41545024548be21c9ce4185217fb944116952ea','IBM measured-count integrity mismatch');
check(receipt.image_light_pre_hardware?.original_photo_sha256===sourceImage&&receipt.image_light_pre_hardware?.image_feature_commitment_sha256===sourceFeatures,'Source is not original photo conditioned BEFORE QPU');
check(packet.source_file_sha256===sourceImage&&packet.feature_commitment_sha256===sourceFeatures,'Public image light-field packet changed');
check(azure.source_class==='LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU'&&azure.job_id==='6a089c00-c44a-11f1-ae67-70a8a5267256'&&azure.shots===512&&azure.counts_sha256==='f8de71823a1420b6a632aea5fc2609299a9d699054939c1bd296fb3f59b04a23'&&sha(canonicalJson(azure.counts))===azure.counts_sha256,'Azure provider counts changed');
check(azure.source.ibm_job_id===receipt.job_id&&azure.source.ibm_counts_sha256===receipt.counts_digest_sha256&&azure.source.original_photo_sha256===sourceImage,'Azure simulator not derived from THIS image and IBM job');

for(const [index,name] of ['bell_zz','bell_xx','decoupled_zz','decoupled_xx'].entries()){
 const counts=receipt.measurements[name];
 check(Object.values(counts).reduce((a,b)=>a+b,0)===4096,'IBM individual PUB shots changed');
 validateRun({key:receipt.job_id+':'+name,backend:receipt.backend_name,job_id:receipt.job_id,pub_index:index,num_bits:2,shots:4096,counts,counts_sha256:sha(canonicalJson(counts))});
}
const measured=receipt.measurements.bell_xx;
const run=validateRun({key:receipt.job_id+':bell-xx',backend:receipt.backend_name,job_id:receipt.job_id,pub_index:1,num_bits:2,shots:4096,counts:measured,counts_sha256:sha(canonicalJson(measured))});
const features=packet.global_12d;
const traits={focus:Math.round(35+features[3]*45),calm:Math.round(40+features[0]*40),spark:Math.round(55+features[2]*40)};
const stage='BonePigPhoto-';let genome=null,selection=-1;
for(let attempt=0;attempt<512;attempt++){
 const candidate=buildGenome(traits,run,stage+attempt,10);
 if(candidate.body==='pup'){genome=candidate;selection=attempt;break;}
}
check(genome&&selection>=0,'No deterministic pup body selected from genuine image-conditioned IBM counts');
check(canonicalJson(genome)===canonicalJson(buildGenome(traits,run,stage+selection,10)),'Measured genome is not reproducible');
const qbeast=buildQbeast(genome);
check(qbeast.profile.id?.startsWith('bb-'),'No canonical QBEAST identity');
const pixels=renderBeast(genome,1,'open');
check(pixels.length===64*64*4,'Native sprite renderer returned wrong bytes');
const session=createSession();adoptBeast(session,genome,'Mr Bone Pig');session.beast.qbeast=structuredClone(qbeast);session.beast.behavior=createBehavior(session.beast);
const action_trace=[];
for(let t=0;t<48;t++){
 const q=packet.quadrants_12d[Math.floor(t/12)];
 const env={place:t<12?'observatory':t<24?'grove':t<36?'shore':'observatory',
  sound:q[3],toy:Math.min(1,azure.counts['11']/512+q[6]),attention:q[0],comfort:q[11]};
 const act=advanceCreature(session,env);
 check(act.ok,'Existing Beast Box classical brain declined image-light step '+t);
 action_trace.push({tick:t,source_class:'CLASSICAL_IMAGE_FEATURES_AND_AZURE_SIMULATOR_COUNTS',
  action:act.event.action,environment:env,creature_tick:act.event.tick});
}
const questions=['Hello Mr Bone Pig. This is your first moment in the Beast Box photo-light experiment.','Your original portrait conditioned real IBM gates. What shall we explore?','What can you remember from this environment?'];
const local_conversation=questions.map((message,i)=>({i,message,output:talk(session,message)}));
const save=exportSession(session);const restored=importSession(save);
check(restored.beast?.qbeast?.profile?.id===qbeast.profile.id&&restored.beast?.behavior?.tick===session.beast.behavior.tick,'Same-QBEAST save/load replay failed');
const profile={
 schema:'beastbox-mr-bone-pig-measured-source-prototype-v1',alias:'Mr. Bone Pig',
 status:'OFF_CHAIN_PROTOTYPE_NOT_MINTED',
 identity:{qbeast_id:qbeast.profile.id,genome_seed:genome.seed,original_native_name:genome.names[1],body:genome.body,
  morphology:'Original-portrait-inspired pig/boar presentation; canonical base body is pup'},
 input:{source_image_sha256:sourceImage,image_feature_sha256:sourceFeatures,analysis_size:packet.analysis_size,light12d:packet.global_12d,spatial_quadrants:packet.quadrants_12d},
 quantum:{ibm_job_id:receipt.job_id,ibm_backend:receipt.backend_name,ibm_shots:receipt.shot_count,ibm_counts_sha256:receipt.counts_digest_sha256,
 azure_qvm_job_id:azure.job_id,azure_target:azure.target,azure_simulator_shots:azure.shots,azure_counts_sha256:azure.counts_sha256,
 provider_boundary:'IBM physical quantum measurement, followed by separate Azure CLOUD SIMULATION of classical data; no transported quantum state'},
 stats:qbeast.profile.game.stats,
 behavior:{steps:action_trace.length,action_counts:Object.fromEntries([...new Set(action_trace.map(a=>a.action))].map(action=>[action,action_trace.filter(a=>a.action===action).length])),trace:action_trace},
 local_conversation:{source:'existing CLASSICAL Beast Box talk() helper, not hosted inference',turns:local_conversation},
 provenance:{creator:'NavisWORLD',game_identity_class:'QBEAST1',photo_in_public_repo:false,token_on_chain:false,save_load_replay_exact:true,body_selection:'deterministic conditional pup morphology on recorded IBM seed',selection_attempt:selection}
};
mkdirSync(folder,{recursive:true});
writeFileSync(join(folder,'mr-bone-pig-data.json'),JSON.stringify(profile,null,2)+'\n');
writeFileSync(join(folder,'mr-bone-pig.qbeast'),serializeQbeast(qbeast));
writeFileSync(join(folder,'mr-bone-pig-unsigned-session.json'),JSON.stringify(save,null,2)+'\n');
writeFileSync(join(folder,'mr-bone-pig-64x64-rgba.bin'),Buffer.from(pixels));
console.log('MR_BONE_PIG_REAL_QBEAST='+JSON.stringify({id:qbeast.profile.id,name:profile.alias,genome_native_name:genome.names[1],body:genome.body,ibm_job:receipt.job_id,azure_job:azure.job_id,behavior_actions:profile.behavior.action_counts,save_load_replay_exact:true,off_chain:true}));
