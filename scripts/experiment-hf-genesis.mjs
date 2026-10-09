/** Read-only, reproducible assay of the EXISTING browser behavior/memory core.
 * No Python source is executed, inference endpoints called or quantum jobs run.
 */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {buildGenome,canonicalJson} from '../apps/beastbox-cloud/public/spark/genome.mjs';
import {buildQbeast} from '../apps/beastbox-cloud/public/spark/qbeast.mjs';
import {expandRun} from '../apps/beastbox-cloud/public/spark/runs.mjs';
import {renderBeast} from '../apps/beastbox-cloud/public/spark/draw.mjs';
import {createSession,adoptBeast,advanceCreature,exportSession,importSession,swapBrain} from '../apps/beastbox-cloud/lib/companion/session.mjs';
import {createBehavior,ACTIONS} from '../apps/beastbox-cloud/lib/companion/behavior.mjs';
import {observeText,recallAssociations,ASSOCIATION_LIMITS} from '../apps/beastbox-cloud/lib/companion/learn.mjs';
import {runGodCoreExperiment} from '../apps/beastbox-cloud/scripts/god-core-experiments.mjs';

const ROOT=fileURLToPath(new URL('../',import.meta.url));
const APP='apps/beastbox-cloud/',OUTPUT='experiments/hf-genesis-001';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const hash=x=>sha(canonicalJson(x));
const same=(a,b)=>canonicalJson(a)===canonicalJson(b);
const requireTrue=(ok,message)=>{if(!ok)throw Error(message);};
const TICKS=360,TRAINING=12;
const env=t=>({place:['grove','shore','nest','observatory'][Math.floor(t/90)%4],toy:t%19===0?.8:0,sound:t%31===0?.5:0,comfort:.6,attention:t%17===0?.4:0});
const codePaths=[
 'scripts/experiment-hf-genesis.mjs',APP+'scripts/god-core-experiments.mjs',
 ...['learn','behavior','session'].map(n=>APP+'lib/companion/'+n+'.mjs'),
 ...['genome','draw','qbeast','runs','qvm-growth'].map(n=>APP+'public/spark/'+n+'.mjs'),
];
const bounds=s=>s.beast.behavior.energy>=0&&s.beast.behavior.energy<=100&&s.beast.behavior.events.length<=32&&s.beast.behavior.memory.length<=24&&Object.keys(s.mind.associations.concepts).length<=ASSOCIATION_LIMITS.concepts&&Object.keys(s.mind.associations.links).length<=ASSOCIATION_LIMITS.links;
const summary=values=>{const mean=values.reduce((a,b)=>a+b,0)/values.length;return {n:values.length,mean,min:Math.min(...values),max:Math.max(...values),sample_sd:values.length>1?Math.sqrt(values.reduce((s,x)=>s+(x-mean)**2,0)/(values.length-1)):0};};

export function runHfGenesisExperiment(){
 const tableBytes=readFileSync(resolve(ROOT,APP+'public/spark/runs.json'));
 const runs=JSON.parse(tableBytes).runs.slice(0,12).map(expandRun),traits={focus:40,calm:40,spark:40};
 const traces=[],pairs=[],genesis=[];
 for(let index=0;index<runs.length;index++){
  const run=runs[index],gen=buildGenome(traits,run,null,10),again=buildGenome(traits,run,null,10);
  const pixels=renderBeast(gen,2,'open'),againPixels=renderBeast(again,2,'open');
  requireTrue(same(gen,again)&&Buffer.from(pixels).equals(Buffer.from(againPixels)),'Repeated genome/render mismatch');
  const s=createSession();adoptBeast(s,gen,gen.names[1]);s.beast.qbeast=buildQbeast(gen);s.beast.energy=80;s.beast.behavior=createBehavior(s.beast);
  for(let n=0;n<TRAINING;n++)observeText(s.mind,'grove explore',{seed:gen.seed});
  const ablated=structuredClone(s);ablated.mind.associations={schema:s.mind.associations.schema,observations:0,concepts:{},links:{}};
  const initial=structuredClone({memory:exportSession(s),ablated:exportSession(ablated)});
  requireTrue(same(s.mind.weights,ablated.mind.weights),'Ablation changed pre-existing matrix');
  const initialRecall=recallAssociations(s.mind,'grove'),counts={memory:Object.fromEntries(ACTIONS.map(a=>[a,0])),ablated:Object.fromEntries(ACTIONS.map(a=>[a,0]))};
  let replay,checkpoint,brainSwapEqual=false;
  for(let t=0;t<TICKS;t++){
   const environment=env(t),a=advanceCreature(s,environment),b=advanceCreature(ablated,environment);
   counts.memory[a.event.action]++;counts.ablated[b.event.action]++;
   traces.push({pair:index,branch:'memory',qbeast_id:s.beast.qbeast.profile.id,...a.event},{pair:index,branch:'ablated',qbeast_id:ablated.beast.qbeast.profile.id,...b.event});
   requireTrue(bounds(s)&&bounds(ablated),'Runtime or memory bounds violated');
   if(t===179){checkpoint=JSON.parse(JSON.stringify(exportSession(s)));replay=importSession(checkpoint);const before=structuredClone({mind:replay.mind,behavior:replay.beast.behavior,qbeast:replay.beast.qbeast});swapBrain(replay,'assay-offline-slot');brainSwapEqual=same(before,{mind:replay.mind,behavior:replay.beast.behavior,qbeast:replay.beast.qbeast});requireTrue(brainSwapEqual,'Brain swap altered memory/behavior/identity');}
   else if(t>=180){const r=advanceCreature(replay,environment);requireTrue(same(r.event,a.event),'Save/load changed next decision');}
  }
  requireTrue(same(s.beast.behavior,replay.beast.behavior)&&same(s.mind,replay.mind),'Persistence replay mismatch');
  requireTrue(same(s.beast.qbeast,initial.memory.beast.qbeast)&&same(s.beast.genome,initial.memory.beast.genome)&&s.beast.xp===initial.memory.beast.xp,'Automatic tick changed identity/genome/XP');
  genesis.push({index,run_key:run.key,backend:run.backend,job_id:run.job_id,source_class:'RECORDED IBM ARCHIVE LABEL; NOT PROVIDER RE-ATTESTED',count_digest:run.counts_sha256,genome_sha256:hash(gen),rgba_sha256:sha(Buffer.from(pixels)),qbeast_id:s.beast.qbeast.profile.id,seed:gen.seed,body:gen.body,island:gen.island,exact_regeneration:true});
  pairs.push({index,seed:gen.seed,initial,checkpoint_tick_180:checkpoint,initial_recall:initialRecall,actions:counts,explore_delta:counts.memory.explore-counts.ablated.explore,action_histograms_different:!same(counts.memory,counts.ablated),save_load_exact:true,brain_swap_exact:brainSwapEqual,final:{memory:exportSession(s),ablated:exportSession(ablated)}});
 }
 const existing=runGodCoreExperiment();
 const long=[];
 for(let index=0;index<3;index++){
  const s=importSession(pairs[index].initial.memory);
  for(let t=0;t<1200;t++){const result=advanceCreature(s,env(t));requireTrue(bounds(s),'Long-run bounds violated');traces.push({pair:index,branch:'long-memory',qbeast_id:s.beast.qbeast.profile.id,...result.event});}
  long.push({index,ticks:1200,final:exportSession(s)});
 }
 const report={
  schema:'beastbox-hf-genesis-assay-001',
  software:{integration_base_commit:'4bc54300559bb2afa122df948e3bc49e45c962f1',code_files:codePaths.map(path=>({path,sha256:sha(readFileSync(resolve(ROOT,path)))}))},
  sources:{hf_repository:'phera-ra/QC67_cosmo',hf_revision:'b414724c627300c41b099dcc6853766d08fd27a4',source_manifest_sha256:sha(readFileSync(resolve(ROOT,OUTPUT+'/source-manifest.json'))),source_audit_sha256:sha(readFileSync(resolve(ROOT,OUTPUT+'/source-audit.json'))),genesis_archive:{path:APP+'public/spark/runs.json',sha256:sha(tableBytes)}},
  protocol:{cohort:12,training_observations:TRAINING,training_phrase:'grove explore',ticks:TICKS,checkpoint_tick:180,loop_seconds_in_product:8,environment:'Four 90-tick rooms; fixed toy/sound/comfort/attention schedule, identical for both branches',ablation:'Clear only new association graph after training; keep genome, identity, old matrix, word sequence counts, state and preferences identical',runtime:'Existing beast.behavior core, classical deterministic decisions; no inference model or live quantum execution',render:'Stage II, eyes open, raw RGBA; excludes PNG metadata/encoding'},
  results:{reproducible_genomes:genesis.length,reproducible_renders:genesis.length,distinct_genomes:new Set(genesis.map(g=>g.genome_sha256)).size,distinct_renders:new Set(genesis.map(g=>g.rgba_sha256)).size,learned_action_link:pairs.filter(p=>p.initial_recall.some(h=>h.word==='explore')).length,changed_action_histograms:pairs.filter(p=>p.action_histograms_different).length,exploration_delta:summary(pairs.map(p=>p.explore_delta)),exact_restart_replays:pairs.filter(p=>p.save_load_exact).length,exact_brain_swaps:pairs.filter(p=>p.brain_swap_exact).length,long_bounded_runs:long.length,complete_event_rows:traces.length,source_baseline_rerun:existing.tests},
  interpretation:{demonstrated:['Identical retained recipe regenerates identical genome and pixels.','The learned graph is read into later action scores; replay includes actual causal inputs.','Graph ablation can change bounded action distributions under identical stimuli.','Same-QBEAST state and learned graph survive a JSON restart and an offline brain-slot swap.'],not_demonstrated:['Quantum advantage, biological life, consciousness, semantic understanding or unbounded open-ended learning.','Independent provider verification of archived IBM labels.','Reproduction of Hugging Face neural benchmarks, embedding sidecar, camera/microphone learning or HMAC authority.'],uncertainty:'This fixed 12-creature cohort is exploratory. Paired descriptive deltas and sample spread concern these runs, not a random population or statistical proof of physical source effects.'},
  genesis,pairs,long_runs:long,source_comparison:existing,
  limitations:['Original genesis measurements are never rewritten.','The new graph is bounded co-occurrence memory, not LLM training.','The score influence is deliberately capped at one per matching action.','The source-comparison simulator cohort is not matched to every IBM bit width/shot count; no causal quantum advantage inference is valid.','Decision traces retain full assay history here; the interactive product stores 32 decisions and 24 feedback events.','Physical iPhone/Safari, biological properties and external provider attestations remain untested in this assay.'],
 };
 return {report,traces};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const {report,traces}=runHfGenesisExperiment(),events=Buffer.from(traces.map(x=>JSON.stringify(x)).join('\n')+'\n'),compressed=gzipSync(events,{level:9});
 report.event_artifact={path:OUTPUT+'/events.jsonl.gz',rows:traces.length,uncompressed_bytes:events.length,uncompressed_sha256:sha(events),bytes:compressed.length,sha256:sha(compressed)};
 const snapshots=Buffer.from([...report.pairs.map(p=>({pair:p.index,initial:p.initial,checkpoint_tick_180:p.checkpoint_tick_180,final:p.final})),...report.long_runs.map(p=>({long_run:p.index,final:p.final}))].map(x=>JSON.stringify(x)).join('\n')+'\n'),states=gzipSync(snapshots,{level:9});
 report.state_artifact={path:OUTPUT+'/states.jsonl.gz',rows:report.pairs.length+report.long_runs.length,uncompressed_bytes:snapshots.length,uncompressed_sha256:sha(snapshots),bytes:states.length,sha256:sha(states)};
 report.pairs=report.pairs.map(({initial,checkpoint_tick_180,final,...rest})=>({...rest,snapshots:{initial_sha256:hash(initial),checkpoint_sha256:hash(checkpoint_tick_180),final_sha256:hash(final)},final:{memory:{tick:final.memory.beast.behavior.tick,energy:final.memory.beast.behavior.energy,curiosity:final.memory.beast.behavior.curiosity},ablated:{tick:final.ablated.beast.behavior.tick,energy:final.ablated.beast.behavior.energy,curiosity:final.ablated.beast.behavior.curiosity}}}));
 report.long_runs=report.long_runs.map(p=>({index:p.index,ticks:p.ticks,snapshot_sha256:hash(p.final),energy:p.final.beast.behavior.energy,curiosity:p.final.beast.behavior.curiosity,retained_decisions:p.final.beast.behavior.events.length}));
 const json=JSON.stringify(report,null,2)+'\n';
 if(process.argv.includes('--write')){mkdirSync(resolve(ROOT,OUTPUT),{recursive:true});writeFileSync(resolve(ROOT,OUTPUT+'/results.json'),json);writeFileSync(resolve(ROOT,OUTPUT+'/events.jsonl.gz'),compressed);writeFileSync(resolve(ROOT,OUTPUT+'/states.jsonl.gz'),states);}
 if(process.argv.includes('--check')){requireTrue(readFileSync(resolve(ROOT,OUTPUT+'/results.json'),'utf8')===json,'Result artifact differs from recomputation');requireTrue(readFileSync(resolve(ROOT,OUTPUT+'/events.jsonl.gz')).equals(compressed),'Trace artifact differs from recomputation');requireTrue(readFileSync(resolve(ROOT,OUTPUT+'/states.jsonl.gz')).equals(states),'State artifact differs from recomputation');}
 console.log(JSON.stringify({schema:report.schema,results:report.results,results_sha256:sha(json),trace:report.event_artifact}));
}
