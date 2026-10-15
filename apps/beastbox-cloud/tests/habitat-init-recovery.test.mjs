import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {loadQbeast as sparkLoad} from '../public/spark/qbeast.mjs';
import {loadQbeast as libLoad} from '../lib/companion/qpack/qbeast.mjs';
const base={format:'QBEAST1',version:1,profile:{seed:'x'},public_state:{mode:'unavailable'},progress:{},generation:0,lineage_head:'0',digest:'0'};
const cases={
 'empty events':{...base,events:[]},
 'missing events (old schema)':{...base,events:undefined},
 'events not an array':{...base,events:{}},
 'old schema without profile':{format:'QBEAST1',version:1,events:[{payload:{summary:'a'}}]},
 'birth record without payload':{...base,events:[{}],generation:1},
 'null record':null,
 'array record':[],
};
for(const [name,load] of [['spark',sparkLoad],['lib',libLoad]]){
 for(const [label,value] of Object.entries(cases)){
  test(`${name} loadQbeast rejects ${label} with a readable error, never a TypeError`,()=>{
   assert.throws(()=>load(JSON.stringify(value)),err=>!(err instanceof TypeError)&&/Beast file|QBEAST|Lineage/.test(err.message));
  });
 }
 test(`${name} loadQbeast rejects corrupt import text`,()=>{assert.throws(()=>load('{"format":"QBEAST1",'),SyntaxError);});
}
test('Spark main() keeps the habitat usable when the saved Beast fails validation',()=>{
 const src=readFileSync(new URL('../public/spark/app.mjs',import.meta.url),'utf8');
 const main=src.slice(src.indexOf('async function main(){'));
 assert.match(main,/if\(raw\)\{try\{const active=replaySpark/);
 assert.match(main,/catch\(err\)\{recovered=quarantineSaved\(raw,err\);\}/);
 assert.match(main,/if\(!raw\|\|recovered\)\{try\{await adopt/);
 assert.match(src,/function quarantineSaved\(raw,err\)[\s\S]*RECOVERY_KEY[\s\S]*removeItem\(QBEAST_KEY\)/);
});
