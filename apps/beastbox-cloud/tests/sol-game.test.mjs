import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

test('native game entry uses a bounded QBEAST handoff and the current verified cartridge player',()=>{
 const source=readFileSync(new URL('../components/sol-spark-player.tsx',import.meta.url),'utf8');
 assert.match(source,/arcade\/sol-spark-gate\/\?mode=handheld&controller=previeworigin41/);
 assert.match(source,/checkedSpark\(text\)/);
 assert.match(source,/event\.origin!==ROOT/);
 assert.match(source,/event\.source!==frame\.current/);
 assert.match(source,/sol-spark-admitted/);
 assert.match(source,/sol-spark-start/);
 assert.match(source,/sol-spark-running/);
 assert.match(source,/beastbox:gba-input/);
 assert.match(source,/sol-spark-input/);
 assert.match(source,/sol-spark-input-ack/);
 assert.match(source,/sol-spark-return-request/);
 assert.match(source,/lost-cosmos-return-v1/);
 assert.match(source,/applyGameReturn/);
 assert.match(source,/SAVE JOURNEY TO BEAST BOX/);
 assert.doesNotMatch(source,/SIM_EARTH|Pocket Reality|getUserMedia|api\/bridge/);
});
