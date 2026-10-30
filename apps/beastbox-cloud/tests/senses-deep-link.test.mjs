import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
test('world menu Senses item deep-links to the Senses panel',()=>{
 const o=readFileSync(new URL('../lib/world/world-options.mjs',import.meta.url),'utf8');assert.match(o,/href:'\/workspace#senses'/);
 const s=readFileSync(new URL('../components/studio.tsx',import.meta.url),'utf8');assert.match(s,/location\.hash==='#senses'\|\|q==='senses'\)\{setPage\('SETTINGS'\)/);});
