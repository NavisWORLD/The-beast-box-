import test from 'node:test';
import assert from 'node:assert/strict';
import {createPlayerDisplay} from '../lib/companion/player-display.mjs';

function setup() {
 const doc=new EventTarget();doc.fullscreenEnabled=true;doc.fullscreenElement=null;
 const states=[],releases=[];let requests=0,exits=0;
 const shell={requestFullscreen:async()=>{requests++;doc.fullscreenElement=shell;doc.dispatchEvent(new Event('fullscreenchange'));}};
 doc.exitFullscreen=async()=>{exits++;doc.fullscreenElement=null;doc.dispatchEvent(new Event('fullscreenchange'));};
 const display=createPlayerDisplay({document:doc,shell,changed:next=>states.push(next),release:()=>releases.push('released')});
 return {doc,shell,states,releases,display,requests:()=>requests,exits:()=>exits};
}
test('fullscreen targets the player and browser Escape restores normal UI',async()=>{
 const t=setup();await t.display.expand();assert.equal(t.doc.fullscreenElement,t.shell);assert.equal(t.display.mode,'fullscreen');
 t.doc.fullscreenElement=null;t.doc.dispatchEvent(new Event('fullscreenchange'));
 assert.equal(t.display.mode,'normal');assert.deepEqual(t.states,['fullscreen','normal']);assert.ok(t.releases.length>=2);t.display.dispose();
});
test('minimize exits actual fullscreen and restore returns the same surface',async()=>{
 const t=setup();await t.display.expand();await t.display.minimize();assert.equal(t.display.mode,'minimized');assert.equal(t.doc.fullscreenElement,null);assert.equal(t.exits(),1);
 await t.display.restore();assert.equal(t.display.mode,'normal');assert.equal(t.requests(),1,'restore does not request a new fullscreen player');t.display.dispose();
});
test('rejected or unavailable element fullscreen uses immersive without claiming fullscreen',async()=>{
 for(const request of [undefined,async()=>{throw Error('browser denied');},async()=>{}]){
  const t=setup();t.shell.requestFullscreen=request;await t.display.expand();assert.equal(t.display.mode,'immersive');assert.equal(t.doc.fullscreenElement,null);
  await t.display.normal();assert.equal(t.display.mode,'normal');t.display.dispose();
 }
});
test('fullscreenchange from another element never marks this player fullscreen',()=>{
 const t=setup();t.doc.fullscreenElement={};t.doc.dispatchEvent(new Event('fullscreenchange'));assert.equal(t.display.mode,'normal');t.display.dispose();
});
test('a late fullscreen grant cannot resurrect a minimized player',async()=>{
 const t=setup();let grant;t.shell.requestFullscreen=()=>new Promise(resolve=>{grant=()=>{t.doc.fullscreenElement=t.shell;t.doc.dispatchEvent(new Event('fullscreenchange'));resolve();};});
 const pending=t.display.expand();await t.display.minimize();grant();await pending;
 assert.equal(t.doc.fullscreenElement,null);assert.equal(t.display.mode,'minimized');assert.equal(t.exits(),1);t.display.dispose();
});
test('a refused fullscreen exit keeps UI truthful and permits a later retry',async()=>{
 const t=setup();await t.display.expand();t.doc.exitFullscreen=async()=>{throw Error('not yet');};await t.display.minimize();assert.equal(t.display.mode,'fullscreen');
 t.doc.fullscreenElement=null;t.doc.dispatchEvent(new Event('fullscreenchange'));assert.equal(t.display.mode,'minimized');t.display.dispose();
});
test('an older failed expand never exits a newer successful fullscreen',async()=>{
 const t=setup();let fail;t.shell.requestFullscreen=()=>new Promise((resolve,reject)=>{fail=reject;});
 const old=t.display.expand();t.shell.requestFullscreen=async()=>{t.doc.fullscreenElement=t.shell;t.doc.dispatchEvent(new Event('fullscreenchange'));};
 await t.display.expand();fail(Error('older request failed'));await old;
 assert.equal(t.display.mode,'fullscreen');assert.equal(t.doc.fullscreenElement,t.shell);assert.equal(t.exits(),0);t.display.dispose();
});
test('an older minimize completion never overwrites a newer restore intent',async()=>{
 const t=setup();await t.display.expand();let finish;t.doc.exitFullscreen=()=>new Promise(resolve=>{finish=()=>{t.doc.fullscreenElement=null;t.doc.dispatchEvent(new Event('fullscreenchange'));resolve();};});
 const old=t.display.minimize();t.doc.exitFullscreen=async()=>{t.doc.fullscreenElement=null;t.doc.dispatchEvent(new Event('fullscreenchange'));};await t.display.restore();finish();await old;
 assert.equal(t.display.mode,'normal');t.display.dispose();
});
