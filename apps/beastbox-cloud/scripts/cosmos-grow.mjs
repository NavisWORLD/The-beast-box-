#!/usr/bin/env node
/**
 * Per-beast cosmos growth (runs inside .github/workflows/zeref-diary-loop.yml).
 *   node scripts/cosmos-grow.mjs plan <plan.json>                 round-robin batch of opted-in beasts
 *   node scripts/cosmos-grow.mjs apply <plan.json> <receipts.json> one tick per planned beast
 *   node scripts/cosmos-grow.mjs mirror-zeref <diary-dir>          copy Zeref's repo diary into beasts/<zeref>/
 * Storage comes from AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_SAS_URL (never printed).
 * Without it every command exits 0 with "storage not configured".
 */
import {existsSync,readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {applyBatch,mirrorZeref,planBatch} from '../lib/cosmos/cosmos-store.mjs';
import {ZEREF_PROFILE} from '../lib/zeref/zeref-mind.mjs';

const [cmd,a,b]=process.argv.slice(2);
const cfg=storageConfig();
const batch=Math.max(1,Math.min(10,Number(process.env.COSMOS_BATCH)||6));
if(!cfg){
 if(cmd==='plan'&&a)writeFileSync(a,JSON.stringify({configured:false,plans:[]})+'\n');
 console.log('COSMOS storage not configured (set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_SAS_URL); per-beast growth skipped.');
 process.exit(0);
}
try{
 if(cmd==='plan'){
  const plan=await planBatch(cfg,{batch,skip:[ZEREF_PROFILE.id]});
  writeFileSync(a,JSON.stringify({configured:true,...plan},null,1)+'\n');
  console.log('COSMOS_PLAN '+JSON.stringify({beasts:plan.plans.map(p=>p.beast_id),skipped:plan.skipped,batch}));
 }else if(cmd==='apply'){
  const plan=JSON.parse(readFileSync(a,'utf8'));
  if(!plan.configured||!plan.plans.length){console.log('COSMOS nothing to grow this tick');process.exit(0);}
  const receipts=existsSync(b)?(JSON.parse(readFileSync(b,'utf8')).receipts||[]):[];
  const done=await applyBatch(cfg,plan,receipts);
  for(const d of done)console.log('COSMOS_TICK '+JSON.stringify(d));
 }else if(cmd==='mirror-zeref'){
  const r=f=>readFileSync(join(a,f),'utf8');
  await mirrorZeref(cfg,{profile:{schema:'cosmos-beast-public/v1',id:ZEREF_PROFILE.id,name:ZEREF_PROFILE.name,provenance:{kind:'recorded-quantum-genome',backend:'ibm_marrakesh'}},
   stateText:r('state.json'),logText:r('diary.jsonl'),latestText:r('latest.json')});
  console.log('COSMOS mirrored Zeref into beasts/'+ZEREF_PROFILE.id+'/');
 }else{console.error('usage: cosmos-grow.mjs plan|apply|mirror-zeref');process.exit(2);}
}catch(e){
 // Sanitised: status + Azure error code only. The loop keeps Zeref's repo diary either way.
 console.log('COSMOS error: '+String(e.message||e).replace(/https?:\/\/\S+/g,'[url]').slice(0,200));
 process.exit(0);
}
