import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
test('phone width: home RECORDED/SIMULATED label is capped so the Universe button never covers it',()=>{
 const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
 assert.match(css,/@media\(max-width:600px\)\{\.home-pocket-layer \[data-sand-source\]\{max-width:33%/);
 assert.match(css,/\.home-menu-layer \[data-world-menu=home\]\{top:14%;right:18%\}/);
});
