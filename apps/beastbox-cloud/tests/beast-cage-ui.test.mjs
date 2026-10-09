import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
test('owner-only runtime and stateless guest remain separate from public cage',()=>{
 const studio=read('components/studio.tsx'),home=read('app/page.tsx');
 assert.match(studio,/if\(!owner\)return <Login/);
 assert.match(studio,/LiveSenses visible=\{page==='SETTINGS'\}/);
 assert.match(studio,/CosmicCompanionDock model=\{model\}/);
 assert.match(studio,/onContext=\{updateLiveContext\}/);
 assert.match(read('app/beast-cage/page.tsx'),/BeastCagePortal/);
 assert.match(home,/href="\/beast-cage"/);
 assert.match(home,/className="public-journey-links"/);
 assert.match(home,/href="\/spark\/index\.html"/);
 assert.match(home,/href="\/sol-game"/);
 assert.match(home,/href="\/research"/);
 assert.match(read('app/try/page.tsx'),/guest_stateless/);
});
test('public journey is simple, welcoming, and consistent across the main surfaces',()=>{
 const home=read('app/page.tsx'),spark=read('public/spark/index.html'),cage=read('components/beast-cage-portal.tsx'),game=read('app/sol-game/page.tsx'),studio=read('components/studio.tsx');
 for(const label of ['My Beast','Beast Cage','Lost COSMOS','Brain Bay','Lab']) assert.match(home,new RegExp(label));
 assert.match(home,/A place for every person/);
 assert.match(home,/Dreamer, idler with time to wander, player, builder/);
 assert.match(home,/NO LOGIN TO MEET YOUR BEAST/);
 assert.match(spark,/MY BEAST → BEAST CAGE → LOST COSMOS/);
 assert.match(spark,/Mobile Spark navigation/);
 assert.match(cage,/Talk to My Beast/);
 assert.match(cage,/Enter LOST COSMOS/);
 assert.match(cage,/More ways to explore/);
 assert.match(game,/YOUR BEAST · YOUR CARTRIDGE · SAME IDENTITY/);
 assert.match(studio,/'settings':'SETTINGS'/);
});

test('real geometric 3D, GPU bounds and reduced-motion illustration fallback',()=>{
 const model=read('components/cosmic-companion-3d.tsx');
 const rig=read('lib/creature-model.ts');
 assert.match(model,/new THREE.WebGLRenderer/);
 assert.match(model,/createCreatureRig\(/);
 assert.match(rig,/new THREE.ExtrudeGeometry/);
 assert.match(rig,/new THREE.MeshPhysicalMaterial/);
 assert.match(model,/requestAnimationFrame/);
 assert.match(model,/document.hidden/);
 assert.match(model,/useUniverseMotion/);assert.match(read('components/use-universe-motion.ts'),/prefers-reduced-motion: reduce/);
 assert.match(model,/cosmic-creature.svg/);
 assert.doesNotMatch(model,/fetch\(|getUserMedia\(|MediaRecorder|localStorage/);
});
test('local numeric signals and owner privacy stop never confer model authority',()=>{
 const device=read('components/device-panel.tsx');
 const dock=read('components/cosmic-companion-dock.tsx');
 assert.match(device,/getFloatTimeDomainData/);
 assert.match(device,/local-measurement-v1/);
 assert.match(dock,/beastbox:local-sensor-level/);
 assert.match(dock,/beastbox:master-privacy-stop/);
 assert.match(dock,/last.sequence/);
 assert.match(dock,/SparkBeastCompanion profile=\{cosmeticProfile\}/);
 for(const forbidden of ['getUserMedia',"api('bridge",'localStorage.setItem','localStorage.removeItem','Math.random'])
  assert.equal(dock.includes(forbidden),false,'Unexpected companion authority or retention: '+forbidden);
});
test('browser-only active Beast profile is not a fake COSMOS identity or authority',()=>{
 const cage=read('components/beast-cage-portal.tsx');
 const provider=read('components/companion-provider.tsx');
 assert.match(cage,/beastbox-cage-appearance-v1/);
 assert.match(cage,/SparkBeastCompanion/);
 assert.match(provider,/beastbox-active-creature-v1/);
 assert.match(provider,/validCreature/);
 assert.doesNotMatch(cage,/api\('bridge/);
 assert.doesNotMatch(provider,/api\('bridge|getUserMedia|Authorization|BEASTBOX_CLOUD_BRIDGE_TOKEN/);
});
test('accessible iPhone and 320px fallback styling exists',()=>{
 const css=read('app/globals.css');
 assert.match(css,/@media\(max-width:360px\)/);
 assert.match(css,/@media\(max-width:680px\)/);
 assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
 assert.match(css,/\.companion-dock/);
 assert.match(css,/pointer-events:none/);
 assert.match(read('app/layout.tsx'),/device-width/);
});

test('homepage truly renders the procedural galaxy creature, not merely a static SVG',()=>{
 const home=read('app/page.tsx');
 const hero=read('components/homepage-creature.tsx');
 assert.match(home,/HomepageCreature/);
 assert.match(hero,/CosmicCompanion3D quality="low"/);
 assert.match(hero,/turntable=\{spin\}/);
 assert.match(home,/Enter the Beast Cage/);
});
test('the same active Spark Beast reaches customize and the owner dock without model authority',()=>{
 const cage=read('components/beast-cage-portal.tsx');
 const dock=read('components/cosmic-companion-dock.tsx');
 assert.match(cage,/SparkBeastCompanion profile=\{creature\}/);
 assert.match(dock,/SparkBeastCompanion profile=\{cosmeticProfile\}/);
 assert.match(dock,/beastbox:master-privacy-stop/);
 assert.doesNotMatch(cage,/\/api\/bridge/);
 assert.doesNotMatch(dock,/localStorage\.setItem|getUserMedia|api\('bridge/);
});
test('public Brain Bay is separate while advanced world cards retain allowlisted owner-only links',()=>{
 const cage=read('components/beast-cage-portal.tsx'),owner=read('components/studio.tsx');
 assert.ok(cage.includes("href:'/brain-bay'"));
 for(const path of ['memory-nebula','sensorium','synapse-observatory','connector-dock']){
  assert.ok(cage.includes('/workspace#'+path));
  assert.ok(owner.includes("'"+path+"'"));
 }
 assert.match(owner,/if\(!owner\)return/);
});

test('seeded 3D source is shared with its actual downloaded GLB',()=>{
 const component=read('components/cosmic-companion-3d.tsx');
 const rig=read('lib/creature-model.ts'),exporter=read('lib/creature-glb.ts');
 const lab=read('components/gba-guest-lab.tsx');
 assert.match(component,/createCreatureRig\(profile,look,quality\)/);
 assert.match(rig,/profile\.appearance\.constellation/);
 assert.match(rig,/profile\.appearance\.finPattern/);
 assert.match(rig,/profile\.appearance\.haloPattern/);
 assert.match(exporter,/createCreatureRig\(profile,look,'auto'\)/);
 assert.match(exporter,/animations:creatureAnimationClips\(\)/);
 assert.match(exporter,/GLTFExporter/);
 assert.match(lab,/Download original 3D model/);
 assert.doesNotMatch(exporter,/fetch\(|\/api\/bridge|credentials|localStorage/);
});
test('one persistent public companion stores only its validated game profile',()=>{
 const layout=read('app/layout.tsx'),roamer=read('components/companion-provider.tsx');
 const geometry=read('lib/companion-roaming.ts');
 assert.match(layout,/<CompanionProvider>\{children\}<\/CompanionProvider>/);
 assert.match(roamer,/beastbox:master-privacy-stop/);
 assert.match(roamer,/selectSafeRoamSpot/);
 assert.match(roamer,/usePathname/);
 assert.match(roamer,/validCreature/);
 assert.match(roamer,/beastbox-active-creature-v1/);
 assert.match(roamer,/SparkBeastCompanion/);
 assert.match(geometry,/rectanglesIntersect/);
 assert.doesNotMatch(roamer,/\/api\/bridge|getUserMedia|indexedDB|setModel|Authorization|ownerToken/);
});

test('generated character moves between Cage and guest via client navigation, never full reload',()=>{
 const cage=read('components/beast-cage-portal.tsx');
 const guest=read('components/gba-guest-lab.tsx');
 assert.match(cage,/<Link href="\/beast-cage\/guest">Take this creature/);
 assert.doesNotMatch(cage,/<a href="\/beast-cage\/guest">Take this creature/);
 assert.match(guest,/profile:sharedProfile/);
 assert.match(guest,/createCreatureGlb\(creature,look\)/);
});

test('unified Spark companion uses the real sprite, gait and voice modules without SIM EARTH',()=>{
 const spark=read('components/spark-beast-companion.tsx');
 const settings=read('components/spark-beast-settings.tsx');
 const release=read('app/api/companion-release/route.ts');
 const studio=read('components/studio.tsx');
 assert.match(spark,/public\/spark\/draw\.mjs/);
 assert.match(spark,/public\/spark\/genome\.mjs/);
 assert.match(spark,/public\/spark\/voice\.mjs/);
 assert.match(spark,/loadSparkRuns/);
 assert.match(read('public/spark/runs.mjs'),/\/spark\/runs\.json/);
 assert.match(spark,/renderBeast/);
 assert.match(spark,/behavior\.gait/);
 assert.match(spark,/Voice\.utterance/);
 assert.match(studio,/SparkBeastSettings/);
 assert.match(settings,/Separate planetary simulator embedded/);
 assert.match(release,/sim_earth_embedded:false/);
 assert.match(release,/same_companion_profile:true/);
 assert.doesNotMatch(spark,/SIM_EARTH|<iframe|getUserMedia|\/api\/bridge/);
});

test('public Beast generator loads all sanitized seed shards and never ships raw workload payloads',()=>{
 const app=read('public/spark/app.mjs');
 const spark=read('components/spark-beast-companion.tsx');
 const cage=read('components/beast-cage-portal.tsx');
 const release=read('app/api/companion-release/route.ts');
 const index=JSON.parse(read('public/spark/user-seeds-20261004.json'));
 assert.equal(index.schema,'spark-beasts-public-seed-pack-index-v1');
 assert.equal(index.totals.unique_jobs,96);
 assert.equal(index.shards.length,4);
 assert.equal(index.privacy.raw_circuits_published,false);
 assert.equal(index.privacy.user_ids_published,false);
 assert.equal(index.privacy.original_signal_payloads_published,false);
 assert.equal(index.privacy.derived_counts_public,true);
 let total=0;
 for(const path of index.shards){
  const shard=JSON.parse(read('public'+path.replace('/spark','/spark')));
  assert.equal(shard.schema,'spark-beasts-public-seed-shard-v1');
  total+=shard.runs.length;
  const raw=JSON.stringify(shard);
  assert.doesNotMatch(raw,/QuantumCircuit|user_id|BEGIN PRIVATE|authorization|api[_ -]?key/i);
 }
 assert.equal(total,96);
 assert.match(app,/loadSparkRuns\(\{includeNewHardware:true\}\)/);
 assert.match(read('public/spark/runs.mjs'),/MARRAKESH_HARDWARE_PATH/);
 assert.match(app,/num_bits>=2/);
 assert.match(read('public/spark/runs.mjs'),/user-seeds-20261004\.json/);
 assert.match(spark,/sameSpark\?runs\.find/);
 assert.match(read('public/spark/runs.mjs'),/index\.shards/);
 assert.match(cage,/Open Public Beast Generator/);
 assert.match(release,/public_seed_jobs_added:96/);
 assert.match(release,/original_signal_payloads_published:false/);
});

test('mobile Lost Cosmos dock can mini expand close and reopen without dropping the connected Beast',()=>{
 const dock=read('components/lost-cosmos-dock.tsx');
 const css=read('components/lost-cosmos-dock.module.css');
 const roamer=read('components/companion-provider.tsx');
 const roamerCss=read('components/companion-provider.module.css');
 const spark=read('components/spark-beast-companion.tsx');
 assert.match(dock,/data-lost-cosmos-dock="true"/);
 assert.match(dock,/data-dock-state=\{state\}/);
 assert.match(dock,/Open Lost Cosmos player/);
 assert.match(dock,/Close Lost Cosmos player/);
 assert.match(dock,/Expand Lost Cosmos player/);
 assert.match(dock,/Generate Beast/);
 assert.match(dock,/creature\?\.id/);
 assert.match(css,/width:min\(250px,calc\(100vw - 72px\)\)/);
 assert.match(css,/\.closed \.screen/);
 assert.match(css,/\.dock:not\(\.wide\):not\(\.full\)\{pointer-events:none\}/);
 assert.match(css,/\.dock:not\(\.wide\):not\(\.full\) \.bar\{pointer-events:none\}/);
 assert.match(css,/\.dock:not\(\.wide\):not\(\.full\) \.screen\{pointer-events:none\}/);
 assert.match(css,/\.poster button.*\.launcher\{pointer-events:auto\}/);
 assert.match(roamer,/Enable creature sounds/);
 assert.match(roamer,/beastbox:spark-chirp/);
 assert.match(roamer,/audioChannel="roamer"/);
 assert.match(roamerCss,/width:110px/);
 assert.match(roamerCss,/top 1\.55s/);
 assert.match(spark,/audioChannel\?:string/);
 assert.match(spark,/beastbox:spark-chirp/);
 assert.doesNotMatch(roamer,/getUserMedia|\/api\/bridge|Authorization/);
});

test('roaming pet reserves the full mobile dock footprint including its toolbar',()=>{
 const provider=read('components/companion-provider.tsx');
 assert.match(provider,/padX=width<680\?84:54/);
 assert.match(provider,/padTop=width<680\?64:44/);
 assert.match(provider,/aside\[data-cosmos-mode="mini"\]/);
 assert.match(provider,/rect\.left-padX/);
});
