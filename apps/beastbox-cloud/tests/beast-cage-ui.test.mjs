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
 assert.match(model,/new THREE.WebGLRenderer/);
 assert.match(model,/new THREE.ExtrudeGeometry/);
 assert.match(model,/new THREE.MeshPhysicalMaterial/);
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
 assert.doesNotMatch(dock,/getUserMedia|api\('bridge|localStorage|Math.random/);
});
test('browser-only cosmetic preference is not a fake COSMOS identity',()=>{
 const cage=read('components/beast-cage-portal.tsx');
 assert.match(cage,/beastbox-cage-appearance-v1/);
 assert.match(cage,/window.localStorage.setItem\(STORAGE,look\)/);
 assert.match(cage,/browser-only visual preview, not an additional COSMOS identity/);
 assert.doesNotMatch(cage,/fetch\(|api\('bridge/);
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
