import assert from 'node:assert/strict';
import {test} from 'node:test';
import {generateCreature,FAMILIES,STAT_NAMES,validCreature,pickAmbientAction,stableCreatureId} from '../lib/creature-profile.ts';
test('v1 deterministic profiles replay with exact identity and stats',()=>{
 const a=generateCreature('  Nebula-1  '),b=generateCreature('Nebula-1');
 assert.deepEqual(a,b);assert.equal(a.id,stableCreatureId('Nebula-1'));
 assert.equal(a.provenance,'classical-seeded-game-generation');
 assert.equal(a.schema,'beast-cage-creature-v1');
});
test('all seven families are selectable without silently changing the stat stream',()=>{
 const base=generateCreature('same-seed');
 for(const family of FAMILIES){
  const x=generateCreature('same-seed',family);
  assert.equal(x.family,family);
  assert.deepEqual(x.game.stats,base.game.stats);
  assert.equal(x.id,base.id);
  assert.ok(validCreature(x));
 }
});
test('seed variety produces bounded and meaningful stat differentiation',()=>{
 const signatures=new Set();
 for(let i=0;i<100;i++){
  const x=generateCreature('seed-'+i);
  const values=STAT_NAMES.map(k=>x.game.stats[k]);
  assert.equal(values.reduce((a,b)=>a+b,0),500);
  assert.ok(values.every(x=>x>=20&&x<=80));
  signatures.add(values.join(','));
 }
 assert.ok(signatures.size>90);
});
test('invalid and privilege-shaped profiles cannot be imported as v1 characters',()=>{
 assert.throws(()=>generateCreature(''));
 assert.throws(()=>generateCreature('x'.repeat(65)));
 assert.throws(()=>generateCreature('x\u0000'));
 const x=generateCreature('import-security');
 assert.equal(validCreature({...x,game:{...x.game,stats:{...x.game.stats,hp:5000}}}),false);
 assert.equal(validCreature({...x,provenance:'authenticated-owner'}),false);
 assert.equal(validCreature({...x,id:'another-user'}),false);
});
test('behavior is purely reproducible classical visual action',()=>{
 const x=generateCreature('roam-seed');
 const first=Array.from({length:60},(_,i)=>pickAmbientAction(x,i));
 const again=Array.from({length:60},(_,i)=>pickAmbientAction(x,i));
 assert.deepEqual(first,again);
 assert.ok(new Set(first).size>2);
 assert.throws(()=>pickAmbientAction(x,-1));
});
