import test from 'node:test';
import assert from 'node:assert/strict';
import {ZEREF_TRUE3D_IDS,RENDERER_KINDS,resolveCreature3D} from '../lib/companion/creature-3d-router.mjs';

test('renderer kinds are closed and Zeref identities are pinned',()=>{
 assert.deepEqual([...RENDERER_KINDS],['zeref-true3d','procedural-cosmic','sprite-only']);
 assert.deepEqual([...ZEREF_TRUE3D_IDS],['bb-7f9c2a03','bb-deada969']);
});

test('Moonwraith persona and saved Zeref share the mesh family but keep distinct IDs',()=>{
 const persona=resolveCreature3D({id:'bb-7f9c2a03'});
 const saved=resolveCreature3D({id:'bb-deada969'});
 assert.equal(persona.kind,'zeref-true3d');
 assert.equal(saved.kind,'zeref-true3d');
 assert.equal(persona.qbeastId,'bb-7f9c2a03');
 assert.equal(saved.qbeastId,'bb-deada969');
 assert.notEqual(persona.qbeastId,saved.qbeastId);
});

test('other saved QBEASTs keep their recorded-seed sprite path; workshop falls back to cosmic rig',()=>{
 const other=resolveCreature3D({id:'bb-aaaaaaaa',genome:{seed:'ab'.repeat(32)}});
 assert.equal(other.kind,'sprite-only');
 assert.equal(other.qbeastId,'bb-aaaaaaaa');
 const workshop=resolveCreature3D({profile:{appearance:{hueShift:0}}});
 assert.equal(workshop.kind,'procedural-cosmic');
 const empty=resolveCreature3D({});
 assert.equal(empty.kind,'procedural-cosmic');
 assert.equal(empty.qbeastId,null);
});
