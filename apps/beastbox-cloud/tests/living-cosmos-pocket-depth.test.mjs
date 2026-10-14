import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const s=readFileSync(new URL('../components/cage-pocket-dimension.tsx',import.meta.url),'utf8');
test('pocket keeps its world and adds depth layers that are disposed with the scene',()=>{
 for(const k of ['createPocketSky','GridHelper','FogExp2','RingGeometry(4.25','SphereGeometry(30','ACESFilmicToneMapping','scene.traverse'])assert.ok(s.includes(k),k);
 assert.match(s,/low\?70:180/);});
