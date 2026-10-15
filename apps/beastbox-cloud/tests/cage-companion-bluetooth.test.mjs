import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../components/beast-adventure.tsx',import.meta.url),'utf8');
test('Muse errors go to a sensor note, never the chat label',()=>{
 assert.doesNotMatch(src,/setLabel\(error instanceof Error \? error\.message : 'Muse/);
 assert.match(src,/setSensorNote\(error instanceof Error/);
 assert.match(src,/disabled=\{bluetooth === false\}/);
});
test('trail names the existing companion instead of "meet a spark beast"',()=>{
 assert.match(src,/companion\?\.name \? `\$\{companion\.name\} is your companion/);
});
