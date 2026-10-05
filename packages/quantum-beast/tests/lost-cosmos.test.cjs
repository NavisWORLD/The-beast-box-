const test=require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {createSnapshot,canonical}=require('../dist/verifier.js');
const {generateCreature}=require('../dist/canonical/creature-profile.js');
const {lostCosmosShare,lostCosmosShareUrl,LOST_COSMOS_SOURCE_SHA,LOST_COSMOS_URL}=require('../dist/lost_cosmos.js');

test('same verified Beast gets one stable Lost COSMOS cage transfer and the current native cartridge URL',async()=>{
 const profile=generateCreature('quantum-beast-first-contact','nebula');
 const snapshot=await createSnapshot(profile);
 const a=await lostCosmosShare(snapshot);
 const b=await lostCosmosShare(snapshot);
 assert.equal(a.transfer,b.transfer);
 assert.match(a.transfer,/^[a-f0-9]{32}$/);
 assert.equal(a.seed,profile.seed);
 assert.equal(a.family,profile.family);
 assert.equal(a.hue,profile.appearance.hueShift);
 assert.equal(a.callsign,profile.name.toUpperCase().replace(/[^A-Z0-9 ]/g,'').trim().slice(0,12));
 assert.deepEqual(a.growth,{epoch:'0',layer:0,points:0,trade:true,grown:false});
 assert.deepEqual(a.memories,[]);
 const {checksum,...body}=a;
 assert.equal(checksum,crypto.createHash('sha256').update(canonical(body)).digest('hex'));
 const url=await lostCosmosShareUrl(snapshot);
 assert.ok(url.startsWith(LOST_COSMOS_URL+'#lcshare='));
 const decoded=JSON.parse(decodeURIComponent(url.split('#lcshare=')[1]));
 assert.equal(decoded.transfer,a.transfer);
 assert.equal(decoded.checksum,a.checksum);
 assert.equal(LOST_COSMOS_SOURCE_SHA,'f2c3683f697b7ee5d35557028c4416556226bb9b');
});
