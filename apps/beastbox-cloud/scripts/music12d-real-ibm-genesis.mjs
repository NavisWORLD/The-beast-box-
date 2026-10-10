/** Third-party media never enters QPU API: approved COSMOS numeric packet -> IBM physical counts -> QBEAST. */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {runRealIBMDragonExperiment} from './real-ibm-marrakesh-dragon-experiment.mjs';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {exportSession,importSession} from '../lib/companion/session.mjs';
import {advanceCreature} from '../lib/companion/behavior.mjs';
const DIR=dirname(fileURLToPath(import.meta.url));
const root=resolve(DIR,'../../..');
const audio=JSON.parse(readFileSync(resolve(root,'experiment-input/cosmos-music-original-song-cst12-20261009.json'),'utf8'));
const receipt=JSON.parse(readFileSync(resolve(root,'_ibm_cst12_music_birth_20261009/measurement_receipt.json'),'utf8'));
const check=(ok,message)=>{if(!ok)throw Error(message)};
check(receipt.source_class==='RECORDED_IBM_HARDWARE'&&receipt.job_status==='DONE'&&receipt.shot_count===16384,'New actual IBM job is mandatory; no old-job fallback');
check(receipt.audio_pre_hardware?.original_song_sha256===audio.song_original_file_sha256&&receipt.audio_pre_hardware?.full_cosmos_12d_packet_sha256===audio.audio_packet_sha256,'Song must have influenced actual QPU rotations before execution');
check(!['db4nlt2mb58s7389er6g','db4n37g4qg6s73c2de00','db4m3bslf4us73c2ui9g'].includes(receipt.job_id),'Cannot reuse an earlier dragon source');
const {output,portrait,qbeast,session}=runRealIBMDragonExperiment({keeperPrefix:'Music12D-',hardwareReceipt:receipt});
check(output.provenance.genesis_job===receipt.job_id&&output.acceptance.save_load_replay_exact&&qbeast.profile.id===output.qbeast.id,'New QBEAST identity or exact save/load failed');
// The 48 real audio windows were reduced to 4 measured quarter-state trajectories.
// Reapply those musical drives across 48 classical simulation ticks, retaining
// exactly which origin caused what: physical QPU bits vs music-derived software.
const trace=[];
for(let i=0;i<48;i++){
 const v=audio.cst12_quarter_means[Math.floor(i/12)];
 const environment={place:i<12?'observatory':i<24?'grove':i<36?'shore':'observatory',sound:Math.max(0,Math.min(1,v[2])),toy:Math.max(0,Math.min(1,v[1])),attention:Math.max(0,Math.min(1,v[0])),comfort:Math.max(0,Math.min(1,v[3]))};
 const updated=advanceCreature(session,environment);
 check(updated.ok,'Audio-conditioned classical behavior rejected at window '+i);
 trace.push({window:i,seconds_start:Math.round(i*audio.duration_seconds/48*1000)/1000,mode:'CST12_CLASSICAL_AUDIO_DRIVE',action:updated.event.action,behavior_tick:updated.event.tick,position:updated.state.position,energy:updated.state.energy,observation:environment});
}
const saved=exportSession(session),readback=importSession(saved);
check(readback.beast.qbeast.profile.id===qbeast.profile.id&&readback.beast.behavior.tick===session.beast.behavior.tick,'Exact identity/session restoration failed after full-song 12D loop');
const dir=resolve(DIR,'../experiment-evidence/music-12d-ibm-20261009');mkdirSync(dir,{recursive:true});
const data={...output,schema:'beastbox-real-song-cst12-ibm-quantum-creature-genesis-v1',audio_pre_hardware:{original_file_sha256:audio.song_original_file_sha256,full_packet_sha256:audio.audio_packet_sha256,committed_song_12d_vector:audio.cst12_aggregated,original_duration_seconds:audio.duration_seconds,circuit_gate_conditioning_verified:true},physics_boundary:'Actual IBM 2-qubit results seeded classical QBEAST; 12D here is an operational music state; no nonlocal quantum audio transport or biological life claim',fresh_audio_behavior:{steps:trace.length,trace,rule:'software environment from quarter-averaged 12-channel music features'},acceptance:{...output.acceptance,audio_loop_save_replay_exact:true}};
writeFileSync(join(dir,'receipt.json'),JSON.stringify(data,null,2)+'\n');
writeFileSync(join(dir,'beast.png'),portrait);
writeFileSync(join(dir,'qbeast.json'),serializeQbeast(qbeast));
writeFileSync(join(dir,'unsigned-session.json'),JSON.stringify(saved,null,2)+'\n');
console.log('NEW_MUSIC12D_IBM_BIRTH '+JSON.stringify({name:output.genome.name,identity:qbeast.profile.id,job:receipt.job_id,shots:receipt.shot_count,audio_sha256:audio.song_original_file_sha256,circuit_audio:receipt.audio_pre_hardware,behavior_steps:output.observed?.action_counts,additional_audio_steps:trace.length,save_load_ok:true}));
