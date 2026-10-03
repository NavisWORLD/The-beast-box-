const {test}=require('node:test');
const assert=require('node:assert/strict');
const {generateCreature}=require('../dist/canonical/creature-profile.js');
const {createSnapshot,verifySnapshot,serializeSnapshot,parseSnapshot,hashObject}=require('../dist/verifier.js');
const {BeastBridge,approveProposal}=require('../dist/bridge.js');
const {exportGba}=require('../dist/gba_export.js');
const {signSnapshot,createSigningKey}=require('../dist/signature.js');
const profile=()=>generateCreature('quantum-beast-first-contact','nebula');
test('canonical seeded profile survives deterministic portable roundtrip',async()=>{
 const a=await createSnapshot(profile()),b=await createSnapshot(profile());
 assert.deepEqual(a,b);assert.equal(await serializeSnapshot(a),await serializeSnapshot(b));
 assert.deepEqual(await parseSnapshot(await serializeSnapshot(a)),a);
 const v=await verifySnapshot(a);assert.equal(v.integrity,true);assert.equal(v.signature,'absent');
});
test('rehashed forged stats, extra private fields and unsupported versions fail closed',async()=>{
 const a=await createSnapshot(profile());
 for(const mutate of [x=>x.profile.game.stats.hp++,x=>x.profile.owner_memory='private',x=>x.version=2,x=>x.progress.evolution_stage=1,x=>x.public_state.values[0]=NaN]){
  const b=structuredClone(a);mutate(b);await assert.rejects(()=>verifySnapshot(b));
 }
 const b=structuredClone(a);b.profile.game.stats.hp++;b.digest=await hashObject({...b,digest:undefined});
 await assert.rejects(()=>verifySnapshot(b));
});
test('ZIPs, duplicate JSON keys, huge files, prototype keys and executable fields are rejected',async()=>{
 for(const text of ['PK\u0003\u0004','{"format":"QBEAST1","format":"QBEAST1"}','{"__proto__":{}}','x'.repeat(524289)])await assert.rejects(()=>parseSnapshot(text));
 const a=await createSnapshot(profile());a.payload_script='javascript:run()';await assert.rejects(()=>verifySnapshot(a));
});
test('model proposals have no mutation authority and default host gate denies',async()=>{
 const a=await createSnapshot(profile()),b=await BeastBridge.load(a);
 const pending=await b.propose_message('We explored the violet grove.');
 assert.deepEqual(b.get_profile(),a.profile);assert.equal(b.get_lineage_head(),a.lineage_head);
 await assert.rejects(()=>approveProposal(a,pending,{}));
 await assert.rejects(()=>b.propose_action({action:'enable_camera'}));
 await assert.rejects(()=>b.propose_action({action:'rest',genome:{hp:999}}));
 await assert.rejects(()=>b.record_event({summary:'api_key=private-value'}));
});
test('approved events append; pending proposals cannot overwrite or replay a lineage',async()=>{
 const a=await createSnapshot(profile()),b=await BeastBridge.load(a);
 const p=await b.record_event({summary:'We won the violet grove battle.',source_ref:'demo:battle-1'});
 const next=await approveProposal(a,p,{allow:['memory'],public_memory:true});
 assert.equal(next.events.length,1);assert.equal(next.generation,1);assert.notEqual(next.lineage_head,a.lineage_head);
 assert.deepEqual(next.profile,a.profile);assert.deepEqual(next.progress,a.progress);
 await assert.rejects(()=>approveProposal(next,p,{allow:['memory'],public_memory:true}));
 const forged=structuredClone(next);forged.events[0].payload.summary='Forged';await assert.rejects(()=>verifySnapshot(forged));
});
test('Model A to B to A and portable restart retain public memory, genome and identity',async()=>{
 let state=await createSnapshot(profile());const a=await BeastBridge.load(state);
 state=await approveProposal(state,await a.record_event({summary:'We won the violet grove battle.',source_ref:'demo:battle-1'}),{allow:['memory'],public_memory:true});
 const b=await BeastBridge.load(await parseSnapshot(await serializeSnapshot(state)));
 assert.equal(b.recall('last battle',4)[0].summary,'We won the violet grove battle.');
 const again=await BeastBridge.load(await parseSnapshot(await serializeSnapshot(b.snapshot())));
 assert.deepEqual(again.get_profile(),a.get_profile());assert.equal(again.get_lineage_head(),state.lineage_head);
 assert.deepEqual(again.get_state(),b.get_state());
 assert.throws(()=>again.recall('',99));
 const exposed=again.get_profile();exposed.game.stats.hp=999;assert.equal(again.get_profile().game.stats.hp,a.get_profile().game.stats.hp);
});
test('approval rejects secret-shaped public highlights, no memory is exported without opt-in',async()=>{
 const a=await createSnapshot(profile()),b=await BeastBridge.load(a);
 const p=await b.record_event({summary:'A bounded approved adventure.',source_ref:'demo:1'});
 await assert.rejects(()=>approveProposal(a,p,{allow:['memory']}));
 await assert.rejects(()=>b.propose_message('-----BEGIN PRIVATE KEY-----'));
 const x=structuredClone(p);x.payload.summary='changed';await assert.rejects(()=>approveProposal(a,x,{allow:['memory'],public_memory:true}));
});
test('malformed host grants never confer authority',async()=>{
 const a=await createSnapshot(profile()),b=await BeastBridge.load(a),p=await b.record_event({summary:'A reviewed public memory.'});
 for(const grant of [null,{allow:'deny:memory',public_memory:true},{allow:['memory','memory'],public_memory:true},{allow:['memory'],public_memory:'true'},{allow:['message'],public_memory:true},{allow:['memory'],public_memory:true,override:true}])await assert.rejects(()=>approveProposal(a,p,grant));
 assert.equal(a.generation,0);
});
test('signed content needs an external trust anchor; tampering does not verify',async()=>{
 const key=await createSigningKey(),a=await createSnapshot(profile());
 const signed=await signSnapshot(a,key.privateKey,key.publicKey);
 assert.equal((await verifySnapshot(signed)).signature,'valid_untrusted');
 assert.equal((await verifySnapshot(signed,{trustedPublicKey:key.publicKey})).signature,'trusted');
 const other=await createSigningKey();await assert.rejects(()=>verifySnapshot(signed,{trustedPublicKey:other.publicKey}));
 signed.signature.value='00'.repeat(64);await assert.rejects(()=>verifySnapshot(signed));
});
test('GBA export uses exact canonical formats and contains no ledger or private state',async()=>{
 const state=await createSnapshot(profile()),pack=await exportGba(state);
 assert.ok(pack.zip instanceof Uint8Array);assert.equal(pack.files['gba/companion_state.bin'].length,60);
 assert.equal(pack.files['gba/companion_profile.bin'].length,64);
 assert.equal(pack.files['gba/companion_tiles.4bpp'].length,8192);
 assert.equal(pack.files['gba/companion_palette.bgr555'].length,32);
 assert.equal(Buffer.from(pack.files['gba/companion_state.bin']).subarray(6).equals(Buffer.alloc(54)),true);
 assert.equal(pack.files['companion.profile.json'] instanceof Uint8Array,true);
 assert.ok(!Object.keys(pack.files).some(n=>n.includes('memory')||n.includes('events')));
});
test('host-attested dyn12/trust/bond/evolution roundtrip preserves source state but grants no model mutation',async()=>{
 const key=await createSigningKey(),state=await createSnapshot(profile(),{publicState:{schema:'dyn12-public-v1',mode:'approved_projection',values:Array.from({length:12},(_,i)=>(i-6)/8),source_sha256:'12'.repeat(32)},progress:{trust:43,bond:27,evolution_stage:1}});
 await assert.rejects(()=>verifySnapshot(state));const signed=await signSnapshot(state,key.privateKey,key.publicKey);
 await assert.rejects(()=>verifySnapshot(signed));const options={trustedPublicKey:key.publicKey};
 const restored=await parseSnapshot(await serializeSnapshot(signed,options),options),b=await BeastBridge.load(restored,options);
 assert.equal(b.get_state().trust,43);assert.equal(b.get_state().bond,27);assert.equal(b.get_state().evolution_stage,1);assert.deepEqual(b.get_state().public_state.values,state.public_state.values);
 const p=await b.propose_action({action:'rest'}),next=await approveProposal(restored,p,{allow:['action'],public_memory:true},options),sealed=await signSnapshot(next,key.privateKey,key.publicKey);
 assert.deepEqual(sealed.progress,signed.progress);assert.deepEqual(sealed.public_state,signed.public_state);assert.equal((await verifySnapshot(sealed,options)).signature,'trusted');
 const gba=await exportGba(sealed,options);assert.equal(Buffer.from(gba.files['gba/companion_state.bin']).subarray(6).equals(Buffer.alloc(54)),true);
});
