import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=x=>readFileSync(new URL('../'+x,import.meta.url),'utf8');
test('guest game-lab is public, local and separated from stateless real model chat',()=>{
 const lab=read('components/gba-guest-lab.tsx'),portal=read('components/beast-cage-portal.tsx');
 assert.match(portal,/href="\/beast-cage\/guest"/);
 assert.match(read('app/beast-cage/guest/page.tsx'),/GuestGbaLab/);
 assert.match(lab,/makeGbaZip\(look,null\)/);
 assert.match(lab,/No camera, microphone or memory access/);
 assert.doesNotMatch(lab,/\/api\/bridge|ownerToken|BEASTBOX_CLOUD_BRIDGE_TOKEN|navigator\.mediaDevices/);
 const guest=read('components/beast-cage-talk.tsx');
 assert.match(guest,/fetch\('\/api\/guest'/);
 assert.match(guest,/guest_stateless!==true/);
});
test('portable GBA export never copies private content into guest pack',()=>{
 const source=read('lib/gba-companion.ts');
 assert.match(source,/GBA_EXPORT_SCHEMA='beast-cage-gba-v1'/);
 assert.match(source,/framePixels/);
 assert.match(source,/spriteTiles/);
 assert.match(source,/const bytes=new Uint8Array\(4\*2048\)/);
 assert.match(source,/const result=new Uint8Array\(32\)/);
 assert.match(source,/const raw=new Uint8Array\(60\)/);
 assert.match(source,/guest|visual preset only/);
 assert.match(source,/includes_personal_memories:false/);
 assert.match(source,/model_weights_included:false,tool_authority:false/);
 assert.doesNotMatch(source,/getUserMedia|\/api\/bridge|Authorization:|fetch\('https:|privateKey|sessionStorage/);
});
test('checkpoint inclusion is limited to explicit owner click and valid 12+12 numerical axes',()=>{
 const owner=read('components/owner-gba-export.tsx'),source=read('lib/gba-companion.ts');
 const studio=read('components/studio.tsx');
 assert.match(studio,/<OwnerGbaExport trace=\{trace\}\/>/);
 assert.match(owner,/if\(!approved\|\|!measured\|\|busy\)return/);
 assert.match(owner,/I explicitly approve/);
 assert.match(owner,/makeGbaZip\(look,measured\)/);
 assert.match(source,/signals\.provenance!=='measured-during-durable-turn'/);
 assert.match(source,/checkpoint_sha256/);
 assert.match(source,/Array\.isArray\(value\)&&value.length===12/);
 assert.match(source,/No silent saturation|no silent saturation/);
 assert.doesNotMatch(owner,/localStorage\.setItem|document\.cookie|\/api\/guest/);
});
test('exact public source archive and server release marker are present',()=>{
 for(const name of ['beast_companion.h','beast_companion.c','example_gba.c','README.md','AGENTS.md'])
  assert.ok(read('public/gba-module/'+name).length>120,name);
 const api=read('app/api/gba-release/route.ts');
 assert.match(api,/beast-cage-guest-gba-20261001/);
 assert.match(api,/guest_contains_private_memory:false/);
 assert.match(api,/hardware_tested:false/);
 const c=read('public/gba-module/beast_companion.c');
 assert.match(c,/BEAST_SNAPSHOT_BYTES/);
 assert.match(c,/data\[6\]>1u/);
 assert.match(c,/beast_visual_energy/);
});
