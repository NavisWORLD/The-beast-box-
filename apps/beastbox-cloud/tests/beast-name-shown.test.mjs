import test from 'node:test';import assert from 'node:assert/strict';
import {activeBeastName,SHOWN_KEY,COMPANION_KEY} from '../lib/companion/beast-name.mjs';
const mem=(o={})=>({getItem:k=>k in o?o[k]:null,setItem:(k,v)=>{o[k]=String(v);}});
test('the Cage card shown name is the fallback, after saved and seeded names',()=>{
 assert.deepEqual(activeBeastName(mem()),{name:null,source:null});
 assert.deepEqual(activeBeastName(mem({[SHOWN_KEY]:'Cresttall'})),{name:'Cresttall',source:'shown'});
 assert.equal(activeBeastName(mem({[SHOWN_KEY]:'Cresttall',[COMPANION_KEY]:JSON.stringify({name:'Lumen'})})).name,'Lumen');
});
