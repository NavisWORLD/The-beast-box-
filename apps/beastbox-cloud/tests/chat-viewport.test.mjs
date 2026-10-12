import test from 'node:test';
import assert from 'node:assert/strict';
import {chatViewport} from '../lib/companion/chat-viewport.mjs';
test('Safari visual viewport resize and pan keep panel above the keyboard',()=>{
 assert.deepEqual(chatViewport(844,{height:844,offsetTop:0}),{height:844,bottom:0});
 assert.deepEqual(chatViewport(844,{height:440,offsetTop:0}),{height:440,bottom:404});
 assert.deepEqual(chatViewport(844,{height:440,offsetTop:94}),{height:440,bottom:310});
 assert.deepEqual(chatViewport(844,{height:900,offsetTop:0}),{height:900,bottom:0});
});
test('unsupported viewport geometry uses the available layout and rejects invalid offsets',()=>{
 assert.deepEqual(chatViewport(700,null),{height:700,bottom:0});
 assert.deepEqual(chatViewport(700,{height:NaN,offsetTop:-30}),{height:700,bottom:0});
});
