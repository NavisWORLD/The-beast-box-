import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {registeredCreatures,CREATURE_RECIPES} from '../public/spark/creature-assets.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {renderBeast} from '../public/spark/draw.mjs';
import {isZerefBeast,skinFromGenome,ZEREF_SKIN} from '../lib/zeref/rig-style.mjs';
const sourceRows=()=>CREATURE_RECIPES.flatMap(r=>JSON.parse(readFileSync(new URL('../public/spark/'+r.file,import.meta.url))).runs.map(expandRun));

test('renaming a saved creature Zeref cannot acquire the separate Moonwraith cat presentation',()=>{
 const [zeref,wraith,pig]=registeredCreatures(sourceRows());
 for(const item of [zeref,wraith,pig]){
  assert.equal(isZerefBeast({id:item.id,name:'Zeref'}),false,'canonical '+item.id+' remains its own visual creature');
  assert.notEqual(skinFromGenome(item.genome,{id:item.id,name:'Zeref'}),ZEREF_SKIN);
 }
 assert.equal(isZerefBeast({id:'bb-7f9c2a03',name:'Renamed site guide'}),true);
 assert.equal(isZerefBeast({name:'Zeref'}),false,'a display name alone never proves a registered identity');
});

test('original source-pinned creatures render distinct transparent frames without changing their genomes',()=>{
 const items=registeredCreatures(sourceRows()),hashes=[];
 for(const item of items){
  const before=JSON.stringify(item.genome);
  const pixels=renderBeast(item.genome,1,'open');
  assert.equal(pixels.length,64*64*4);
  assert.equal(pixels[3],0,'the atlas background stays transparent');
  assert.ok(pixels.some((v,i)=>i%4===3&&v===255),'sprite contains real opaque pixels');
  assert.equal(JSON.stringify(item.genome),before,'drawing cannot rewrite recorded traits or seed');
  hashes.push(createHash('sha256').update(pixels).digest('hex'));
 }
 assert.equal(new Set(hashes).size,items.length,'no registered beast reuses a repeated recolored sprite frame');
 const zeref=items.find(i=>i.id==='bb-deada969');
 assert.equal(zeref.body,'dragonling');
 assert.equal(hashes[items.indexOf(zeref)],'4176ec373c5f3bedc25dfb39aaf1ccd3eafe4701d0fac2e82de78a43852c5bd9','the approved recorded native Zeref art remains byte-identical');
});
