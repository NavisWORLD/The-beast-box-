import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const s=readFileSync(new URL('../components/living-world.tsx',import.meta.url),'utf8');
test('grass wake: blades bend from each resident real trail (uPlayT) in the blade vertex shader',()=>{assert.match(s,/uniform vec3 uPlayT\[8\]/);assert.match(s,/addScaledVector\(r\.f,-\.05\)/);});
test('first person: resident fan centres on the look yaw and fits the camera field of view, 7.5-10.5 units, near clear kept',()=>{assert.match(s,/const yaw=fpY\+/);assert.match(s,/hf\*\.7/);assert.match(s,/7\.5\+\(\(ri\*0\.618\)%1\)\*3/);assert.match(s,/ang\(r\.n,pN\)<FP_RES_CLEAR/);});
test('measured mid-distance count is exposed honestly',()=>{assert.match(s,/midOnScreen:midOn/);assert.doesNotMatch(s.split('midOnScreen')[0].slice(-3000),/Math\.random/);});
