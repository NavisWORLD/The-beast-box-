import test from 'node:test';
import assert from 'node:assert/strict';
import * as controls from '../lib/companion/go-hud.mjs';
const {GBA_KEYS,GBA_ACTIONS,normalizeGameButton,pressCartridge}=controls;
test('public control actions map to exactly the established emulator buttons',()=>{
 const expected={MOVE_UP:'up',MOVE_DOWN:'down',MOVE_LEFT:'left',MOVE_RIGHT:'right',ACTION_A:'a',ACTION_B:'b',START:'start',SELECT:'select'};
 for(const [action,button] of Object.entries(expected)){assert.equal(normalizeGameButton(action),button);assert.equal(normalizeGameButton(button),button);assert.equal(GBA_ACTIONS[button],action);}
 assert.equal(normalizeGameButton('teleport'),null);assert.equal(normalizeGameButton('__proto__'),null);
});
test('a local emulator input uses one transport, avoiding simulated plus keyboard duplication',()=>{
 const inputs=[],host={EJS_emulator:{gameManager:{simulateInput:(p,i,value)=>inputs.push([p,i,value])}},dispatchEvent:event=>{inputs.push(['duplicate-key',event.type]);}};
 for(const button of Object.keys(GBA_KEYS)){assert.equal(pressCartridge(button,true,host),true);assert.equal(pressCartridge(button,false,host),true);}
 assert.equal(inputs.length,Object.keys(GBA_KEYS).length*2);assert.ok(inputs.every(row=>row[0]===0));
});
