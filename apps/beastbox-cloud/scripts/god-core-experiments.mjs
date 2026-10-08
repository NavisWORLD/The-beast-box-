/** GOD CORE 001: deterministic, exploratory software experiment.
 * Source categories are intentionally different. No live QPU jobs are run.
 * Run from apps/beastbox-cloud: node scripts/god-core-experiments.mjs --write
 */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {buildGenome,canonicalJson} from '../public/spark/genome.mjs';
import {expandQvmReceipt,QVM_SOURCE_CLASS} from '../public/spark/qvm-growth.mjs';
import {createBehavior,stepBehavior,feedbackBehavior,ACTIONS} from '../lib/companion/behavior.mjs';

const base=dirname(fileURLToPath(import.meta.url));
const sha=s=>createHash('sha256').update(s).digest('hex');
const fixtures=JSON.parse(readFileSync(join(base,'../public/spark/runs.json'),'utf8')).runs;
const qvm=expandQvmReceipt(JSON.parse(readFileSync(join(base,'../public/spark/rigetti-qvm-sim.json'),'utf8')));
const traits={focus:40,calm:40,spark:40}, TICKS=240, LONG_TICKS=1200;
const fromArchive=row=>({key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts:Object.fromEntries(row.c.split(',').map(piece=>{const[k,v]=piece.split(':');return[k,Number(v)]})),counts_sha256:row.h,source_class:'RECORDED IBM COUNTS'});
function classicalControl(run,index){
 const n=run.num_bits,counts={};
 for(let i=0;i<run.shots;i++){
  let bits='',block=0;
  while(bits.length<n){const digest=sha('god-core-001-classical-v1\0'+run.key+'\0'+index+'\0'+i+'\0'+block++);bits+=[...digest].map(h=>Number.parseInt(h,16).toString(2).padStart(4,'0')).join('');}
  const key=bits.slice(0,n);counts[key]=(counts[key]||0)+1;
 }
 return {key:'classical:g001:'+index,backend:'classical.sha256.deterministic',job_id:'local-control-'+index,pub_index:0,num_bits:n,shots:run.shots,counts,counts_sha256:sha(canonicalJson(counts)),source_class:'CLASSICAL CONTROL'};
}
const environment=t=>({place:['grove','shore','nest','observatory'][Math.floor(t/60)%4],toy:t%10===0?1:0,attention:t%13===0?1:0,comfort:t%3===0?1:0.4,sound:t%17===0?0.9:0});
function simulate(gen,ticks=TICKS,withFeedback=false){
 const beast={seed:gen.seed,genome:gen,energy:80};
 let state=createBehavior(beast),counts=Object.fromEntries(ACTIONS.map(a=>[a,0])),energyLow=100;
 const checkpoints=[],events=[];
 for(let t=0;t<ticks;t++){
  if(withFeedback && t>=60 && t%15===0){state=feedbackBehavior(state,beast,{place:'grove',reward:1,kind:'controlled-reward'});}
  const result=stepBehavior(state,beast,environment(t));
  state=result.state;counts[result.event.action]++;energyLow=Math.min(energyLow,state.energy);
  if(t<16||t%60===0)events.push(result.event); // bounded published trace samples
  if(t===119)checkpoints.push(JSON.parse(JSON.stringify(state)));
 }
 return {state,counts,energyLow,checkpoints,traceSamples:events};
}
function equal(a,b){return canonicalJson(a)===canonicalJson(b);}
export function runGodCoreExperiment(){
 const recorded=fixtures.slice(0,12).map(fromArchive);
 if(recorded.length!==12||recorded.some(r=>!/ibm_/i.test(r.backend)))throw Error('Recorded cohort is missing its pinned IBM count rows.');
 const classical=recorded.map(classicalControl);
 const simulator=qvm.slice(0,12).map(r=>({...r,source_class:'SIMULATOR / QVM'}));
 const groups=[['RECORDED IBM COUNTS',recorded],['CLASSICAL CONTROL',classical],['SIMULATOR / QVM',simulator]];
 const rows=[],genesis=[],replay=[],longRuns=[];
 for(const [className,runs] of groups){
  for(let i=0;i<runs.length;i++){
   const run=runs[i],gen=buildGenome(traits,run,null,10),again=buildGenome(traits,run,null,10);
   if(!equal(gen,again))throw Error('A: repeated identical genesis mismatch');
   const beast=simulate(gen);
   if(beast.state.events.length>32||beast.state.memory.length>24||beast.state.energy<0||beast.state.energy>100)throw Error('F: runtime bounds violated');
   rows.push({className,index:i,run_key:run.key,backend:run.backend,job_id:run.job_id,shots:run.shots,num_bits:run.num_bits,source_digest:run.counts_sha256,genome_sha256:sha(canonicalJson(gen)),genesis_seed:gen.seed,body:gen.body,island:gen.island,temperament:gen.temperament,actions:beast.counts,low_energy:beast.energyLow,final_energy:beast.state.energy,final_curiosity:beast.state.curiosity,preferences:beast.state.preferences,trace_samples:beast.traceSamples});
   genesis.push({className,index:i,exact:true,seed:gen.seed});
  }
 }
 const measured=rows.filter(r=>r.className==='RECORDED IBM COUNTS'),control=rows.filter(r=>r.className==='CLASSICAL CONTROL');
 const diff=measured.map((r,i)=>({pair:i,exploreDelta:(r.actions.explore||0)-(control[i].actions.explore||0),energyDelta:r.final_energy-control[i].final_energy}));
 for(let i=0;i<6;i++){
  const gen=buildGenome(traits,recorded[i],null,10),on=simulate(gen,TICKS,true),off=simulate(gen,TICKS,false);
  replay.push({seed:gen.seed,learned:structuredClone(on.state.preferences),untrained:structuredClone(off.state.preferences),actionsDifferent:!equal(on.counts,off.counts),sameGenesis:true});
  if(on.state.preferences.grove<=off.state.preferences.grove)throw Error('D: controlled feedback did not increase grove preference');
  // The last checkpoint is a snapshot at tick 120. Resume the identical test stimuli.
  let recovered=JSON.parse(JSON.stringify(off.checkpoints[0])),beast={seed:gen.seed,genome:gen,energy:80};
  for(let t=120;t<TICKS;t++)recovered=stepBehavior(recovered,beast,environment(t)).state;
  if(!equal(recovered,off.state))throw Error('E: restart produced a different decision trace');
 }
 for(let i=0;i<3;i++){
  const gen=buildGenome(traits,recorded[i],null,10),live=simulate(gen,LONG_TICKS,true);
  longRuns.push({seed:gen.seed,ticks:LONG_TICKS,energy:live.state.energy,event_log:live.state.events.length,memory:live.state.memory.length});
 }
 return {schema:'beastbox-god-core-experiment-001',source_classes:['RECORDED IBM COUNTS','CLASSICAL CONTROL','SIMULATOR / QVM'],qvm_source_class:QVM_SOURCE_CLASS,protocol:{genome:'existing lost-cosmos-beast-genome-v2',behavior:'beastbox-behavior-v1',run_row_rule:'first 12 published IBM archive rows, first 12 pinned QVM batches, SHA256 classical bitstrings matched to IBM bit width and shot counts',cohort_per_class:12,traits,ticks:TICKS,long_ticks:LONG_TICKS,environment:'four 60-tick habitats with deterministic toy/attention/comfort/noise',feedback:'positive grove outcome every 15 ticks after tick 60; ablation omits outcome',checkpoint:'JSON roundtrip at tick 120 then identical stimulus replay',runtime_class:'classical deterministic software'},tests:{A_repeated_genesis:genesis.length,B_paired_source_comparison:diff,C_behavioral_diversity:new Set(measured.map(r=>JSON.stringify(r.actions))).size,D_controlled_preference_change:replay.length,E_restart_replay:replay.length,F_long_bounded_runs:longRuns.length},comparisons:{pairwise_differences:diff,interpretation:'Descriptive outcomes of different seeded cohorts; no quantum advantage, causal source isolation, statistical significance or external provider re-attestation established.'},memoryAblation:replay,longRuns,sourceRows:rows,limitations:['IBM archive labels come from existing published records; not newly verified at provider.','Rigetti data are pinned Azure QVM SIMULATOR results, never QPU.','Deterministic SHA-256 controls are reproducible classical pseudorandom input, not a hardware RNG.','The 12-per-source cohort and hand-designed environment are exploratory, not a blinded physical experiment.','Only bounded operational artificial-life-like properties are tested.','No physical iPhone battery, biological life or consciousness claims.']};
}
if(process.argv[1] && fileURLToPath(import.meta.url)===process.argv[1]){
 const report=runGodCoreExperiment(),json=JSON.stringify(report,null,2)+'\n';
 if(process.argv.includes('--write')){const dir=join(base,'../experiment-evidence/god-core-001');mkdirSync(dir,{recursive:true});writeFileSync(join(dir,'results.json'),json);}
 console.log(JSON.stringify({schema:report.schema,tests:report.tests,interpretation:report.comparisons.interpretation,rows:report.sourceRows.length,sha256:sha(json)}));
}
