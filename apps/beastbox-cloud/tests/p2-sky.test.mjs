import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {p2SkyAt,P2SKY} from '../lib/universe/p2-sky.mjs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('P2 sky is driven only by the one sun, spark ticks and storm; deterministic',()=>{const a=p2SkyAt({elevDeg:30,day:1,storm:0,sparkTick:7}),b=p2SkyAt({elevDeg:30,day:1,storm:0,sparkTick:7});assert.deepEqual(a,b);assert.equal(a.label,'SIMULATED');assert.equal(P2SKY.label,'SEEDED');});
test('storm darkens, covers, rains; clear day has no rain and no aurora',()=>{const c=p2SkyAt({elevDeg:30,day:1,storm:0}),s=p2SkyAt({elevDeg:30,day:1,storm:1});assert.equal(c.rain,0);assert.equal(c.aurora,0);assert.ok(s.darken>c.darken&&s.cover>c.cover&&s.rain>.9);assert.ok(s.starFade<c.starFade&&s.moonA<c.moonA);});
test('aurora only at night and pulses with spark ticks',()=>{const n0=p2SkyAt({elevDeg:-30,day:0,sparkTick:0}),n3=p2SkyAt({elevDeg:-30,day:0,sparkTick:3});assert.ok(n0.aurora>n3.aurora&&n3.aurora>0);assert.equal(p2SkyAt({elevDeg:40,day:1,sparkTick:0}).aurora,0);});
test('no Math.random, no new light, no own clock in the P2 sky',()=>{for(const f of ['lib/universe/p2-sky.mjs','lib/universe/p2-sky-three.ts']){const s=src(f);assert.ok(!s.includes('Math.random'));assert.ok(!/Light\(/.test(s));assert.ok(!/Date\.now|performance\.now/.test(s));}
 const lw=src('components/living-world.tsx');assert.match(lw,/p2SkyAt\(\{elevDeg:os1\.elevationDeg,day:os1\.day,storm:/);assert.match(lw,/sparkTick:field\?field\.tick:0/);});
