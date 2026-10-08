import {test} from 'node:test';
import assert from 'node:assert/strict';
import {visualStateFromBeast} from '../lib/companion/creature-visual-state.mjs';

test('stored care and native growth determine only the visual pose',()=>{
 const beast={mood:'happy',energy:81,qbeast:{profile:{id:'recorded-id'}},nativeStage:2};
 const snapshot=structuredClone(beast);
 assert.equal(visualStateFromBeast(beast),'celebrating');
 assert.deepEqual(beast,snapshot,'visual state is read-only');
 beast.energy=9;assert.equal(visualStateFromBeast(beast),'sleeping');
 beast.energy=80;beast.mood='sleep';assert.equal(visualStateFromBeast(beast),'sleeping');
 beast.mood='evolve';assert.equal(visualStateFromBeast(beast),'celebrating');
 beast.mood='idle';assert.equal(visualStateFromBeast(beast),'idle');
 assert.equal(visualStateFromBeast(null),'idle');
});
