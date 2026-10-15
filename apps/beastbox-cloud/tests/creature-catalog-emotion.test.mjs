import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {rowsOf,filterRows,randomRow,uniqueRow} from '../public/spark/catalog-picker.mjs';
import {deriveEmotions,diaryEntry,EMOTIONS} from '../lib/companion/emotion.mjs';
const cat=JSON.parse(readFileSync(new URL('../public/spark/catalog-index.json',import.meta.url),'utf8'));
const table=JSON.parse(readFileSync(new URL('../public/spark/runs.json',import.meta.url),'utf8'));
const rows=rowsOf(cat);
test('catalogue covers every recorded IBM distribution exactly once, labelled simulated signal',()=>{
 assert.equal(rows.length,table.runs.length);assert.deepEqual(new Set(rows.map(r=>r.key)),new Set(table.runs.map(r=>r.k)));
 assert.equal(cat.signal.simulated,true);assert.equal(cat.signal.profile,'balanced');assert.match(cat.claim_boundary,/recorded historical IBM/);
});
test('rarest entry matches the 12 RAREST FINDS sheet #1 (Ferrotitan, kingston da6onfs6 p9)',()=>{
 const top=filterRows(rows,{sort:'rarest'})[0];assert.equal(top.finalName,'Ferrotitan');assert.match(top.key,/^ibm_kingston:da6onfs6.*#pub9$/);assert.equal(top.body,'golem');assert.equal(top.island,'Rust Meridian');
});
test('filters by island, body and search',()=>{
 const f=filterRows(rows,{island:'Umbral Deep',body:'serpent'});assert.ok(f.length>0);assert.ok(f.every(r=>r.island==='Umbral Deep'&&r.body==='serpent'));
 assert.ok(filterRows(rows,{q:'ferrotitan'}).some(r=>r.finalName==='Ferrotitan'));
});
test('random is uniform (rejection sampling) and unique avoids owned traits/seeds',()=>{
 let i=0;const seq=[4294967295,0,7];assert.equal(randomRow(rows.slice(0,3),()=>seq[i++]),rows[0]);// 4294967295 rejected for n=3
 const u=uniqueRow(rows,cat,[]);assert.ok(u.novelBits>0);
 const owned={...u.row,inputs:{quantum_run:u.row.key}};const u2=uniqueRow(rows,cat,[owned]);assert.notEqual(u2.row.key,u.row.key);
});
test('emotions are deterministic, bounded, explained, and change only from real recorded events',()=>{
 const beast={seed:'ab'.repeat(32),energy:80,genome:{temperament:'Playful',mouth:'w',inputs:{traits:{focus:30,calm:30,spark:30}},quantum:{entropy_norm:.4,marginals:[.7]}},behavior:{memory:[]}};
 const a=deriveEmotions(beast),b=deriveEmotions(structuredClone(beast));assert.deepEqual(a,b);
 for(const k of EMOTIONS)assert.ok(a[k]>=0&&a[k]<=100);assert.ok(a.topWhy.length>0);assert.ok(a.choice.motion);
 const src=readFileSync(new URL('../lib/companion/emotion.mjs',import.meta.url),'utf8');assert.doesNotMatch(src,/Date\.now|new Date|performance\.now|setInterval/);
 const pet=structuredClone(beast);pet.behavior.memory.push({tick:0,kind:'care:pet',place:'grove',reward:1});
 const c=deriveEmotions(pet);assert.ok(c.joy>a.joy);assert.ok(diaryEntry(a,c,'pet').changed.length>0);
 const sim=deriveEmotions(beast,{simGrowth:.5});assert.ok(sim.why.some(w=>/SIMULATED Rigetti/.test(w.reason)));
});
