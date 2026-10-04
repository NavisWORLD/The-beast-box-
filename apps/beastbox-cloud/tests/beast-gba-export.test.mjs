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
 assert.match(api,/beast-cage-lost-cosmos-spark-alive-20261004/);
 assert.match(api,/a4057c5a8d57963bb27e157eab683852ab58bc28/);
 assert.match(api,/same_cage_transfer:true/);
 assert.match(api,/persistent-gba-player/);
 assert.match(api,/shared-spark-care-ledger/);
 assert.match(api,/guest_contains_private_memory:false/);
 assert.match(api,/hardware_tested:false/);
 assert.match(api,/lost_cosmos_page:.*arcade\/sol-spark-gate\//);
 assert.ok(api.includes("rom_url:'/api/gba-rom'"));
 assert.match(api,/sim_earth_embedded:false/);
 const c=read('public/gba-module/beast_companion.c');
 assert.match(c,/BEAST_SNAPSHOT_BYTES/);
 assert.match(c,/data\[6\]>1u/);
 assert.match(c,/beast_visual_energy/);
});

test('Quantum Beast bridge launches the same portable identity into current Lost COSMOS',()=>{
 const transfer=read('components/quantum-beast-transfer.tsx');
 const bridge=read('../../packages/quantum-beast/src/lost_cosmos.ts');
 assert.match(transfer,/PLAY THIS BEAST IN LOST COSMOS/);
 assert.match(transfer,/lostCosmosShareUrl/);
 assert.match(transfer,/window\.location\.assign\(url\)/);
 assert.match(bridge,/a4057c5a8d57963bb27e157eab683852ab58bc28/);
 assert.match(bridge,/beastbox-lost-cosmos-transfer-v1/);
 assert.match(bridge,/LCSHARE1/);
 assert.match(bridge,/origin:'beast'/);
 assert.doesNotMatch(bridge,/owner.*authority|BEASTBOX_OWNER_PASSWORD|BEASTBOX_CLOUD_AUTH_SECRET/);
});

test('public Spark game path points to Lost COSMOS and never the retired SIM world',()=>{
 const page=read('public/spark/index.html');
 const bridge=read('../../packages/quantum-beast/src/lost_cosmos.ts');
 assert.match(page,/PLAY IN LOST COSMOS/);
 assert.match(page,/href="\/sol-game"/);
 assert.doesNotMatch(page,/Play in Living Universe|SIM_EARTH_7_08_REALITY_BODY|navisworld\.github\.io\/Cosmic-synapse/);
 assert.match(bridge,/LOST_COSMOS_URL=.*arcade\/lost-cosmos\/synapse\.html/);
 assert.doesNotMatch(bridge,/SIM_EARTH|Pocket Reality|standalone\//);
});
