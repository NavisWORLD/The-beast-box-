/** Real IBM-measured Wraith — native QBEAST engine, isolated from dragon experiments. */
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
const folder=resolve(root,'apps/beastbox-cloud/experiment-evidence/wraith-photo-ibm-azure-20261010');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const sha=x=>createHash('sha256').update(x).digest('hex');
const check=(v,msg)=>{if(!v)throw Error(msg)};
const receipt=read('_ibm_wraith_videoaudio_light12d_20261009/measurement_receipt.json');
const azure=read('_azure_wraith_videoaudio_light12d_20261009/result.json');
const packet=read('experiment-input/wraith-image-video-audio-light12d-20261009.json');
const sourceImage='303c9d2865195f0f1f7c19eaf889fa989270435e4a3047a7eb6d4b6c6de0449d';
const sourceVideo='ef1e0982371a0d74ab25ee994f51f011bd6efa9b4e7fa5c25ca7a39acf4358f5';
const sourceFeatures='ceede33f8d78a88f8d69e315490558e9bc21c8b88cf935bd8b1e6c52d57e2f04';
check(receipt.schema==='navisworld-ibm-longer-onejob-physics-receipt-v1'&&receipt.job_id==='db4rg5klf4us73c34tqg'&&receipt.backend_name==='ibm_marrakesh'&&receipt.source_class==='RECORDED_IBM_HARDWARE'&&receipt.job_status==='DONE'&&receipt.shot_count===16384,'Missing authentic physical IBM job');
check(sha(canonicalJson(receipt.measurements))===receipt.counts_digest_sha256&&receipt.counts_digest_sha256==='de17933e5400a6c18467bd3a454af5f32147135f517c8ef656fc0e5d36ec5377','IBM measured-count integrity mismatch');
check(receipt.wraith_multisource_pre_hardware?.original_glyph_sha256===sourceImage&&receipt.wraith_multisource_pre_hardware?.original_video_sha256===sourceVideo&&receipt.wraith_multisource_pre_hardware?.qpu_summary_sha256===sourceFeatures&&receipt.wraith_multisource_pre_hardware?.video_motion_and_audio_are_qpu_gate_controls===true,'Source is not original photo conditioned BEFORE QPU');
check(packet.source_image_sha256===sourceImage&&packet.source_video_sha256===sourceVideo&&packet.qpu_summary_sha256===sourceFeatures,'Public image light-field packet changed');
check(azure.source_class==='LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU'&&azure.job_id==='3c9e2a90-c45f-11f1-ae67-7ced8dda8a51'&&azure.shots===512&&azure.counts_sha256==='6e8fe47d1f53583623eb98eccd7715117d8dd2f889c0acabc12bef0c9e41f5ba'&&sha(canonicalJson(azure.counts))===azure.counts_sha256,'Azure provider counts changed');
check(azure.source.ibm_job_id===receipt.job_id&&azure.source.ibm_counts_sha256===receipt.counts_digest_sha256&&azure.source.original_glyph_sha256===sourceImage&&azure.source.original_video_sha256===sourceVideo&&azure.source.wraith_12d_sha256===sourceFeatures,'Azure simulator not derived from THIS image and IBM job');

for(const [index,name] of ['bell_zz','bell_xx','decoupled_zz','decoupled_xx'].entries()){
 const counts=receipt.measurements[name];
 check(Object.values(counts).reduce((a,b)=>a+b,0)===4096,'IBM individual PUB shots changed');
 validateRun({key:receipt.job_id+':'+name,backend:receipt.backend_name,job_id:receipt.job_id,pub_index:index,num_bits:2,shots:4096,counts,counts_sha256:sha(canonicalJson(counts))});
}
const measured=receipt.measurements.bell_xx;
const run=validateRun({key:receipt.job_id+':bell-xx',backend:receipt.backend_name,job_id:receipt.job_id,pub_index:1,num_bits:2,shots:4096,counts:measured,counts_sha256:sha(canonicalJson(measured))});
const features=packet.global_12d;
const traits={focus:Math.round(35+features[5]*45),calm:Math.round(30+features[3]*50),spark:Math.round(45+features[7]*50)};
const stage='WraithGlyphVideoAudio-';let genome=null,selection=-1;
for(let attempt=0;attempt<512;attempt++){
 const candidate=buildGenome(traits,run,stage+attempt,10);
 if(candidate.body==='moth'){genome=candidate;selection=attempt;break;}
}
check(genome&&selection>=0,'No deterministic moth body selected from actual Wraith light and audio-conditioned IBM counts');
check(canonicalJson(genome)===canonicalJson(buildGenome(traits,run,stage+selection,10)),'Measured genome is not reproducible');
const qbeast=buildQbeast(genome);
check(qbeast.profile.id?.startsWith('bb-'),'No canonical QBEAST identity');
const pixels=renderBeast(genome,1,'open');
check(pixels.length===64*64*4,'Native sprite renderer returned wrong bytes');
const session=createSession();adoptBeast(session,genome,'Wraith');session.beast.qbeast=structuredClone(qbeast);session.beast.behavior=createBehavior(session.beast);
const action_trace=[];
for(let t=0;t<48;t++){
 const q=packet.quarter_means_12d[Math.floor(t/12)];
 const env={place:t<12?'observatory':t<24?'grove':t<36?'shore':'observatory',
  sound:q[7],toy:Math.min(1,azure.counts['11']/512+q[6]),attention:q[4],comfort:q[3]};
 const act=advanceCreature(session,env);
 check(act.ok,'Existing Beast Box classical brain declined image-light step '+t);
 action_trace.push({tick:t,source_class:'CLASSICAL_IMAGE_FEATURES_AND_AZURE_SIMULATOR_COUNTS',
  action:act.event.action,environment:env,creature_tick:act.event.tick});
}
const questions=['Hello Wraith. You were generated using a video, sound and real IBM measurements. What would you explore?','The original ghost glyph and the moving video influenced the hardware gates. What can you actually observe?','What can you remember from these 48 steps?'];
const local_conversation=questions.map((message,i)=>({i,message,output:talk(session,message)}));
const save=exportSession(session);const restored=importSession(save);
check(restored.beast?.qbeast?.profile?.id===qbeast.profile.id&&restored.beast?.behavior?.tick===session.beast.behavior.tick,'Same-QBEAST save/load replay failed');
const profile={
 schema:'beastbox-wraith-measured-source-prototype-v1',alias:'Wraith',
 status:'OFF_CHAIN_PROTOTYPE_NOT_MINTED',
 identity:{qbeast_id:qbeast.profile.id,genome_seed:genome.seed,original_native_name:genome.names[1],body:genome.body,
  morphology:'Supplied horned violet phantom identity art; native engine currently uses existing moth silhouette (not a new ghost body)'},
 input:{source_image_sha256:sourceImage,image_feature_sha256:sourceFeatures,source_video_sha256:sourceVideo,source_media_packet_sha256:packet.original_full_packet_sha256,video_duration_seconds:packet.video_duration_seconds,light12d:packet.global_12d,spatiotemporal_quarters:packet.quarter_means_12d},
 quantum:{ibm_job_id:receipt.job_id,ibm_backend:receipt.backend_name,ibm_shots:receipt.shot_count,ibm_counts_sha256:receipt.counts_digest_sha256,
 azure_qvm_job_id:azure.job_id,azure_target:azure.target,azure_simulator_shots:azure.shots,azure_counts_sha256:azure.counts_sha256,
 provider_boundary:'IBM physical quantum measurement, followed by separate Azure CLOUD SIMULATION of classical data; no transported quantum state'},
 stats:qbeast.profile.game.stats,
 behavior:{steps:action_trace.length,action_counts:Object.fromEntries([...new Set(action_trace.map(a=>a.action))].map(action=>[action,action_trace.filter(a=>a.action===action).length])),trace:action_trace},
 local_conversation:{source:'existing CLASSICAL Beast Box talk() helper, not hosted inference',turns:local_conversation},
 provenance:{creator:'NavisWORLD',game_identity_class:'QBEAST1',raw_source_media_in_public_repo:false,token_on_chain:false,save_load_replay_exact:true,body_selection:'deterministic conditional native moth vessel on recorded IBM seed',selection_attempt:selection}
};
mkdirSync(folder,{recursive:true});
writeFileSync(join(folder,'wraith-data.json'),JSON.stringify(profile,null,2)+'\n');
writeFileSync(join(folder,'wraith.qbeast'),serializeQbeast(qbeast));
writeFileSync(join(folder,'wraith-unsigned-session.json'),JSON.stringify(save,null,2)+'\n');
writeFileSync(join(folder,'wraith-64x64-rgba.bin'),Buffer.from(pixels));
console.log('WRAITH_REAL_QBEAST='+JSON.stringify({id:qbeast.profile.id,name:profile.alias,genome_native_name:genome.names[1],body:genome.body,ibm_job:receipt.job_id,azure_job:azure.job_id,behavior_actions:profile.behavior.action_counts,save_load_replay_exact:true,off_chain:true}));
