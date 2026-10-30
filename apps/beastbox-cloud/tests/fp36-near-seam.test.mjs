// First person (target 36): the flat patch meets the curved planet's horizon, so no below-horizon band, seam or teal rim; the sky caption clears the chips on phones.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const look=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
const lw=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('flat patch inner edge sits inside the 1.6 m eye horizon of the 8-unit planet',()=>{
 const m=look.match(/export const FLAT_INNER=([\d.]+)/);assert.ok(m);const inner=+m[1];
 const PR=8,eye=.47;const dip=Math.acos(PR/(PR+eye));const reach=eye/Math.tan(dip); // where the planet horizon ray meets the eye-level plane
 assert.ok(inner<=reach+.05&&inner>=.6,`inner ${inner} vs horizon reach ${reach.toFixed(2)}`);
 assert.match(look,/RingGeometry\(FLAT_INNER,R/);assert.doesNotMatch(look,/RingGeometry\(14,R/);
});
test('phone sky caption sits below the View / Motion / Quality chips',()=>{
 const m=lw.match(/--lw-line-top:calc\(env\(safe-area-inset-top\) \+ (\d+)px\)/);assert.ok(m);assert.ok(+m[1]>=160);
});
test('no Math.random in the first-person look',()=>{assert.doesNotMatch(look,/Math\.random/);});
