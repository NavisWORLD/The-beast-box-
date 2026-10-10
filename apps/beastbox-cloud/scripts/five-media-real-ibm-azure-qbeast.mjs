/** Five new canonical QBEASTs from five NEW actual IBM QPU receipts + Azure QVM. */
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
const base=root+'/apps/beastbox-cloud/experiment-evidence/five-media-genesis-20261010';
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const sha=x=>createHash('sha256').update(x).digest('hex');
const check=(v,m)=>{if(!v)throw Error(m)};
const manifest='7e34156b41e37c65cc1b8bba6810ca27764afc52cfaa9b5c64c7e146e61598ab';
const expected=[
 ['Zeref-Nightcat-Dragon','db4tc8kvf2bc73cv3np0','ee0ecbc7d7073f6a130653ca8ed0f89f56876138a6dea49664477157f988e1bb'],
 ['Umbrascale-Starseed','db4tdtkvf2bc73cv3qng','c8ab49c149cdc4c2e6d1f23decd6f54cd8b3571b6c0b6f2546810752ba207376'],
 ['Pistonwyrm-Gearseed','db4te084qg6s73c2m3lg','cfe37f452193e1502c2390a68dd412712ae7f53bdc98dde90997bf2a22dc1882'],
 ['Heartflare-Moonfire','db4te4g4qg6s73c2m470','bc36ac7a9e6866b0c15314144d58847293499ab8a20d4725ea93ec274531cc97'],
 ['Moonwraith-Cassette-Kit','db4te7slf4us73c3888g','59c3ae19b5b8c3e0f03353ccdf5471dd5c5718fed5e4ee1969d0f57bb6f07aec']
];
const input=read('experiment-input/five-creature-real-media-12d-20261010.json');
check(input.full_source_manifest_sha256===manifest&&input.creatures.length===5,'Input media provenance changed');
const results=[];
for(const [i,[name,expectedIBM,expectedDigest]] of expected.entries()){
 const slug=name.toLowerCase(),folder=(i+1)+'-'+slug;
 const ibm=read('_ibm_five_multisource_qbeasts_20261010/'+folder+'/measurement_receipt.json');
 const azure=read('_azure_five_multisource_qbeasts_20261010/'+folder+'/result.json');
 const source=input.creatures[i];
 check(source.name===name,'Different creature source order');
 check(ibm.source_class==='RECORDED_IBM_HARDWARE'&&ibm.status==='DONE'&&ibm.alias===name&&ibm.job_id===expectedIBM&&ibm.shots===16384&&ibm.counts_sha256===expectedDigest,'Missing exact NEW physical provider evidence');
 check(sha(canonicalJson(ibm.counts))===ibm.counts_sha256&&ibm.source_manifest_sha256===manifest&&ibm.input_windows48_sha256===source.windows48_sha256,'Actual physical IBM measurements changed');
 check(azure.creature===name&&azure.source_class==='LIVE_AZURE_CLOUD_SIMULATOR_NOT_QPU'&&azure.target==='rigetti.sim.qvm'&&azure.shots===512,'No real cloud simulator receipt for this creature');
 check(azure.source.ibm_job_id===expectedIBM&&azure.source.ibm_full_counts_sha256===expectedDigest&&azure.source.source_manifest_sha256===manifest,'Azure job does not derive from this actual IBM job');
 check(sha(canonicalJson(azure.counts))===azure.counts_sha256&&Object.values(azure.counts).reduce((a,b)=>a+b,0)===512,'Azure simulator counts are invalid');
 const runs=[];
 for(const [index,label] of ['bell_zz','bell_xx','decoupled_zz','decoupled_xx'].entries()){
  const c=ibm.counts[label];check(Object.values(c).reduce((a,b)=>a+b,0)===4096,'Physical four-PUB shot total changed');
  runs.push(validateRun({key:expectedIBM+':'+label,backend:ibm.backend_name,job_id:expectedIBM,pub_index:index,num_bits:2,shots:4096,counts:c,counts_sha256:sha(canonicalJson(c))}));
 }
 const v=source.global_12d;
 const traits={focus:Math.round(35+v[3]*50),calm:Math.round(28+v[0]*60),spark:Math.round(38+v[7]*60)};
 const genome=buildGenome(traits,runs[1],name+'-original-five-media',10);
 const qbeast=buildQbeast(genome);
 check(qbeast.profile.id.startsWith('bb-'),'Native QBEAST identity invalid');
 check(canonicalJson(buildGenome(traits,runs[1],name+'-original-five-media',10))===canonicalJson(genome),'Quantum-seeded genome not reproducible');
 const pixel=renderBeast(genome,1,'open');check(pixel.length===64*64*4,'Native sprite bytes invalid');
 const session=createSession();adoptBeast(session,genome,name);session.beast.qbeast=structuredClone(qbeast);
 session.beast.behavior=createBehavior(session.beast);
 const trace=[];
 const places=['observatory','grove','shore','observatory'];
 for(let step=0;step<48;step++){
  const env={place:places[Math.floor(step/12)],sound:v[7],toy:Math.min(1,azure.counts['11']/512+v[6]),
    attention:v[0],comfort:v[3]};
  const run=advanceCreature(session,env);
  check(run.ok,'Classical creature step failed '+step);
  trace.push({step,action:run.event.action,creature_tick:run.event.tick,environment:env,
   input_provenance:'AVERAGED_REAL_48_WINDOW_MEDIA_NUMBERS_PLUS_ACTUAL_AZURE_SIMULATOR_COUNTS'});
 }
 const save=exportSession(session);const restored=importSession(save);
 check(restored.beast?.qbeast?.profile?.id===qbeast.profile.id&&restored.beast?.behavior?.tick===session.beast.behavior.tick,'Native QBEAST state/save replay not exact');
 const localMessages=['Hello '+name+'. These are the first recorded classical software turns.','You were seeded from original images and song/video waveforms before actual IBM hardware measurement. What do you do next?','What do you know about the difference between real hardware quantum measurements and a simulated creature?'];
 const localResponses=localMessages.map((prompt,j)=>({turn:j,prompt,response:talk(session,prompt),source_class:'CLASSICAL_LOCAL_TEMPLATE_NOT_HOSTED_MODEL'}));
 const directory=join(base,folder);mkdirSync(directory,{recursive:true});
 const metadata={name:name+' // QBEAST Alive Card (Unminted)',description:'A fictional digital creature determined reproducibly from actual photo/audio-conditioned IBM Quantum hardware measurements and separate Azure Rigetti QVM simulation. Behavior and conversations are classical software.',image:'pending-unminted-image',animation_url:'pending-gif',
  attributes:[{trait_type:'QBEAST ID',value:qbeast.profile.id},{trait_type:'Native Body',value:genome.body},{trait_type:'Physical IBM Job',value:ibm.job_id},{trait_type:'IBM Backend',value:ibm.backend_name},{trait_type:'IBM Measured Shots',value:16384},{trait_type:'Azure Rigetti QVM Job',value:azure.job_id},{trait_type:'Source Media Manifest SHA256',value:manifest},{trait_type:'Mint Status',value:'UNMINTED'}],
  minted:false,token_id:null,contract_address:null,chain:null};
 const report={schema:'navisworld-five-new-measured-multimedia-qbeast-v1',alias:name,
  identity:{qbeast_id:qbeast.profile.id,genome_seed:genome.seed,native_name:genome.names[1],body:genome.body},
  source:{manifest_sha256:manifest,image_sha256:source.primary_image_sha256,song_sha256:input.source_song_sha256,
   video_sha256:[input.source_long_video_sha256,input.source_wraith_video_sha256],
   heartbeat_source_mp3_available:false,windows48_sha256:source.windows48_sha256},
  quantum:{ibm_job_id:ibm.job_id,ibm_backend:ibm.backend_name,ibm_shots:16384,ibm_counts_sha256:ibm.counts_sha256,
   azure_simulator_job_id:azure.job_id,azure_simulator_shots:512,azure_counts_sha256:azure.counts_sha256,
   actual_optical_light_injection:false,quantum_state_transport:false},
  stats:qbeast.profile.game.stats,
  behavior:{steps:48,action_counts:Object.fromEntries([...new Set(trace.map(a=>a.action))].map(a=>[a,trace.filter(t=>t.action===a).length])),trace},
  local_conversation:{source_class:'CLASSICAL_TEMPLATE_NOT_MODEL_INFERENCE',turns:localResponses},
  verified:{new_real_IBM_job:true,real_Azure_cloud_simulator:true,actual_native_game_play:false,
   actual_hosted_model_conversation:false,save_reload_exact:true,real_model_training:false,nft_minted:false}};
 writeFileSync(join(directory,'creature.json'),JSON.stringify(report,null,2)+'\n');
 writeFileSync(join(directory,'nft_unminted.json'),JSON.stringify(metadata,null,2)+'\n');
 writeFileSync(join(directory,'creature.qbeast'),serializeQbeast(qbeast));
 writeFileSync(join(directory,'portable-session.json'),JSON.stringify(save,null,2)+'\n');
 writeFileSync(join(directory,'native-sprite-64x64-rgba.bin'),Buffer.from(pixel));
 results.push({name,qbeast_id:qbeast.profile.id,genome_seed:genome.seed,ibm_job_id:ibm.job_id,azure_job_id:azure.job_id,
  real_steps:48,save_reloaded:true,action_counts:report.behavior.action_counts});
 console.log('FIVE_NEW_REAL_MEASURED_QBEAST='+JSON.stringify(results.at(-1)));
}
check(new Set(results.map(r=>r.qbeast_id)).size===5,'Five seeds failed unique QBEAST identity requirement');
writeFileSync(join(base,'all-five-report.json'),JSON.stringify({schema:'beastbox-five-real-qbeasts-v1',source_manifest_sha256:manifest,creatures:results},null,2)+'\n');
