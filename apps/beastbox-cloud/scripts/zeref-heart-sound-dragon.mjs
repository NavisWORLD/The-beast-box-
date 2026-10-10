/** Fresh measured QBEAST with keeper name Zeref; observed sound-response controls. */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import {runRealIBMDragonExperiment} from './real-ibm-marrakesh-dragon-experiment.mjs';
import {exportSession,importSession,advanceCreature,beastIdentity} from '../lib/companion/session.mjs';
import {nameBeast} from '../lib/companion/adventure.mjs';
import {createBehavior,ACTIONS} from '../lib/companion/behavior.mjs';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {canonicalJson} from '../public/spark/genome.mjs';
import {renderBeast} from '../public/spark/draw.mjs';
import {habitatPose} from '../public/spark/habitat.mjs';
const ROOT=resolve('..','..');
// Called from repository root by Actions, and from the app root by local replays.
const input=process.cwd().endsWith('beastbox-cloud')?join(ROOT,'_zeref_live_20261010'):resolve('_zeref_live_20261010');
const out=process.cwd().endsWith('beastbox-cloud')?resolve('experiment-evidence/zeref-heart-sound-20261010'):resolve('apps/beastbox-cloud/experiment-evidence/zeref-heart-sound-20261010');
const read=file=>JSON.parse(readFileSync(join(input,file),'utf8')),sha=value=>createHash('sha256').update(canonicalJson(value)).digest('hex');
const physics=read('physics-receipt.json'),azure=read('azure-result.json'),audio=read('audio-features.json'),heartbeat=read('heartbeat.json');
if(azure.source.ibm_job_id!==physics.job_id||azure.counts_sha256!==sha(azure.counts)||azure.shots!==512)throw Error('Actual measured Azure lineage required');
const {output,portrait,qbeast,session}=runRealIBMDragonExperiment({keeperPrefix:'Zeref-heart-',hardwareReceipt:physics});
const id=beastIdentity(session.beast);nameBeast(session,'Zeref');
session.beast.behavior=createBehavior(session.beast);
const count=azure.counts,p00=(count['00']||0)/512,p11=(count['11']||0)/512;
const actualAzureEvent=advanceCreature(session,{place:'observatory',sound:.5,toy:p11,attention:p00+p11,comfort:p00});
const start=JSON.parse(JSON.stringify(exportSession(session))),traces={};
for(const arm of ['sound','muted','shuffled']){
 const next=importSession(structuredClone(start)),events=[],actions=Object.fromEntries(ACTIONS.map(x=>[x,0]));
 for(let tick=0;tick<96;tick++){
  const index=arm==='shuffled'?(tick*7+3)%8:tick%8;
  const level=arm==='muted'?0:Math.max(0,Math.min(1,audio.features[8+index]*8));
  const event=advanceCreature(next,{place:tick<48?'grove':'observatory',sound:level,toy:0,attention:level>.4?.7:.2,comfort:.65});
  if(!event.ok||beastIdentity(next.beast)!==id)throw Error('Behavior or identity changed unexpectedly');
  events.push(event.event);actions[event.event.action]++;
 }
 const reloaded=importSession(JSON.parse(JSON.stringify(exportSession(next))));
 if(canonicalJson(exportSession(next))!==canonicalJson(exportSession(reloaded)))throw Error('Exact behavior save/reload failed');
 traces[arm]={actions,events,final_state:next.beast.behavior,trace_sha256:sha(events),save_reload_exact:true};
 if(arm==='sound')Object.assign(session,reloaded);
}
const poses=Array.from({length:48},(_,i)=>({t:i/12,pose:habitatPose(session.beast.genome,i/12,'idle',false)}));
const spriteFrames=['open','closed','sparkle'].map(eyes=>({eyes,width:64,height:64,rgba_base64:Buffer.from(renderBeast(session.beast.genome,1,eyes)).toString('base64')}));
const result={schema:'beastbox-zeref-fresh-heart-sound-dragon-v1',keeper_name:'Zeref',genome_name:output.genome.name,
 qbeast_id:id,seed:session.beast.seed,genome_sha256:sha(session.beast.genome),physics,azure,heartbeat_sha256:heartbeat.heartbeat_sha256,
 audio,actual_azure_environment_event:actualAzureEvent.event,behavior_controls:traces,
 base_assay:output,training:read('training-sandbox-report.json'),animation:{kind:'existing seeded habitat pose, not gameplay recording',fps:12,poses},
 source_execution:'real IBM hardware and actual Azure cloud simulator; later behavior is classical software',
 native_gameplay_recorded:false,hosted_production_chat_recorded:false,biological_life_proven:false};
mkdirSync(out,{recursive:true});
for(const [file,value] of Object.entries({'receipt.json':result,'qbeast.json':qbeast,'unsigned-session.json':exportSession(session),'sprite-frames.json':spriteFrames}))writeFileSync(join(out,file),JSON.stringify(value,null,2)+'\n');
writeFileSync(join(out,'beast.png'),portrait);writeFileSync(join(out,'Zeref.qbeast'),serializeQbeast(qbeast));
console.log('ZEREF_FRESH_DRAGON_RESULT='+JSON.stringify({name:'Zeref',genome_name:output.genome.name,id,ibm_job:physics.job_id,azure_job:azure.job_id,seed:session.beast.seed,actions:traces.sound.actions,muted:traces.muted.actions,save_reload:true}));
