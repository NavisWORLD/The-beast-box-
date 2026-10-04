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
 assert.match(home,/href="\/research"/);
 assert.match(read('app/try/page.tsx'),/guest_stateless/);
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
 assert.match(model,/prefers-reduced-motion: reduce/);
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
test('all world cards use allowlisted owner-only deep links',()=>{
 const cage=read('components/beast-cage-portal.tsx'),owner=read('components/studio.tsx');
 for(const path of ['brain-bay','memory-nebula','sensorium','synapse-observatory','connector-dock']){
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
 assert.match(spark,/\/spark\/runs\.json/);
 assert.match(spark,/renderBeast/);
 assert.match(spark,/behavior\.gait/);
 assert.match(spark,/Voice\.utterance/);
 assert.match(studio,/SparkBeastSettings/);
 assert.match(settings,/SIM EARTH embedded here/);
 assert.match(release,/sim_earth_embedded:false/);
 assert.match(release,/same_companion_profile:true/);
 assert.doesNotMatch(spark,/SIM_EARTH|<iframe|getUserMedia|\/api\/bridge/);
});
