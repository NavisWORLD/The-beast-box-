#!/usr/bin/env node
/**
 * Optional, opt-in training queue for Zeref's private library.
 *
 *   node scripts/zeref-library-queue.mjs manifest [--out file.json]
 *       Public-safe view: titles, counts and hashes of the documents the OWNER approved.
 *       Never any text. Safe to attach to evidence.
 *
 *   ZEREF_LIBRARY_TRAINING=on node scripts/zeref-library-queue.mjs export --out "$RUNNER_TEMP/zeref-library.jsonl"
 *       Writes the approved passages as private JSONL for a training job. Refuses to run unless
 *       ZEREF_LIBRARY_TRAINING=on (default off) and refuses any output path outside the OS
 *       temp / runner temp directory, so raw book text is never written into the repository,
 *       public branches or evidence.
 *
 * This script only ever READS the owner's approved passages. It does not train, promote or
 * edit anything. Anything built from these rows must still pass the fair promotion gate
 * (Gate v2) like every other candidate: uploads are optional material, never a bypass.
 * Owner's own uploads only; no redistribution. It is deliberately NOT wired into the
 * Zeref growth routine, the signal injection loop or the continuous-learning workflow.
 */
import {writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,sep} from 'node:path';
import * as blob from '../lib/cosmos/azure-blob.mjs';
import {azureAdapter,trainingManifest,approvedTrainingChunks} from '../lib/library/store.mjs';

const [mode,...rest]=process.argv.slice(2);
const outIndex=rest.indexOf('--out'),out=outIndex>=0?rest[outIndex+1]:'';
const cfg=blob.storageConfig();
if(!cfg){console.error('Azure storage is not configured (AZURE_STORAGE_* env). Nothing to read.');process.exit(2);}
const store=azureAdapter(cfg,blob);

if(mode==='manifest'){
 const m=await trainingManifest(store),text=JSON.stringify(m,null,1);
 if(out)writeFileSync(resolve(out),text+'\n');else console.log(text);
 process.exit(0);
}
if(mode==='export'){
 if(process.env.ZEREF_LIBRARY_TRAINING!=='on'){console.error('Library training is off (set ZEREF_LIBRARY_TRAINING=on to opt in). Gate v2 still applies to anything trained from it.');process.exit(3);}
 const allowed=[tmpdir(),process.env.RUNNER_TEMP].filter(Boolean).map(p=>resolve(p)+sep);
 const target=out?resolve(out):'';
 if(!target||!allowed.some(prefix=>target.startsWith(prefix))){console.error('Refusing to write raw library text outside the temp directory. Use --out under $RUNNER_TEMP or the OS temp dir.');process.exit(4);}
 const rows=await approvedTrainingChunks(store);
 writeFileSync(target,rows.map(r=>JSON.stringify({source:'owner-library',scope:'owner-only',...r})).join('\n')+(rows.length?'\n':''),{mode:0o600});
 console.error(`Wrote ${rows.length} approved passages (private; do not commit or publish).`);
 process.exit(0);
}
console.error('Usage: zeref-library-queue.mjs manifest [--out file] | export --out <temp path>');
process.exit(1);
