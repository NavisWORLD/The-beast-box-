import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=(p)=>readFileSync(new URL(`../${p}`,import.meta.url),'utf8');
test('home 3D Zeref accessible label is just "Zeref in 3D"',()=>{
 const s=read('components/zeref-sprite-3d.tsx');
 assert.match(s,/label='Zeref in 3D'/);
 assert.doesNotMatch(s,/label='[^']*Moonwraith/);
});
test('spark rig screen-reader label does not say Moonwraith',()=>{
 assert.doesNotMatch(read('components/spark-rig.tsx'),/aria-label=\{[^}]*Moonwraith/);
});
test('diary panel names the form once, without "display persona"',()=>{
 const s=read('components/zeref-diary-panel.tsx');
 assert.match(s,/Zeref's Moonwraith form is the one shown here/);
 assert.doesNotMatch(s,/display persona/i);
});
