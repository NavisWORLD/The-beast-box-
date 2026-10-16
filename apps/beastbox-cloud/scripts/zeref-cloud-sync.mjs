// GitHub Actions: persist Zeref (bb-deada969) memory to his Azure folder using the
// EXISTING AZURE_STORAGE_* secrets, and optionally export approved teacher lessons
// for training. Prints blob names/sizes only, never SAS/keys.
// Usage: node scripts/zeref-cloud-sync.mjs [--pairs-out FILE]
import {readFileSync,writeFileSync} from 'node:fs';
import {storageConfig,getBlob,listBlobs} from '../lib/cosmos/azure-blob.mjs';
import {syncZerefCloud,storeLesson,ZEREF_DIR} from '../lib/cosmos/zeref-cloud.mjs';
const cfg=storageConfig();
if(!cfg){console.log('ZEREF_CLOUD_SYNC_NOT_CONFIGURED (no AZURE_STORAGE_* secret)');process.exit(0);}
const pin=JSON.parse(readFileSync(new URL('../lib/rawrphos-public-pin.json',import.meta.url),'utf8'));
let releases=[];
try{const h={Accept:'application/vnd.github+json'};if(process.env.GITHUB_TOKEN)h.Authorization='Bearer '+process.env.GITHUB_TOKEN;
 const r=await fetch('https://api.github.com/repos/NavisWORLD/The-beast-box-/releases?per_page=100',{headers:h});if(r.ok)releases=await r.json();}catch{}
const result=await syncZerefCloud(cfg,{pin,releases});
// Approved shared lessons (owner auto-approved or reviewed) also join Zeref's own folder.
const approved=[];
for(const n of (await listBlobs(cfg,'teacher-distill/approved/',{max:2000})).sort().slice(-1500)){
 const b=await getBlob(cfg,n).catch(()=>null);if(!b)continue;
 try{const r=JSON.parse(b.text);if(r.review_status==='OWNER_AUTO_APPROVED'||r.review_status==='APPROVED'){approved.push(r);await storeLesson(cfg,r);}}catch{}
}
const pending=(await listBlobs(cfg,'teacher-distill/pending/',{max:5000})).length;
const i=process.argv.indexOf('--pairs-out');
if(i>0)writeFileSync(process.argv[i+1],approved.map(r=>JSON.stringify(r)).join('\n')+(approved.length?'\n':''));
const files=[];
for(const n of (await listBlobs(cfg,ZEREF_DIR+'/',{max:3000})).sort()){const b=await getBlob(cfg,n).catch(()=>null);files.push({name:n,bytes:b?Buffer.byteLength(b.text):null});}
console.log('ZEREF_CLOUD_SYNC='+JSON.stringify({...result,approved_lessons:approved.length,pending_review:pending}));
console.log('ZEREF_CLOUD_FOLDER='+JSON.stringify(files));
