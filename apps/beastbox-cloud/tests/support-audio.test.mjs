import assert from 'node:assert/strict';
import test from 'node:test';
import './register-ts.mjs';
import { SUPPORT_TIERS } from '../lib/support-tiers.ts';
import { createBeastAudio } from '../lib/companion/beast-audio-engine.mjs';
import { createSupportAudio } from '../lib/support-audio.mjs';

function fixture() {
  const log = []; let made = 0, closed = 0;
  const param = () => {
    const p = {value:0,events:[]};
    for (const method of ['setValueAtTime','setTargetAtTime','cancelScheduledValues','exponentialRampToValueAtTime'])
      p[method] = (...args) => {p.events.push([method,...args]); return p;};
    return p;
  };
  const node = kind => {const n={kind,connect(){},disconnect(){this.disconnected=true;}}; log.push(n); return n;};
  const ctx = {currentTime:2,state:'running',destination:{},
    createGain(){return Object.assign(node('gain'),{gain:param()});},
    createDynamicsCompressor(){return Object.assign(node('compressor'),Object.fromEntries(['threshold','knee','ratio','attack','release'].map(k=>[k,param()])));},
    createOscillator(){return Object.assign(node('osc'),{frequency:param(),start(t){this.startAt=t;},stop(t){this.stopAt=t;}});},
    resume:async()=>{ctx.state='running';}, close(){closed++;},
  };
  const audio = createBeastAudio({createContext:()=>{made++;return ctx;}});
  let enabled = true;
  const player = createSupportAudio(audio,{enabled:()=>enabled});
  return {audio,player,ctx,log,made:()=>made,closed:()=>closed,mute:()=>{enabled=false;player.stop();}};
}

test('support is silent before a gesture and respects both local and site mute',async()=>{
  const f=fixture();
  assert.equal(await f.player.play(SUPPORT_TIERS[0].sound),false);
  assert.equal(f.made(),0);
  f.audio.unlock(); f.audio.sparkMute();
  assert.equal(await f.player.play(SUPPORT_TIERS[0].sound),false);
  f.audio.sparkUnmute(); f.mute();
  assert.equal(await f.player.play(SUPPORT_TIERS[0].sound),false);
  assert.equal(f.log.filter(n=>n.kind==='osc').length,0);
});

test('every tier schedules a distinct, short, quiet reaction on the shared bus',async()=>{
  const signatures=new Set();
  for(const tier of SUPPORT_TIERS){
    const f=fixture(); f.audio.unlock();
    assert.equal(await f.player.play(tier.sound),true);
    const osc=f.log.filter(n=>n.kind==='osc');
    assert.ok(osc.length>=2&&osc.length<=4);
    for(const n of osc) assert.ok(n.stopAt>n.startAt&&n.stopAt-f.ctx.currentTime<.75);
    signatures.add(JSON.stringify(osc.map(n=>[n.type,n.frequency.events,n.startAt,n.stopAt])));
    const peaks=f.log.filter(n=>n.kind==='gain').flatMap(n=>n.gain.events).filter(e=>e[0]==='exponentialRampToValueAtTime');
    assert.ok(peaks.every(e=>e[1]>0&&e[1]<=.026));
    assert.equal(f.made(),1); f.player.dispose(); assert.equal(f.closed(),0);
    assert.ok(osc.every(n=>n.disconnected));
  }
  assert.equal(signatures.size,8);
});

test('muting or disposal while Safari resumes cancels the pending chirp',async()=>{
  for(const action of ['mute','dispose']){
    const f=fixture(); f.audio.unlock(); f.ctx.state='suspended';
    let resolve; f.ctx.resume=()=>new Promise(r=>{resolve=r;});
    const pending=f.player.play(SUPPORT_TIERS[3].sound);
    if(action==='mute') f.mute(); else f.player.dispose();
    f.ctx.state='running'; resolve();
    assert.equal(await pending,false);
    assert.equal(f.log.filter(n=>n.kind==='osc').length,0);
  }
});

test('repeated taps stop previous voices, hidden pages stay silent and audio refusal is optional',async()=>{
  const f=fixture(); f.audio.unlock();
  await f.player.play(SUPPORT_TIERS[1].sound);
  const first=f.log.filter(n=>n.kind==='osc');
  await f.player.play(SUPPORT_TIERS[2].sound);
  assert.ok(first.every(n=>n.disconnected));
  f.audio.setHidden(true);
  assert.equal(await f.player.play(SUPPORT_TIERS[5].sound),false);
  f.audio.setHidden(false); f.ctx.createOscillator=()=>{throw Error('device unavailable');};
  assert.equal(await f.player.play(SUPPORT_TIERS[0].sound),false);
  f.player.dispose(); assert.equal(f.closed(),0);
});

test('a rejected native resume is handled without claiming sound played',async()=>{
  const f=fixture(); f.audio.unlock(); f.ctx.state='suspended';
  f.ctx.resume=async()=>{throw Error('browser declined audio');};
  assert.equal(await f.player.play(SUPPORT_TIERS[0].sound),false);
  assert.equal(f.log.filter(n=>n.kind==='osc').length,0);
  await new Promise(resolve=>setImmediate(resolve));
});
