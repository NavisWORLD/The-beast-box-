/** Fresh completed IBM -> Azure measurements in the existing dragon engine. */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {runRealIBMDragonExperiment} from './real-ibm-marrakesh-dragon-experiment.mjs';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {exportSession} from '../lib/companion/session.mjs';
const DIR=dirname(fileURLToPath(import.meta.url));
export function runFinalLiveDragon(){
 const hardwareReceipt=JSON.parse(readFileSync(join(DIR,'../experiment-input/ibm-final-live-20261009-receipt.json'),'utf8'));
 const recordedStimulus=JSON.parse(readFileSync(join(DIR,'../public/spark/azure-final-ibm-qvm-20261009.json'),'utf8'));
 const result=runRealIBMDragonExperiment({keeperPrefix:'Ethereal-live-',hardwareReceipt,recordedStimulus});
 if(result.output.qbeast.id!=='bb-8546076e'||result.output.genome.name!=='Umbrascale'||result.output.provenance.candidate_index!==19)throw Error('Final fresh dragon identity changed.');
 result.output.schema='beastbox-final-live-ibm-azure-dragon-experiment-v1';
 result.output.protocol.genesis_selection='first deterministic dragonling candidate from completed physical IBM Fez Bell XX measurements; morphology selection is user-conditioned';
 result.output.protocol.simulator+='; the fresh receipt-derived 512-shot Azure result enters the existing behavior core once';
 result.output.limitations=result.output.limitations.map(line=>line.startsWith('Only the archived Rigetti')?'Both cloud provider jobs completed before their receipts entered this assay. No QPU remains connected to the classical behavior loop.':line);
 return result;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const {output,portrait,qbeast,session}=runFinalLiveDragon();
 const dir=resolve(DIR,'../experiment-evidence/final-live-umbrascale-001');mkdirSync(dir,{recursive:true});
 writeFileSync(join(dir,'receipt.json'),JSON.stringify(output,null,2)+'\n');writeFileSync(join(dir,'beast.png'),portrait);
 writeFileSync(join(dir,'qbeast.json'),serializeQbeast(qbeast));writeFileSync(join(dir,'unsigned-session.json'),JSON.stringify(exportSession(session),null,2)+'\n');
 console.log('FINAL_LIVE_DRAGON_RESULT '+JSON.stringify({name:output.genome.name,id:output.qbeast.id,keeper:output.provenance.keeper_label,actions:output.observed.action_counts,energy:output.observed.final_energy,curiosity:output.observed.final_curiosity,azure_action:output.recorded_azure_stimulus.actual_event.action,replay:output.acceptance.save_load_replay_exact,conversations:output.conversation.turns.length}));
}
