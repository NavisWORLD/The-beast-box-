import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {seededStorms,allStorms,STORM_MIN_ATMOSPHERE} from '../lib/universe/seeded-storms.mjs';
const u={seed:'abc123',planets:[{id:'s-p0',atmosphere:.7,flux:1.2},{id:'s-p1',atmosphere:.05,flux:2},{id:'s-p2',atmosphere:.4,flux:.3}],storms:[]};
test('deterministic, only atmosphere planets, always labelled SEEDED',()=>{const a=seededStorms(u),b=seededStorms(u);assert.deepEqual(a,b);assert.ok(a.length>=2);
 for(const s of a){assert.equal(s.label,'SEEDED');assert.notEqual(s.planet,'s-p1');assert.ok(s.intensity>0&&s.intensity<=.6);}
 assert.notDeepEqual(seededStorms({...u,seed:'zzz'}),a);});
test('a real or simulated storm on a planet wins over the seeded one',()=>{const live=[{id:'storm-3',planet:'s-p0',intensity:.2}];const all=allStorms({...u,storms:live});assert.equal(all[0].id,'storm-3');assert.equal(all.filter(s=>s.planet==='s-p0').length,1);});
test('no Math.random in the module',()=>{assert.ok(!/Math\.random/.test(readFileSync(new URL('../lib/universe/seeded-storms.mjs',import.meta.url),'utf8').replace(/\/\/.*$/gm,'')));assert.ok(STORM_MIN_ATMOSPHERE>0);});
