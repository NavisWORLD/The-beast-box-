import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('How this look is made carries Emeth labels verbatim',()=>{for(const t of ['Horizon layers · SEEDED','Planets and rings lit by one sun · SEEDED','Lightning from storms · SIMULATED','Spark shimmer · SIMULATED','No storm reading, no flashes · ABSENT','Flashes softened for reduced motion'])assert.ok(src.includes(`'${t}'`),t);
 assert.ok(src.includes('data-lw-gx-labels')&&src.includes('gxReducedMotion()?'));assert.ok(!/Math\.random/.test(src));});
