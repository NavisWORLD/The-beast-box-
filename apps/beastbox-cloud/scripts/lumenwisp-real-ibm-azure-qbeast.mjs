/** SECOND quantum generation: verified parent pixels → NEW physical IBM → NEW Azure → new QBEAST. */
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
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const sha=x=>createHash('sha256').update(x).digest('hex');
const check=(v,msg)=>{if(!v)throw Error(msg)};
const parent='bb-4a61a8d5';
const expectedJob='db4sba4lf4us73c36910',expectedCounts='62effbad67bf75e985c0250e0c8a6b1d94f92d8c9e46d25e52a81975461bcce7';
const expectedPacket='47dd7682ace55167c070e6703d8cb3defedb7c44e1302054533996d7b0097720';
const receipt=read('_ibm_lumenwisp_native_pixel12d_20261009/measurement_receipt.json');
const azure=read('_azure_lumenwisp_native_pixel12d_20261009/result.json');
const packet=read('build/lumenwisp-pre-qpu/feature_packet.json');
check(receipt.source_class==='RECORDED_IBM_HARDWARE'&&receipt.job_status==='DONE'&&receipt.job_id===expectedJob&&receipt.backend_name==='ibm_marrakesh'&&receipt.shot_count===16384,'Missing exact fresh new physical IBM job');
check(receipt.counts_digest_sha256===expectedCounts&&sha(canonicalJson(receipt.measurements))===expectedCounts,'New physical QPU counts were changed');
check(receipt.second_generation_pre_hardware?.parent_qbeast_id===parent&&receipt.second_generation_pre_hardware?.feature_packet_sha256===expectedPacket,'Not an authentic Wraith offspring image conditioned BEFORE hardware');
check(packet.parent_qbeast_id===parent&&packet.feature_packet_sha256===expectedPacket,'Parent native sprite lineage changed');
check(azure.source_class==='LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU'&&azure.shots===512&&azure.target==='rigetti.sim.qvm','Missing separate actual Azure simulation');
check(sha(canonicalJson(azure.counts))===azure.counts_sha256&&Object.values(azure.counts).reduce((a,b)=>a+b,0)===512,'Azure simulator results corrupted');
check(azure.source.ibm_job_id===expectedJob&&azure.source.ibm_counts_sha256===expectedCounts&&azure.source.native_spritelight_12d_sha256===expectedPacket,'Azure does not derive from the original freshly measured IBM job');
const verifiedRuns=[];
for(const [index,name] of ['bell_zz','bell_xx','decoupled_zz','decoupled_xx'].entries()){
 const counts=receipt.measurements[name];
 check(Object.values(counts).reduce((a,b)=>a+b,0)===4096,'Four real PUBs each require 4096 actual hardware shots');
 verifiedRuns.push(validateRun({key:expectedJob+':'+name,backend:receipt.backend_name,job_id:receipt.job_id,pub_index:index,num_bits:2,shots:4096,counts,counts_sha256:sha(canonicalJson(counts))}));
}
const run=verifiedRuns[1];
const g=packet.global_12d;
const traits={focus:Math.round(35+g[0]*55),calm:Math.round(24+g[3]*60),spark:Math.round(40+g[11]*60)};
const genome=buildGenome(traits,run,'Lumenwisp-Generation2',10);
const qbeast=buildQbeast(genome);
check(qbeast.profile.id!==parent&&qbeast.profile.id?.startsWith('bb-'),'Offspring must have distinct canonical identity');
check(canonicalJson(genome)===canonicalJson(buildGenome(traits,run,'Lumenwisp-Generation2',10)),'Offspring genome is not reproducible');
const sprite=renderBeast(genome,1,'open');check(sprite.length===64*64*4,'Native sprite bytes invalid');
const session=createSession();adoptBeast(session,genome,'Lumenwisp');session.beast.qbeast=structuredClone(qbeast);
session.beast.behavior=createBehavior(session.beast);
const trace=[];
for(let i=0;i<48;i++){
 const q=packet.quarter_means_12d[Math.floor(i/12)];
 const environment={place:i<12?'observatory':i<24?'grove':i<36?'shore':'observatory',
  sound:Math.min(1,q[11]),toy:Math.min(1,azure.counts['11']/512+q[4]),attention:q[0],comfort:q[3]};
 const step=advanceCreature(session,environment);check(step.ok,'Classical environment update failed at '+i);
 trace.push({step:i,action:step.event.action,behavior_tick:step.event.tick,environment,mode:'CLASSICAL_SIMULATION_FROM_REAL_MEASURED_SEED'});
}
const questions=['Hello Lumenwisp. What can you sense from your saved software world?',
 'You descend from Wraith, whose recorded native sprite helped set new IBM hardware gates. What do you know?',
 'The IBM job was physical and Azure was a separate simulator. What are your limits?'];
const patternConversation=questions.map((question,index)=>({index,question,result:talk(session,question),source:'CLASSICAL_LOCAL_PATTERN_NOT_RAWRPHOS'}));
const saved=exportSession(session),restored=importSession(saved);
check(restored.beast?.qbeast?.profile?.id===qbeast.profile.id&&restored.beast?.behavior?.tick===session.beast.behavior.tick,'Portable identity or behavior replay was lost');
const dir=resolve(root,'apps/beastbox-cloud/experiment-evidence/lumenwisp-real-generation2-20261009');mkdirSync(dir,{recursive:true});
const report={
 schema:'beastbox-lumenwisp-authentic-second-generation-ibm-azure-qbeast-v1',
 alias:'Lumenwisp',parent_qbeast_id:parent,offspring_qbeast_id:qbeast.profile.id,
 identity:{id:qbeast.profile.id,genome_seed:genome.seed,native_engine_name:genome.names[1],body:genome.body},
 physics:{ibm_job_id:receipt.job_id,ibm_backend:receipt.backend_name,ibm_hardware_shots:receipt.shot_count,
  ibm_counts_sha256:receipt.counts_digest_sha256,azure_job_id:azure.job_id,azure_simulator_shots:azure.shots,
  azure_counts_sha256:azure.counts_sha256,
  original_source:'actual prior Wraith QBEAST generated sprite and 48 CLASSICAL behavior decisions',
  source_packet_sha256:expectedPacket,quantum_state_transported:false},
 stats:qbeast.profile.game.stats,
 trace,patternConversation,
 acceptance:{fresh_IBM_hardware:true,cloud_Azure_simulator:true,
  actual_model_training_in_this_job:false,actual_RAWRPHOS_game_model_reply_in_this_job:false,
  portable_save_load_exact:true,active_game_played:false,not_biological_life:true}
};
writeFileSync(join(dir,'lumenwisp-new-qbeast-data.json'),JSON.stringify(report,null,2)+'\n');
writeFileSync(join(dir,'lumenwisp.qbeast'),serializeQbeast(qbeast));
writeFileSync(join(dir,'lumenwisp-portable-session.json'),JSON.stringify(saved,null,2)+'\n');
writeFileSync(join(dir,'lumenwisp-native-64x64-rgba.bin'),Buffer.from(sprite));
console.log('LUMENWISP_ACTUAL_NEW_MEASURED_QBEAST='+JSON.stringify({id:report.offspring_qbeast_id,
 name:report.alias,parent:report.parent_qbeast_id,ibm_job:report.physics.ibm_job_id,
 azure_job:report.physics.azure_job_id,behavior_steps:trace.length,save_load_verified:true}));
