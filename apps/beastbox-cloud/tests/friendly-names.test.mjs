import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {starName,planetName,ageWords} from '../lib/universe/friendly-names.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('raw ids become friendly names and never leak the id',()=>{
 assert.equal(starName('star-1'),'Star 1');assert.equal(planetName('star-1-p2'),'Planet 2 of Star 1');
 assert.equal(planetName('star-1-p1',{home:'star-1-p1'}),'your home world');assert.equal(planetName('star-2-p3',{hearth:'star-2-p3'}),'Hearth');
 assert.equal(planetName('weird'),'a planet');assert.equal(starName(null),'a star');assert.equal(ageWords(12),'age 12 moments');assert.equal(ageWords('x'),'age 0 moments');
});
test('players never see star-N ids, "age N ticks" or the bb- id in the chat headers',()=>{
 const u=read('components/tiny-universe-view.tsx');assert.doesNotMatch(u,/age \{st\.age\} ticks|\{st\.id\}<br|Beast Box home cage|entangled with/);
 assert.match(u,/starName\(st\.id\)/);assert.match(u,/RECORDED IBM E/);
 assert.doesNotMatch(read('components/beast-chat-overlay.tsx'),/<small>\{session\?\.beast\?\.qbeast\?\.profile\.id\|\|profile\?\.id\|\|/);
 assert.match(read('components/beast-talk-panel.tsx'),/data-chat-qbeast="bb-deada969"/);
 assert.doesNotMatch(read('components/living-world.tsx'),/Visiting \{visit\.id\}/);
});
