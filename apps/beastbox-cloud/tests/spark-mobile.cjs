/* Actual browser acceptance: public renderer, care, audio and shared identity. */
const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs/promises');
const root=process.argv[2]||'http://127.0.0.1:3000',out=process.argv[3]||'/tmp/sol-spark-mobile';
(async()=>{await fs.mkdir(out,{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.BEAST_BROWSER_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[],results=[];
const widths=process.argv[4]?[Number(process.argv[4])]:[430,390,375,320];
for(const width of widths){
 const context=await browser.newContext({viewport:{width,height:900},isMobile:true,hasTouch:true,deviceScaleFactor:1});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(`${width}: ${e.message}`));
 await page.addInitScript(()=>{window.__audioCount=0;window.__audioContexts=[];const AC=window.AudioContext;window.AudioContext=class extends AC{constructor(...args){super(...args);window.__audioCount++;window.__audioContexts.push(this)}};});
 await page.goto(root+'/spark/index.html');await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,{timeout:30000});
 assert.equal(await page.evaluate(()=>window.__audioCount),0,'browser must stay silent before the first user gesture');
 assert.equal(await page.locator('#voice').getAttribute('aria-pressed'),'true');assert.match(await page.locator('#voice').textContent(),/SOUND READY/);
 const before=await page.locator('#view').screenshot();await page.waitForTimeout(1600);const after=await page.locator('#view').screenshot();assert.ok(!before.equals(after),'creature must animate');
 await page.locator('#generate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Spawned'));
 await page.waitForFunction(()=>document.querySelector('#voice').textContent.includes('SOUND ON'));assert.equal(await page.evaluate(()=>window.__audioCount),1,'first gesture unlocks default-on sound');assert.equal(await page.evaluate(()=>window.__audioContexts[0].state),'running');
 const identity=await page.evaluate(()=>JSON.parse(JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1')).text));
 await page.locator('#pet').click();await page.waitForFunction(()=>document.querySelector('#care-stats').textContent.includes('XP 4'));
 await page.locator('#rest').click();await page.waitForFunction(()=>document.querySelector('#view').dataset.state==='rest');
 await page.locator('#talk').click();await page.locator('#talk-text').fill('Hello little beast');await page.locator('#talk-form button').click();await page.waitForFunction(()=>document.querySelector('#talk-reply').textContent.length>0);
 await page.locator('#voice').click();await page.waitForFunction(()=>document.querySelector('#voice').getAttribute('aria-pressed')==='false');await page.waitForFunction(()=>document.querySelector('#audio-state').textContent.includes('Muted'));assert.equal(await page.evaluate(()=>window.__audioCount),1,'mute reuses the one shared audio context');
 await page.locator('#voice').click();await page.waitForFunction(()=>document.querySelector('#voice').textContent.includes('SOUND ON'));assert.equal(await page.locator('#voice').getAttribute('aria-pressed'),'true');assert.equal(await page.evaluate(()=>window.__audioCount),1,'unmute does not create a second audio context');
 await page.locator('#music').click();await page.waitForFunction(()=>document.querySelector('#music').textContent.includes('MUSIC OFF'));await page.locator('#music').click();await page.waitForFunction(()=>document.querySelector('#music').textContent.includes('MUSIC ON'));
 await page.locator('#music-volume').evaluate(el=>{el.value='35';el.dispatchEvent(new Event('input',{bubbles:true}));});
 if(width===390){
  await page.evaluate(async()=>{
   const sourceContext=new AudioContext();await sourceContext.resume();
   const oscillator=sourceContext.createOscillator(),gain=sourceContext.createGain(),destination=sourceContext.createMediaStreamDestination();
   oscillator.frequency.value=440;gain.gain.value=.72;oscillator.connect(gain).connect(destination);oscillator.start();
   window.__sparkMicFixture={sourceContext,oscillator,stream:destination.stream};
   const media=navigator.mediaDevices||{};
   if(!navigator.mediaDevices)Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:media});
   Object.defineProperty(media,'getUserMedia',{configurable:true,value:async()=>destination.stream});
  });
  await page.locator('#mic-react').click();
  await page.waitForFunction(()=>document.querySelector('#mic-react')?.getAttribute('aria-pressed')==='true');
  await page.waitForFunction(()=>Number(document.querySelector('#view')?.dataset.micLevel||0)>.05);
  await page.waitForFunction(()=>document.querySelector('#view')?.dataset.state==='listen');
  await page.locator('#mic-react').click();
  await page.waitForFunction(()=>document.querySelector('#mic-react')?.getAttribute('aria-pressed')==='false');
  assert.equal(await page.evaluate(()=>window.__sparkMicFixture.stream.getAudioTracks()[0].readyState),'ended','turning mic reaction off stops the captured track');
  await page.evaluate(async()=>{try{window.__sparkMicFixture.oscillator.stop()}catch{};await window.__sparkMicFixture.sourceContext.close();Object.defineProperty(navigator.mediaDevices,'getUserMedia',{configurable:true,value:async()=>{throw new DOMException('Denied by fixture','NotAllowedError')}});});
  await page.locator('#mic-react').click();
  await page.waitForFunction(()=>document.querySelector('#status')?.textContent.includes('permission was not granted'));
  assert.equal(await page.locator('#mic-react').getAttribute('aria-pressed'),'false','denied microphone permission leaves the Beast usable and mic off');
 }
 await page.locator('.stage-wrap > details summary').click();
 const stages=[];for(const s of [1,2,3]){await page.locator('#pick'+s).click();stages.push((await page.locator('#view').screenshot()).toString('base64'));}assert.equal(new Set(stages).size,3);
 const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));assert.equal(saved.beast.stage,1);assert.equal(saved.beast.qbeast.profile.id,identity.profile.id);assert.deepEqual(saved.beast.qbeast,identity);
 await page.locator('#run').waitFor({state:'visible'});await page.locator('#run').evaluate((el,key)=>{if(!Array.from(el.options).some(o=>o.value===key)){const o=document.createElement('option');o.value=key;o.textContent=key;el.append(o);}el.value=key;},saved.beast.genome.inputs.quantum_run);
 await page.locator('#regenerate').click();await page.waitForTimeout(200);assert.equal(await page.locator('#view').getAttribute('data-creature-id'),identity.profile.id,'regeneration retains deterministic identity');
 const layout=await page.evaluate(()=>({body:document.documentElement.scrollWidth,w:innerWidth,view:document.querySelector('#view').getBoundingClientRect().toJSON(),buttons:[...document.querySelectorAll('.interactions button,#voice,#music,#mic-react,#generate,#lost-cosmos,.mobile-nav button,.mobile-nav a')].map(el=>el.getBoundingClientRect().toJSON())}));assert.ok(layout.body<=width,`overflow at ${width}: ${layout.body}`);assert.ok(layout.view.width>230);for(const b of layout.buttons)assert.ok(b.x>=0&&b.right<=width);
 await page.locator('[data-jump="#seed-lab"]').first().click();await page.waitForFunction(()=>location.hash==='#seed-lab');await page.locator('[data-jump="#habitat"]').first().click();await page.waitForFunction(()=>location.hash==='#habitat');
 await page.screenshot({path:out+`/spark-${width}.png`,fullPage:true});
 console.log('Width',width,'public interaction passed');await page.goto(root+'/beast-cage');await page.waitForFunction(id=>document.querySelector('[data-spark-beast][data-creature-id="'+id+'"]'),identity.profile.id,{timeout:30000});
 await page.waitForFunction(name=>{const dock=document.querySelector('[data-lost-cosmos-dock]');return dock?.dataset.dockState==='native'&&dock.getAttribute('aria-label')==='Lost Cosmos cartridge connected to '+name;},saved.beast.displayName);
 const player=page.locator('[data-lost-cosmos-player-shell]');
 assert.equal(await player.getAttribute('data-player-mode'),'minimized');
 await player.getByRole('link',{name:'OPEN GAME',exact:true}).click();await page.waitForURL(root+'/sol-game');
 await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='normal');
 await player.getByRole('button',{name:'MINIMIZE',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='minimized');
 await player.getByRole('link',{name:'OPEN GAME',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('[data-lost-cosmos-player-shell]')?.dataset.playerMode==='normal');
 assert.equal(await player.getAttribute('data-creature-id'),identity.profile.id,'opening and restoring the unstarted player keeps the same Beast');
 console.log('Width',width,'cage passed');await page.goto(root+'/beast-cage/play');await page.waitForFunction(()=>document.querySelector('canvas'));
 console.log('Width',width,'adventure passed');await page.goto(root+'/beast-cage/guest');await page.waitForFunction(()=>document.querySelector('[data-creature-id]'));
 console.log('Width',width,'guest passed');await page.goto(root+'/sol-game');await page.waitForFunction(id=>document.querySelector('[data-spark-player]')?.dataset.creatureId===id,identity.profile.id);
 const talkPanel=page.locator('[data-lost-cosmos-player-shell] [data-spark-game-talk]');
 await talkPanel.getByRole('button',{name:/^TALK TO /}).click();
 await talkPanel.getByRole('textbox').fill('Hello from the cartridge');
 const talkLayout=await talkPanel.evaluate(el=>({right:el.getBoundingClientRect().right,inputs:[...el.querySelectorAll('button,textarea')].map(b=>b.getBoundingClientRect().toJSON()),body:document.documentElement.scrollWidth}));
 assert.ok(talkLayout.body<=width&&talkLayout.right<=width,`game talk overflow at ${width}`);
 for(const b of talkLayout.inputs)assert.ok(b.x>=0&&b.right<=width);
 await page.screenshot({path:out+`/game-talk-${width}.png`,fullPage:true});
 await talkPanel.getByRole('button',{name:'CLOSE TALK',exact:true}).click();
 console.log('Width',width,'native entry passed');await page.goto(root+'/spark/index.html');await page.waitForFunction(id=>document.querySelector('#view')?.dataset.creatureId===id,identity.profile.id);assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.xp),saved.beast.xp);
 await page.reload();await page.waitForFunction(id=>document.querySelector('#view')?.dataset.creatureId===id,identity.profile.id);assert.equal(await page.evaluate(()=>window.__audioCount),0,'sound stays browser-policy silent until a new gesture after reopen');assert.match(await page.locator('#voice').textContent(),/SOUND READY/);
 await page.locator('#generate').click();await page.waitForFunction(id=>document.querySelector('#view').dataset.creatureId!==id,identity.profile.id);await page.waitForFunction(()=>document.querySelector('#voice').textContent.includes('SOUND ON'));assert.equal(await page.evaluate(()=>window.__audioCount),1);
 if(width===390){
  const voice=await page.evaluate(async previous=>{
   const {Voice}=await import('/spark/voice.mjs');
   const current=JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.genome;
   async function render(gen,stage,mood){
    const ac=new OfflineAudioContext(1,44100*3,44100),out=Voice.master(ac);out.gain.value=.13;
    const u=Voice.utterance(gen.voice,stage,mood,0,{focus:.6,calm:.7,spark:.8});Voice.schedule(ac,out,0,gen.voice,u);
    const data=(await ac.startRendering()).getChannelData(0),bytes=new Uint8Array(data.buffer);
    const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
    let peak=0,sum=0;for(const v of data){peak=Math.max(peak,Math.abs(v));sum+=v*v;}
    return {hash,peak,rms:Math.sqrt(sum/data.length),utterance:JSON.stringify(u),data};
   }
   const first=await render(previous,1,'spark'),again=await render(previous,1,'spark'),calm=await render(previous,3,'calm'),other=await render(current,1,'spark');
   let maxDifference=0;for(let i=0;i<first.data.length;i++)maxDifference=Math.max(maxDifference,Math.abs(first.data[i]-again.data[i]));
   for(const v of [first,again,calm,other])delete v.data;
   return {first,again,calm,other,maxDifference};
  },saved.beast.genome);
  assert.equal(voice.first.utterance,voice.again.utterance,'same genome produces the exact generated voice phrase');
  // Browser DSP can round parallel filters differently; compare actual samples.
  assert.ok(voice.maxDifference<.00001,`repeat waveform differs by ${voice.maxDifference}`);
  assert.notEqual(voice.first.hash,voice.calm.hash,'stage and mood vary the voice');assert.notEqual(voice.first.hash,voice.other.hash,'new beast has a different voice');
  for(const v of [voice.first,voice.again,voice.calm,voice.other]){assert.ok(v.peak>0&&v.peak<.8);assert.ok(v.rms>0);}
  await fs.writeFile(out+'/voice-report.json',JSON.stringify(voice,null,2));
 }
 assert.equal(await page.locator('a:has-text("Play in Living Universe")').count(),0);results.push({width,identity:identity.profile.id,careXP:saved.beast.xp,audio:'default-on/first-gesture-unlock/persistent-mute',navigation:'same QBEAST',overflow:false});await context.close();
}
const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await context.newPage();
page.on('pageerror',e=>errors.push(e.message));await page.goto(root+'/spark/index.html');await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
await page.waitForFunction(()=>document.querySelector('#view').dataset.state==='idle');
const stamp=()=>{const c=document.querySelector('#view');return [...c.getContext('2d').getImageData(0,0,c.width,c.height).data].reduce((h,v)=>Math.imul(h^v,16777619)>>>0,2166136261);};
const before=await page.evaluate(stamp);await page.waitForTimeout(1500);assert.equal(await page.evaluate(stamp),before,'reduced motion keeps rendered idle still');
await context.close();await browser.close();assert.deepEqual(errors,[]);await fs.writeFile(out+'/report.json',JSON.stringify({results,reducedMotion:true,consoleErrors:errors},null,2));console.log('PASS: real mobile Chromium, all four widths, care, talk, stage previews, gesture sound, deterministic QBEAST and navigation continuity');})().catch(e=>{console.error(e);process.exit(1)});
