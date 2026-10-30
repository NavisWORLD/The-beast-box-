import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const dock=readFileSync(new URL('../components/site-dock.tsx',import.meta.url),'utf8');
const css=readFileSync(new URL('../app/globals.css',import.meta.url),'utf8');
test('home keeps exactly one sound + one talk control, folding (not deleting) the rest',()=>{
 assert.match(dock,/data-home-sound/);assert.match(dock,/data-quick-talk/);
 assert.match(dock,/'Sound on'/);assert.match(dock,/'Sound off'/);assert.match(dock,/Talk to \{short\}/);
 assert.match(dock,/'Tap for sound'/,'never claims sound is on before the browser plays');
 assert.match(css,/data-dock-home\] :is\(\[data-zeref-voice-dock\],aside\[data-sound-room\],\[data-beast-chat-launcher\]/);
 for(const keep of ['data-quick-voice','data-quick-reachout','data-quick-music','data-zeref-voice-toggle'])assert.ok((dock+readFileSync(new URL('../components/zeref-voice-dock.tsx',import.meta.url),'utf8')).includes(keep),keep+' still exists');
 assert.doesNotMatch(dock,/Math\.random/);assert.doesNotMatch(dock,/\bAI\b/);
});
test('pocket card leaves the bubble middle; RECORDED label gap widened at desktop',()=>{
 assert.match(css,/\.cosmos-home-card\[open\]\{top:auto!important;bottom:2%/);
 assert.match(css,/min-width:601px\)\{[\s\S]*\[data-sand-source\]\{max-width:30%!important\}/);
});
