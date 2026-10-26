import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/sol-spark-player.tsx',import.meta.url),'utf8');
test('the "Tap START LOST COSMOS" poster is really tappable once the beast is verified, and uses the same start path as the button',()=>{
 assert.match(src,/function startGame\(\)\{if\(starting\|\|!admitted\|\|running\)return;setStarting\(true\);setNote\('Starting Lost COSMOS…'\);post\(\{type:'sol-spark-start'\}\);\}/);
 assert.match(src,/role=\{admitted\?'button':'note'\}/);assert.match(src,/data-preboot-start/);assert.match(src,/onClick=\{admitted\?startGame:undefined\}/);
 assert.match(src,/e\.key==='Enter'\|\|e\.key===' '/);assert.match(src,/pointerEvents:'auto'/);
 assert.match(src,/onClick=\{startGame\}>\{starting\?'STARTING…'/);// the START button uses it too
 assert.equal((src.match(/post\(\{type:'sol-spark-start'\}\)/g)||[]).length,1);// one start path
});
test('a cartridge page that never answers shows an honest message and a real retry (no endless "Loading the cartridge…")',()=>{
 assert.match(src,/setTimeout\(\(\)=>setStalled\(true\),20000\)/);
 assert.match(src,/The cartridge did not answer/);assert.match(src,/data-rom-retry/);assert.match(src,/TRY AGAIN/);
 assert.match(src,/function retryLoad\(\)\{sent\.current=false;setStalled\(false\);setAdmitted\(false\);/);assert.match(src,/setFrameKey\(k=>k\+1\)/);
 assert.match(src,/<iframe key=\{frameKey\}/);
 assert.match(src,/Nothing is lost\. Try loading it again\./);
 assert.doesNotMatch(src,/Math\.random/);
});
test('the ROM itself is untouched: still the same /api/gba-rom route and the "original ROM, unchanged" line',()=>{assert.match(src,/original ROM, unchanged/);assert.doesNotMatch(src,/api\/gba-rom.*(patch|modify)/);});
