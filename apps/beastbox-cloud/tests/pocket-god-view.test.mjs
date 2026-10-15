import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/pocket-god-view.ts',import.meta.url),'utf8');
const pd=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
test('god view: habitat on a planet, orbiting suns, inside a galaxy, credited to the Genesis Engine',()=>{
 for(const k of ['Genesis Engine','PLANET_R','createAtmosphere','orbitR','binary','galaxy','fbm('])assert.ok(src.includes(k),k);
 assert.match(src,/gN=low\?900:2400/,'capped particles');});
test('free orbit + multi-scale zoom from close-up to galaxy',()=>{
 assert.match(src,/ZOOM_MIN=3\.2,ZOOM_MAX=12000/);assert.match(pd,/Math\.exp\(event\.deltaY\*\.0016\)/);assert.match(pd,/\.06,3\.08\)/);
 assert.match(pd,/PerspectiveCamera\(46,1,\.1,30000\)/);});
test('quantum honesty: only the labelled counts feed growth; nothing is invented',()=>{
 assert.match(src,/countWeights\(o\.counts\)/);assert.ok(!/Math\.random/.test(src));assert.ok(!/fetch\(|localStorage/.test(src));
 assert.ok(!/hardware/.test(src.replace(/never hardware/,'')));});
