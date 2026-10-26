import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('the privacy area is named "Privacy and info" everywhere it is linked, and /privacy still exists',()=>{
 const page=read('app/privacy/page.tsx');
 assert.match(page,/title: 'Privacy and info · Beast Box'/);assert.match(page,/PRIVACY AND INFO/);
 assert.match(read('lib/site-nav.ts'),/label:'Privacy and info',href:'\/privacy'/);
 assert.match(read('lib/world/world-map.mjs'),/\['\/privacy','workshop','Privacy and info'\]/);
 assert.match(read('components/world-menu.tsx'),/href="\/privacy"[^>]*>.*Privacy and info<\/a>/s);
 assert.match(read('app/page.tsx'),/href="\/privacy">Privacy and info/);
 assert.match(read('app/next/page.tsx'),/label:"Privacy and info",href:"\/privacy"/);
});
test('/privacy holds the long explanations under one heading, with honest label meanings',()=>{
 const p=read('app/privacy/page.tsx');
 assert.match(p,/What the labels mean and how your signals are used/);
 for(const w of ['RECORDED','SIMULATED','SEEDED','MEASURED'])assert.match(p,new RegExp('<strong>'+w+'</strong>'));
 for(const t of ['Your own beast has its own brain state','tilt the four sand wells in your pocket cage','the same seed gives the same weights','Stop sharing does not delete that packet','12D is a simulation','Audio, video and the pulse waveform never leave your phone',
  'The camera does one job at a time','one camera switch covers both','Stop sharing ends all reading right away and deletes the numbers saved for you','It is one tap, with no confirm step','Turning world signals on asks you to confirm first','Weather is not used','no page on this site shows them to other people','Nothing about your surroundings runs on quantum hardware'])assert.ok(p.includes(t),t);
 assert.doesNotMatch(p,/every object has a brain/i);assert.doesNotMatch(p,/Every creature has its own brain state|sky, light and creature moods|always gives the same result/);
 assert.ok(p.includes('RECORDED seeds are the real IBM run'));
});
