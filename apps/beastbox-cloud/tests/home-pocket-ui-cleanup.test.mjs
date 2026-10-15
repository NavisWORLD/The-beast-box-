import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
test('home pocket overlaps cleaned: mini companion shrunk (support panel kept), chat launcher above the dock',()=>{
 const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
 assert.match(css,/body:has\(\.zeref-sprite3d\) \.cosmic-support\{transform:scale\(\.7\)/);assert.ok(!/cosmic-support\{display:none/.test(css),"Feed the Beast support stays reachable");
 assert.match(css,/launcher"\]\{bottom:calc\(68px/);
 assert.match(css,/companion-provider-module"\]\[class\*="shell"\]\{display:none/);assert.match(css,/site-sound-dock-module[^{]*\{left:calc\(max\(8px/);
 const pd=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
 for(const k of ['Genesis Engine','fbm(','AdditiveBlending','CircleGeometry','autoOrbit'])assert.ok(pd.includes(k),k);});
