import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('real model has geometric 360 yaw rather than a static sprite swap',()=>{
 const m=read('components/cosmic-companion-3d.tsx'),page=read('app/beast-cage/turntable/page.tsx');
 assert.match(m,/new THREE\.ExtrudeGeometry/);
 assert.match(m,/const stars=document\.createElement\('canvas'\)/);
 assert.match(m,/rotationRef\.current\.turntable/);
 assert.match(m,/turntablePhase/);
 assert.match(page,/turntable=\{spin\}/);
 for(const angle of ['0','90','180','270'])assert.match(page,new RegExp(angle));
 assert.match(page,/source prompt \/ process/);
});
