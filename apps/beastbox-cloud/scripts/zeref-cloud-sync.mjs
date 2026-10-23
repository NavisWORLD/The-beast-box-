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
const OK=new Set(['OWNER_AUTO_APPROVED','APPROVED','SHARED_TEACHER_AUTO']);
const approved=[];
for(const n of (await listBlobs(cfg,'teacher-distill/approved/',{max:2000})).sort().slice(-1500)){
 const b=await getBlob(cfg,n).catch(()=>null);if(!b)continue;
 try{const r=JSON.parse(b.text);if(OK.has(r.review_status)){approved.push(r);await storeLesson(cfg,r);}}catch{}
}
// Fix 002: Zeref's own lessons/ folder is read too (create-only lessons; deduped by id).
const seenIds=new Set(approved.map(r=>r.id));
for(const n of (await listBlobs(cfg,ZEREF_DIR+'/lessons/',{max:3000})).sort().slice(-1500)){
 const b=await getBlob(cfg,n).catch(()=>null);if(!b)continue;
 try{const r=JSON.parse(b.text);if(OK.has(r.review_status)&&!seenIds.has(r.id)){seenIds.add(r.id);approved.push(r);}}catch{}
}
const pending=(await listBlobs(cfg,'teacher-distill/pending/',{max:5000})).length;
const i=process.argv.indexOf('--pairs-out');
if(i>0)writeFileSync(process.argv[i+1],approved.map(r=>JSON.stringify(r)).join('\n')+(approved.length?'\n':''));
// 2026-10-22: export Zeref's own experience records (bb-deada969 ONLY; bb-7f9c2a03 never read here)
// for the capped experience chat-mix source: diary ticks (Cage pocket walks, moods, places, Rigetti SIMULATED
// growth) and approved training-cycle records (native game). Numbers/labels only, no private transcripts.
const j=process.argv.indexOf('--experiences-out');
if(j>0){const ex=[];
 const d=await getBlob(cfg,ZEREF_DIR+'/diary.jsonl').catch(()=>null);
 if(d)for(const l of d.text.split('\n').slice(-400)){try{const e=JSON.parse(l);if(e.beast_id==='bb-deada969')ex.push({kind:'diary',tick:e.tick,at:e.at,mood:e.mood,place:e.place,
  places_visited:e.places_visited,new_combo_count:e.new_combo_count,combos:(e.discovered_combos||[]).map(c=>c.name).slice(0,3),stage_name:e.stage_name,grew:e.grew,
  growth:e.growth_source?.kind,simulated:!!e.growth_source?.simulated,universe_growth:e.universe_growth??null,new_cells:e.learning?.new_cells,favorite_spot:e.learning?.favorite_spot,thought:e.thought?.by==='deterministic-template'?e.thought.text:null});}catch{}}
 for(const n of (await listBlobs(cfg,ZEREF_DIR+'/experiences/',{max:2000})).sort()){const b=await getBlob(cfg,n).catch(()=>null);if(!b)continue;try{const r=JSON.parse(b.text);ex.push({kind:'training-cycle',tag:r.tag,at:r.published_at});}catch{}}
 writeFileSync(process.argv[j+1],ex.map(r=>JSON.stringify(r)).join('\n')+(ex.length?'\n':''));
 console.log('ZEREF_EXPERIENCE_EXPORT='+JSON.stringify({diary_ticks:ex.filter(r=>r.kind==='diary').length,training_cycles:ex.filter(r=>r.kind==='training-cycle').length}));}
const files=[];
for(const n of (await listBlobs(cfg,ZEREF_DIR+'/',{max:3000})).sort()){const b=await getBlob(cfg,n).catch(()=>null);files.push({name:n,bytes:b?Buffer.byteLength(b.text):null});}
console.log('ZEREF_CLOUD_SYNC='+JSON.stringify({...result,approved_lessons:approved.length,pending_review:pending}));
console.log('ZEREF_CLOUD_FOLDER='+JSON.stringify(files));
