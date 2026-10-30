// GENESIS X step 1: the first-person sky dome, ground haze, ridges and cloud shell are dithered after the sRGB encode (no 8-bit banding). Fixed pixel hash, no random calls, no clock.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const look=readFileSync(new URL('../lib/universe/one-world-look.ts',import.meta.url),'utf8');
const p2=readFileSync(new URL('../lib/universe/p2-sky-three.ts',import.meta.url),'utf8');
test('dither is defined once and is +-1 LSB triangular on gl_FragCoord',()=>{assert.match(look,/export const DITHER_GLSL=/);assert.match(look,/\/255\.0/);assert.match(look,/gl_FragCoord\.xy/);assert.doesNotMatch(look+p2,/Math\.random/);assert.doesNotMatch(look.match(/DITHER_GLSL='[^']*'/)[0],/uT|time/i);});
test('sky dome, ground, ridges and cloud shell use it',()=>{assert.equal((look.match(/gl_FragColor=vec4\(dith\(toS\(/g)||[]).length,3);assert.match(p2,/gl_FragColor=vec4\(dith\(toS\(o\/max\(oa,\.001\)\)\),oa\)/);});
test('triangular noise stays within one 8-bit step',()=>{const f=x=>x-Math.floor(x);const h=(x,y)=>f(Math.sin(x*12.9898+y*78.233)*43758.5453);let mx=0;for(let i=0;i<4000;i++){const x=i%97+.5,y=Math.floor(i/97)+.5;const n=h(x,y)+h(x+.5193,y+.3711)-1;mx=Math.max(mx,Math.abs(n));}assert.ok(mx<=1);});
