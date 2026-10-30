import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=f=>readFileSync(new URL('../'+f,import.meta.url),'utf8');
test('target 36: warm sun bloom by day, labelled SEEDED, core over the P1 bloom threshold, gated by the one sun day factor',()=>{const s=src('lib/universe/one-world-look.ts');
 assert.match(s,/SUNBLOOM36=Object\.freeze\(\{label:'SEEDED',core:2\.4/);assert.match(s,/\*uDay\*step\(0\.0,e\);/);assert.ok(!s.includes('Math.random'));
 const t=JSON.parse(JSON.stringify((src('lib/universe/data/p1post.mjs').match(/"threshold": ([\d.]+)/g)||[]).map(x=>+x.split(': ')[1])));assert.ok(t.length&&2.4>Math.max(...t)/0.85);});
