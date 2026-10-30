import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';
import {provenance,PROVENANCE_ROWS} from '../lib/universe/visual-life-provenance.mjs';
import {VL_PACK} from '../lib/universe/vislife-look.mjs';
import {VL_OUTPUT_LABELS} from '../lib/universe/visual-life-labels.mjs';
const snap={foam:{cover:.1,label:'SIMULATED'},caustics:{on:true,label:'SIMULATED'},haze:{cls:'mid',mul:1.4,label:'SIMULATED'},boom:{phase:'shell',label:'SEEDED'},palette:{type:'temperate',label:'SEEDED'},sound:{on:true,events:0}};
test('an empty snapshot lists every piece as not in view, nothing is claimed',()=>{const p=provenance({});assert.equal(p.rows.length,PROVENANCE_ROWS.length);assert.ok(p.rows.every(r=>r.on===false));assert.deepEqual(provenance(null).rows.map(r=>r.on),p.rows.map(r=>r.on));});
test('a row is on only when its own piece is in the snapshot (caustics need on, fog needs real moisture-lifted fog, sound needs the toggle)',()=>{
 const on=Object.fromEntries(provenance(snap).rows.map(r=>[r.key,r.on]));assert.deepEqual(on,{foam:true,caustics:true,haze:true,fog:true,boom:true,palette:true,sound:true});
 const off=Object.fromEntries(provenance({...snap,caustics:{on:false},haze:{mul:1.0},sound:{on:false}}).rows.map(r=>[r.key,r.on]));assert.deepEqual(off,{foam:true,caustics:false,haze:true,fog:false,boom:true,palette:true,sound:false});
});
test('labels are honest: simulated pieces SIMULATED, palette SEEDED, the boom carries the engine own label, RECORDED only on the genesis seed row',()=>{
 const p=provenance(snap),by=Object.fromEntries(p.rows.map(r=>[r.key,r.label]));
 assert.equal(by.foam,'SIMULATED');assert.equal(by.caustics,'SIMULATED');assert.equal(by.haze,'SIMULATED');assert.equal(by.fog,'SIMULATED');assert.equal(by.palette,'SEEDED');assert.equal(by.sound,'SIMULATED');assert.equal(by.boom,'SEEDED');
 assert.equal(provenance({boom:{phase:'flash'}}).rows.find(r=>r.key==='boom').label,VL_OUTPUT_LABELS.boom);
 assert.ok(p.rows.every(r=>r.label!=='RECORDED'&&r.label!=='MEASURED'));assert.equal(p.seed.label,'RECORDED');assert.match(p.seed.text,/Genesis seed/);
});
test('the pack row quotes the real pack: version 1.1 and the sha256 of the JSON it was generated from, labelled SEEDED',()=>{
 const raw=fs.readFileSync(new URL('../lib/universe/data/vislife.json',import.meta.url));const p=provenance({});
 assert.equal(p.pack.sha256,createHash('sha256').update(raw).digest('hex'));assert.equal(p.pack.sha256,VL_PACK.sha256);assert.equal(p.pack.version,1.1);assert.equal(p.pack.label,'SEEDED');
});
test('authored text: 44 characters or fewer, none of the never-say words, each row names an engine channel',()=>{
 const L=JSON.parse(fs.readFileSync(new URL('../lib/universe/data/visual_life_labels.json',import.meta.url),'utf8'));
 const bad=L.never_say.filter(x=>!/\(|RECORDED/.test(x)).concat(['live ','real-time','every object has a brain','AI']);
 for(const r of PROVENANCE_ROWS){assert.ok(r.text.length<=44,r.text);assert.ok(r.driver.length>8);const all=(r.text+' '+r.driver).toLowerCase();for(const w of bad)assert.ok(!(w==='AI'?/\bAI\b/.test(r.text+' '+r.driver):all.includes(w.toLowerCase())),w+' in '+r.key);}
 assert.ok(provenance({}).seed.text.length<=44);
});
test('pure and deterministic: same snapshot gives deep-equal output, the input is not mutated, no clock or random in the module',()=>{
 const s=JSON.stringify(snap);assert.deepEqual(provenance(snap),provenance(snap));assert.equal(JSON.stringify(snap),s);
 const src=fs.readFileSync(new URL('../lib/universe/visual-life-provenance.mjs',import.meta.url),'utf8').replace(/^\s*\/\/.*$/gm,'');assert.ok(!/Math\.random|Date\.|performance\.now|requestAnimationFrame|fetch\(/.test(src));
});
test('the view shows it from its own snapshot, only when opened, in all three chip panels',()=>{
 const v=fs.readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
 assert.equal((v.match(/\{soundBtn\}\{provBlock\}/g)||[]).length,3);assert.ok(v.includes('vlProvenance((window as any).__lwVisualLife)'));assert.ok(v.includes('data-lw-vl-provenance'));assert.ok(/if\(e\.currentTarget\.open\)setProv\(/.test(v));
});
