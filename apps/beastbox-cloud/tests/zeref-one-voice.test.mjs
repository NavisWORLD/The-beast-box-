import test from 'node:test';import assert from 'node:assert/strict';
import {chooseOneVoice} from '../lib/zeref/one-voice.mjs';
import {worldContextLine} from '../lib/zeref/world-context.mjs';
test('ties and missing drafts go to the gated mind',()=>{
 assert.equal(chooseOneVoice('Keeper: hi\nZeref:',{reply:'hello there friend'},{reply:'hello there friend'}).chosen,'gated');
 assert.equal(chooseOneVoice('Keeper: hi',{reply:'hello there friend'},null).chosen,'gated');
 assert.equal(chooseOneVoice('Keeper: hi',null,{reply:'hey hey you'}).chosen,'growing');
});
test('on-topic non-looping draft wins, deterministically',()=>{
 const p='Keeper: tell me about the ocean waves\nZeref:';
 const a=chooseOneVoice(p,{reply:'I am so happy! I am so happy! I am so happy!'},{reply:'The ocean waves roll under my moon.'});
 assert.equal(a.chosen,'growing');assert.deepEqual(a,chooseOneVoice(p,{reply:'I am so happy! I am so happy! I am so happy!'},{reply:'The ocean waves roll under my moon.'}));
});
test('world line is labelled and leaves absent feeds out',()=>{
 assert.equal(worldContextLine(null,null),'');
 const l=worldContextLine({links:{liveTick:{state:'STALE',signals:{energy:5}}}},{recent:[{tick:9,place:'Echo Prism',mood:'content'},{tick:3,place:'Tidewell'}]});
 assert.match(l,/Echo Prism \(RECORDED diary\)/);assert.match(l,/content \(SIMULATED\)/);assert.doesNotMatch(l,/energy/);
});
