import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const app=readFileSync(new URL('../public/spark/app.mjs',import.meta.url),'utf8');
const roll=app.slice(app.indexOf('function rollDraft'),app.indexOf('async function keepDraft')),keep=app.slice(app.indexOf('async function keepDraft'),app.indexOf('async function main'));
test('Surprise Me reroll is a pure draft: no storage, permissions, network or spending',()=>{
 assert.doesNotMatch(roll,/localStorage|withSparkLock|adopt\(|fetch\(|getUserMedia|bluetooth/);
 assert.match(roll,/personalRecipeLabel\(\)/);assert.match(roll,/buildGenome\(b,run,user,10\)/);
});
test('Create adopts exactly the previewed recipe once and keeps the nickname',()=>{
 assert.match(keep,/chosen=draft;draft=null;\$\('draft-keep'\)\.disabled=true/);
 assert.match(keep,/user:chosen\.user/);assert.match(keep,/current\.gen\.seed!==chosen\.gen\.seed/);assert.match(keep,/nameBeast\(next,nick\)/);
});
