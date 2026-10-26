import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {prettyBeastName,beastDisplayName,activeBeastName} from '../lib/companion/beast-name.mjs';
const src=f=>readFileSync(new URL(f,import.meta.url),'utf8');
test('one spelling of a hyphenated beast name: middle dot, then spaces; short names stay as typed',()=>{
 assert.equal(prettyBeastName('Zeref-Nightcat-Dragon'),'Zeref \u00b7 Nightcat Dragon');
 assert.equal(prettyBeastName('Zeref \u00b7 Nightcat Dragon'),'Zeref \u00b7 Nightcat Dragon');
 assert.equal(prettyBeastName('Spider-Man'),'Spider-Man');assert.equal(prettyBeastName('Zeref'),'Zeref');assert.equal(prettyBeastName(null),null);
 assert.equal(beastDisplayName({displayName:'Zeref-Nightcat-Dragon'}),'Zeref \u00b7 Nightcat Dragon');
 const st={getItem:k=>k==='beastbox-active-creature-v1'?JSON.stringify({name:'Zeref-Nightcat-Dragon'}):null};
 assert.deepEqual(activeBeastName(st),{name:'Zeref \u00b7 Nightcat Dragon',source:'seeded'});});
test('Look Closer: plain subtitle (no engine name), open sky stage, safe-area room for the last section',()=>{
 const p=src('../app/beast-cage/turntable/page.tsx'),c=src('../app/beast-cage/turntable/turntable.module.css');
 assert.match(p,/in 3D, built from your saved look\./);assert.doesNotMatch(p,/procedural Three\.js rig/);assert.doesNotMatch(p,/aria-label="Actual rotating Three\.js/);
 assert.doesNotMatch(p,/WORLD_SCENE_BG/);assert.match(p,/data-open-sky/);assert.match(c,/overflow:visible/);assert.match(c,/\.process\{margin-bottom:calc\(72px \+ env\(safe-area-inset-bottom/);});
test('menu names match the canonical nav; no raw creature id on the home-base card by default',()=>{
 const portal=src('../components/beast-cage-portal.tsx');
 for(const old of ['Adventure walk</Link> · <Link href="/beast-cage/field">📷 Lost COSMOS Field (camera)','Game lab','Workshop deck','>3D model<'])assert.ok(!portal.includes(old),old);
 for(const n of ['Tiny World','Look Closer','Lost COSMOS Field','Catch a Star','>Workshop<'])assert.ok(portal.includes(n),n);
 assert.doesNotMatch(src('../components/beast-go.tsx'),/Workshop deck/);
 const d=src('../components/creature-dashboard.tsx');assert.match(d,/<p>Saved on this device, for \{name\}\.<\/p>/);assert.match(d,/<p data-advanced-only>Saved as <code>\{id\}<\/code>/);});
test('the crest petals fan back into a cone and the back glow is a soft gradient, not a hard disc',()=>{
 assert.match(src('../lib/creature-model.ts'),/rotation\.order='ZXY'.*rotation\.x=i%2\?-\.78:-\.52/s);
 const c=src('../components/cosmic-companion-3d.tsx');assert.match(c,/glowTex/);assert.doesNotMatch(c,/new THREE\.CircleGeometry\(1\.9/);});
test('open-stage pack hints: SEEDED chip stays, haze colour matches the ground fade, 46 degree lens and three-quarter start on the turntable only',()=>{
 const p=src('../app/beast-cage/turntable/page.tsx'),c=src('../app/beast-cage/turntable/turntable.module.css'),m=src('../components/cosmic-companion-3d.tsx');
 assert.match(p,/data-stage-seeded>SEEDED/);assert.match(c,/#252431/);assert.match(c,/#7662a3/);
 assert.match(m,/rotationRef\.current\.turntable\|\|rotationRef\.current\.angle!==null\)\{[^}]*camera\.fov=46/);assert.match(m,/turntablePhase=rotationRef\.current\.turntable\?35\*Math\.PI\/180:0/);});
