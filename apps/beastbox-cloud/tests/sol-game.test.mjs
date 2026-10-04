import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

test('native game entry uses a bounded QBEAST handoff and the current verified cartridge player',()=>{
 const source=readFileSync(new URL('../components/sol-spark-player.tsx',import.meta.url),'utf8');
 assert.match(source,/arcade\/sol-spark-gate\/\?mode=handheld/);
 assert.match(source,/checkedSpark\(text\)/);
 assert.match(source,/event\.origin!==ROOT/);
 assert.match(source,/event\.source!==frame\.current/);
 assert.match(source,/sol-spark-admitted/);
 assert.doesNotMatch(source,/SIM_EARTH|Pocket Reality|getUserMedia|api\/bridge/);
});
