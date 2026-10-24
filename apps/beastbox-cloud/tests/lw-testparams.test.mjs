import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('?hold=1 and ?growthdebug=1 are opt-in URL params read once',()=>{
 assert.match(lw,/\[\?&\]hold=1\\b/);assert.match(lw,/\[\?&\]growthdebug=1\\b/);
});
test('hold freezes idle drift, sway, zoom and the time of day only when set',()=>{
 assert.match(lw,/const idle=!HOLD&&performance\.now\(\)-userAt>6000/);
 assert.match(lw,/const sw=HOLD\?0:Math\.sin\(t\*\.15\)/);
 assert.match(lw,/if\(HOLD\)\{if\(hz\.m!==mode\)/);
 assert.match(lw,/if\(HOLD\)\{if\(hz\.a===null\)hz\.a=a;a=hz\.a;\}/);
});
test('growthdebug readout is a DOM overlay with tap counts and adds no hardcoded text',()=>{
 assert.match(lw,/data-lw-growthdebug/);assert.match(lw,/gTaps\[g\.node\.id\]/);
});
