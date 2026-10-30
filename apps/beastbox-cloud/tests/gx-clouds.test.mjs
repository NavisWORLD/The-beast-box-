// GENESIS X step 2: layered volumetric clouds in the first-person sky, lit by the one sun (self-shadow march toward uSun), darkening and thickening with storm. No random calls, no own clock.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../lib/universe/p2-sky-three.ts',import.meta.url),'utf8');
test('three decks on desktop, two on phones',()=>{assert.match(src,/uLayers:\{value:phone\?2:3\}/);assert.match(src,/for\(int k=0;k<3;k\+\+\)\{if\(float\(k\)>=uLayers\)break;/);});
test('lit only by the one sun uniform, with a march toward it',()=>{assert.match(src,/vec3 S=normalize\(uSun\)/);assert.match(src,/fbm\(q\+sp\*o\)/);assert.match(src,/exp\(-2\.2\*sh\*\(1\.0\+uDark\)\)/);assert.doesNotMatch(src,/DirectionalLight|PointLight/);});
test('storm darkens and thickens the low deck',()=>{assert.match(src,/uCover\*\(\.95\+\.6\*uDark\)/);assert.match(src,/lit\*=1\.0-\.55\*uDark\*den/);});
test('no Math.random, no performance.now / Date in the sky layers',()=>{assert.doesNotMatch(src,/Math\.random|performance\.now|Date\.now/);});
