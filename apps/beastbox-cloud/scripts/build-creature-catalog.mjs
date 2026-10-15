// Builds public/spark/catalog-index.json: one entry per recorded IBM hardware count distribution
// in public/spark/runs.json, sparked with the default SIMULATED signal profile 'balanced' and no keeper id,
// the same recipe as the "MASS SPARK - 100 OF 5580" / "12 RAREST FINDS" sheets (spark-beasts/mass_spark.py).
// Rarity = sum of trait self-information, -log2 p(trait value), across the whole catalogue.
import {readFileSync,writeFileSync} from 'node:fs';
import {buildGenome,BODIES} from '../public/spark/genome.mjs';
import {simulateStable} from '../public/spark/signal.mjs';
export const TRAITS=['island','body','pose','ears','tail','wings','pattern','eye_style','mouth','temperament','glow'];
const table=JSON.parse(readFileSync(new URL('../public/spark/runs.json',import.meta.url),'utf8'));
const expand=r=>({key:r.k,backend:r.b,job_id:r.j,pub_index:r.p,num_bits:r.n,shots:r.s,counts_sha256:r.h,counts:Object.fromEntries(r.c.split(',').map(x=>{const[k,v]=x.split(':');return[k,Number(v)]}))});
const traits=simulateStable('balanced');
const rows=table.runs.map(r=>{const g=buildGenome(traits,expand(r),null,10);return {k:r.k,seed:g.seed,name:g.names[1],names:[g.names[1],g.names[2],g.names[3]],element:g.element,...Object.fromEntries(TRAITS.map(t=>[t,g[t]])),e:g.quantum.entropy_norm};});
const freq=Object.fromEntries(TRAITS.map(t=>[t,{}]));for(const r of rows)for(const t of TRAITS)freq[t][r[t]]=(freq[t][r[t]]||0)+1;
const N=rows.length;
for(const r of rows){r.bits=Math.round(TRAITS.reduce((s,t)=>s-Math.log2(freq[t][r[t]]/N),0)*100)/100;}
const values=Object.fromEntries(TRAITS.map(t=>[t,Object.keys(freq[t]).sort()]));
// Compact row: [key, stage1 name, stage3 name, bits, ...trait value indices in TRAITS order]
const packed=rows.map(r=>[r.k,r.names[0],r.names[2],r.bits,...TRAITS.map(t=>values[t].indexOf(r[t]))]);
const out={schema:'beastbox-creature-catalog-v1',source:'/spark/runs.json',signal:{profile:'balanced',simulated:true,focus:traits.focus,calm:traits.calm,spark:traits.spark},keeper:null,
 claim_boundary:'Each entry is one recorded historical IBM Quantum hardware count distribution used as a fixed seed, sparked with a SIMULATED default headband signal (balanced). Not a live quantum device.',
 rarity:'bits = sum over traits of -log2(share of all entries with that trait value)',
 count:N,traits:TRAITS,values,counts:Object.fromEntries(TRAITS.map(t=>[t,values[t].map(v=>freq[t][v])])),rows:packed};
writeFileSync(new URL('../public/spark/catalog-index.json',import.meta.url),JSON.stringify(out));
console.log(N,'rows; traits',JSON.stringify(traits));
