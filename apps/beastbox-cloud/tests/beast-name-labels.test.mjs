import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {ZEREF_LINES,beastLine} from '../lib/universe/tiny-universe-view.mjs';
test('Emeth reaction lines use the active beast name and read exactly as before for Zeref',()=>{
 assert.equal(beastLine(ZEREF_LINES.supernova,'Zeref'),'A star let go. Zeref goes very still.');
 assert.equal(beastLine(ZEREF_LINES.storm,'Zeref'),'A storm. Zeref puffs up, then waits.');
 assert.equal(beastLine(ZEREF_LINES.abiogenesis,'Zeref'),'New life. Zeref\u2019s tail curls happy.');
 assert.equal(beastLine(ZEREF_LINES.supernova,'Yewling'),'A star let go. Yewling goes very still.');
 assert.equal(beastLine(ZEREF_LINES.storm,null),'A storm. Zeref puffs up, then waits.');});
test('the knowledge card heading takes the active beast name, with Zeref as the fallback; the default beast is untouched',()=>{
 const c=readFileSync(new URL('../components/zeref-knowledge-diagnostics.tsx',import.meta.url),'utf8');assert.match(c,/What \{beastName\} knows/);assert.match(c,/useActiveBeastName\(\)\|\|'Zeref'/);});
