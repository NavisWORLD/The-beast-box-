import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const s=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('first person draws each REAL resident and thing once, from the real objects',()=>{
 assert.match(s,/const fpLife=\(\(\)=>\{const g=new THREE\.Group\(\);lk2Ground\.group\.add\(g\);const rs=\(residents as any\[\]\)\.map\(\(r:any\)=>\{const s=new THREE\.Sprite\(r\.sp\.material\)/);
 assert.match(s,/const ts=things\.map\(\(th:any\)=>\{const c=th\.node\.clone\(\)/);
 assert.match(s,/label:'REAL residents and things at true bearing and walking distance'/);});
test('figures sit at true walking distance, hidden near (the 3D one shows), in the bay, or for things not yet awake',()=>{
 assert.match(s,/bayV\.normalize\(\)\.multiplyScalar\(d\)/);assert.match(s,/if\(hide\|\|d<3\|\|/);assert.match(s,/put\(c,th\.n,!th\.awake\)/);});
test('the old far copies only behind a test hook',()=>{assert.match(s,/if\(\(window as any\)\.__lwFarEchoes\)lk2Ground\.addLife/);});
test('residents shelter by real things in storms, and are curious in calm first person',()=>{
 assert.match(s,/if\(storming>\.5&&!r\.nap\)\{const nt2=nearestThing\(r\.n\)/);
 assert.match(s,/if\(fpOn&&!\(r\.nap>0\)&&storming<=\.5&&r\.pause<=0&&!lwLand\?\.goalFor/);});
test('no random calls added',()=>{const add=s.split('GENESIS X life').slice(1).join('');assert.doesNotMatch(add.slice(0,4000),/Math\.random/);});
