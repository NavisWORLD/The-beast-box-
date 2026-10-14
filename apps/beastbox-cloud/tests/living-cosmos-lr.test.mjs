import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {GBA_KEYS,STANDARD_GAMEPAD_BUTTONS,GBA_ACTIONS} from '../lib/companion/go-hud.mjs';
test('native player shows L/R and the input contract maps them for touch, keyboard and gamepad',()=>{
 assert.match(readFileSync(new URL('../components/sol-spark-player.tsx',import.meta.url),'utf8'),/<GbaControls shoulders enabled=\{inputEnabled\}\/>/);
 assert.equal(GBA_KEYS.l.index,10);assert.equal(GBA_KEYS.r.index,11);assert.equal(GBA_KEYS.l.key,'q');assert.equal(GBA_KEYS.r.key,'e');
 assert.equal(STANDARD_GAMEPAD_BUTTONS[4],'l');assert.equal(STANDARD_GAMEPAD_BUTTONS[5],'r');assert.equal(GBA_ACTIONS.l,'ACTION_L');});
