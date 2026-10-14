/** Server-side integrity replay against existing published measurement archives. */
import {readFileSync,readdirSync} from 'node:fs';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {expandRun,validateRun} from '../../public/spark/runs.mjs';
import {replaySpark} from '../../public/spark/identity.mjs';
import {publicProfileFromBeast} from '../../public/spark/cosmos-profile.mjs';
let archive=null;
function sources(){
 if(archive)return archive;
 const dir=join(process.cwd(),'public/spark'),byKey=new Map(),metadata=new Map();
 const names=readdirSync(dir).filter(name=>/^(?:runs|ibm-[a-z0-9-]+|user-seeds-[0-9-]+|azure-[a-z0-9-]+)\.json$/.test(name));
 for(const name of names){const bytes=readFileSync(join(dir,name));if(bytes.length>8000000)continue;let raw;try{raw=JSON.parse(bytes);}catch{continue;}
  for(const row of raw.runs||[]){const run=expandRun(row);validateRun(run);if(byKey.has(run.key)&&byKey.get(run.key).counts_sha256!==run.counts_sha256)throw Error('Conflicting published run archive');byKey.set(run.key,run);metadata.set(run.key,{source:'public:spark/'+name,archive_sha256:createHash('sha256').update(bytes).digest('hex'),recordedTimestamp:raw.generated_at||raw.recorded_at||null});}
 }
 return archive={byKey,metadata};
}
export function verifyPrivateGenesis(qbeastText,name){
 if(typeof qbeastText!=='string'||Buffer.byteLength(qbeastText)>200000)throw Error('A bounded canonical Spark QBEAST is required.');
 const {byKey,metadata}=sources(),{snapshot,gen,run}=replaySpark(qbeastText,byKey);
 const profile=publicProfileFromBeast({qbeast:snapshot,genome:gen,displayName:name});if(!profile)throw Error('Canonical public profile unavailable.');
 return {profile,qbeastText,quantumGenesis:{schema:'private-genesis-reference/v1',kind:run.qvm?'RECORDED_SIMULATOR_REPLAY':'RECORDED_MEASUREMENT_REPLAY',backend:run.backend,job_id:run.job_id,shots:run.shots,raw_counts:run.counts,counts_sha256:run.counts_sha256,...metadata.get(run.key),circuit_spec_or_hash:null,circuitReceiptComplete:false,freshHardwareJob:false,qbeast_id:snapshot.profile.id,seed_derivation:'existing Spark Beasts v1; public recipe nonce for new personal creations',verification:'canonical QBEAST replay matched the existing published archive; no new provider measurement asserted'}};
}
