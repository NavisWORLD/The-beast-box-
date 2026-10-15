import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
test('home pocket overlaps cleaned: mini companion hidden, chat launcher above the dock',()=>{
 const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
 assert.match(css,/body:has\(\.zeref-sprite3d\) \.cosmic-support\{display:none\}/);
 assert.match(css,/launcher"\]\{bottom:calc\(68px/);
 const pd=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
 for(const k of ['Genesis Engine','fbm(','AdditiveBlending','CircleGeometry','autoOrbit'])assert.ok(pd.includes(k),k);});
