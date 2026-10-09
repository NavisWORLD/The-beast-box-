/** Final specimen in the existing engine, using completed measured receipts. */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {runRealIBMDragonExperiment} from './real-ibm-marrakesh-dragon-experiment.mjs';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {exportSession} from '../lib/companion/session.mjs';
const DIR=dirname(fileURLToPath(import.meta.url));
export function runFinalEtherealDragon(){
 const recordedStimulus=JSON.parse(readFileSync(join(DIR,'../public/spark/azure-rigetti-qvm-20261009.json'),'utf8'));
 const result=runRealIBMDragonExperiment({keeperPrefix:'Ethereal-dragon-',recordedStimulus});
 if(result.output.qbeast.id!=='bb-bea717c9'||result.output.genome.name!=='Duskscale'||result.output.provenance.candidate_index!==21)throw Error('Final measured dragon identity changed.');
 result.output.schema='beastbox-final-ethereal-dragon-experiment-v1';
 result.output.protocol.simulator+='; the completed 2026-10-09 512-shot Azure result also enters the existing behavior core once';
 result.output.limitations=result.output.limitations.map(line=>line.startsWith('Only the archived Rigetti')?'Completed simulator results were replayed. No new Azure job or Cosmos DB write took place in this assay.':line);
 return result;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const {output,portrait,qbeast,session}=runFinalEtherealDragon();
 const dir=resolve(DIR,'../experiment-evidence/final-ethereal-dragon-001');mkdirSync(dir,{recursive:true});
 writeFileSync(join(dir,'receipt.json'),JSON.stringify(output,null,2)+'\n');writeFileSync(join(dir,'beast.png'),portrait);
 writeFileSync(join(dir,'qbeast.json'),serializeQbeast(qbeast));writeFileSync(join(dir,'unsigned-session.json'),JSON.stringify(exportSession(session),null,2)+'\n');
 console.log('FINAL_ETHEREAL_DRAGON_RESULT '+JSON.stringify({name:output.genome.name,id:output.qbeast.id,keeper:output.provenance.keeper_label,actions:output.observed.action_counts,energy:output.observed.final_energy,curiosity:output.observed.final_curiosity,azure_action:output.recorded_azure_stimulus.actual_event.action,replay:output.acceptance.save_load_replay_exact,conversations:output.conversation.turns.length}));
}
