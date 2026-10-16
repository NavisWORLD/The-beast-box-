import test from 'node:test';import assert from 'node:assert/strict';
import {voiceProfile,speakableText,canReachOut,recordReachOut,defaultPrefs,armOnFirstTap,reachOutPrompt,MIN_GAP_MS,IDLE_MS} from '../lib/companion/seeded-voice.mjs';
test('voice is deterministic per seed and differs across seeds',()=>{
 assert.deepEqual(voiceProfile('bb-deada969'),voiceProfile('bb-deada969'));
 assert.notDeepEqual(voiceProfile('bb-deada969'),voiceProfile('bb-1234'));
 const p=voiceProfile('bb-deada969',{dominant:'fear'});assert.equal(p.emotion,'fear');assert.ok(p.pitch>=.1&&p.rate>=.5);
});
test('teacher text is never speakable',()=>{
 assert.equal(speakableText({role:'beast',text:'hi',teacher:{text:'x'}}),'');
 assert.equal(speakableText({role:'you',text:'hi'}),'');
 assert.equal(speakableText({role:'beast',text:' Dog. '}),'Dog.');
});
test('reach-out is rate limited and needs idle + toggle',()=>{
 let p=armOnFirstTap(defaultPrefs());assert.equal(p.voice,true);
 const now=10e6;assert.equal(canReachOut(p,now,now-1000).ok,false);
 assert.equal(canReachOut(p,now,now-IDLE_MS-1).ok,true);
 p=recordReachOut(p,now);assert.equal(canReachOut(p,now+MIN_GAP_MS-1,0).ok,false);
 assert.equal(canReachOut(p,now+MIN_GAP_MS+1,0).ok,true);
 assert.equal(canReachOut({...p,reachOut:false},now+1e7,0).ok,false);
 assert.match(reachOutPrompt({place:'Echo Prism',mood:'curious'}),/Echo Prism/);
});
