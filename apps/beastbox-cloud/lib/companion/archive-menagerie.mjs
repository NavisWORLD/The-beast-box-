/** Read-only public count-derived specimens. These are generated previews, never saved player Beasts. */
import {buildGenome} from '../../public/spark/genome.mjs';
import {buildQbeast} from '../../public/spark/qbeast.mjs';

export const ARCHIVE_RECIPES=Object.freeze([
 Object.freeze({focus:20,calm:70,spark:40}),
 Object.freeze({focus:80,calm:20,spark:60}),
 Object.freeze({focus:40,calm:30,spark:90}),
]);

/** This is a source classification, not an attestation of live QPU execution. */
export function archiveProvenance(backend){
 const name=String(backend||'').toLowerCase();
 if(/(?:qvm|simulator|simulation)/.test(name))return 'SIMULATOR';
 if(/^ibm_[a-z0-9_-]+$/.test(name))return 'RECORDED IBM COUNTS';
 return 'RECORDED SEED DATA';
}
export function makeArchiveMenagerie(runs,limit=12){
 const cap=Number.isInteger(limit)?Math.max(0,Math.min(24,limit)):12;
 if(!Array.isArray(runs)||cap===0)return [];
 const pool=[],seenIds=new Set(),seenBody=new Set();
 // Bound local CPU work. The gallery never queries the quantum service.
 for(const [i,run] of runs.slice(0,144).entries()){
  if(!run||typeof run.key!=='string'||!run.counts||!run.counts_sha256)continue;
  try{
   const recipe=ARCHIVE_RECIPES[i%ARCHIVE_RECIPES.length];
   const genome=buildGenome(recipe,run,null,10);
   const snapshot=buildQbeast(genome);
   const id=snapshot.profile.id;
   if(seenIds.has(id))continue;
   seenIds.add(id);
   const item={
    id,name:genome.names[1],family:snapshot.profile.family,
    body:genome.body,island:genome.island,
    genome,runKey:run.key,jobId:run.job_id||'',
    countsHash:run.counts_sha256,backend:run.backend,
    origin:archiveProvenance(run.backend),
    sourceClass:'DERIVED PREVIEW',stage:1
   };
   if(!seenBody.has(genome.body)){pool.unshift(item);seenBody.add(genome.body);}
   else pool.push(item);
  }catch{/* Corrupt archive rows never become fabricated specimens. */}
  if(pool.length>=96)break;
 }
 // Prefer body diversity without inventing rankings or rarity claims.
 const chosen=[],used=new Set();
 for(const item of pool){
  if(chosen.length>=cap)break;
  if(used.has(item.body))continue;
  chosen.push(item);used.add(item.body);
 }
 for(const item of pool){
  if(chosen.length>=cap)break;
  if(!chosen.some(selected=>selected.id===item.id))chosen.push(item);
 }
 return chosen;
}
