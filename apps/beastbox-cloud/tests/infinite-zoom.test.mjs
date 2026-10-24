import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const rd=n=>readFileSync(new URL('../components/'+n,import.meta.url),'utf8');
const u3=rd('universe-3d.tsx'),lw=rd('living-world.tsx'),pd=rd('cage-pocket-dimension.tsx'),pg=rd('pocket-god-view.ts');
test('/universe 3D: zoom-out has no hard stop at ZOOM_MAX; far plane and the star shell follow the camera distance',()=>{
 assert.match(u3,/ZOOM_LIMIT=1e7/);assert.match(u3,/Math\.log\(ZOOM_LIMIT\)/);assert.ok(!/Math\.min\(Math\.log\(ZOOM_MAX\)/.test(u3),'old hard clamp gone');
 assert.match(u3,/cam\.far=Math\.max\(6000,d\*5\)/);assert.match(u3,/bgStars\.position\.copy\(cam\.position\)/);assert.match(u3,/ZOOM_MAX=1400/,'old comfortable range kept');});
test('cage pocket: zoom clamps use ZOOM_LIMIT, far plane grows with distance, ZOOM_MAX stays exported',()=>{
 assert.match(pg,/ZOOM_MIN=3\.2,ZOOM_MAX=12000/);assert.match(pg,/ZOOM_LIMIT=1e6/);
 assert.ok(!/ZOOM_MIN,ZOOM_MAX\)/.test(pd));assert.match(pd,/camera\.far=Math\.max\(30000,zd\*5\)/);});
test('living world: pull-back past full orbit when it is not the /universe door; door hand-off unchanged',()=>{
 assert.match(lw,/const pullOut=\(\)=>!spawnRef\.current&&!orbitOutRef\.current/);assert.match(lw,/orbitOutRef\.current\(\);return;/);
 assert.match(lw,/Math\.exp\(zXc\*zb\.orbit\)/);assert.match(lw,/camera\.far=farW/);assert.match(lw,/lwStars\.position\.copy\(camera\.position\)/);
 });
