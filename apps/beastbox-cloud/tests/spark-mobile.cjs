/* Actual browser acceptance: public renderer, care, audio and shared identity. */
const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs/promises');
const root=process.argv[2]||'http://127.0.0.1:3000',out=process.argv[3]||'/tmp/sol-spark-mobile';
(async()=>{await fs.mkdir(out,{recursive:true});const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[],results=[];
const widths=process.argv[4]?[Number(process.argv[4])]:[430,390,375,320];
for(const width of widths){
 const context=await browser.newContext({viewport:{width,height:900},isMobile:true,hasTouch:true,deviceScaleFactor:1});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(`${width}: ${e.message}`));
 await page.addInitScript(()=>{window.__audioCount=0;window.__audioContexts=[];const AC=window.AudioContext;window.AudioContext=class extends AC{constructor(...args){super(...args);window.__audioCount++;window.__audioContexts.push(this)}};});
 await page.goto(root+'/spark/index.html');await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId,{timeout:30000});
 assert.equal(await page.evaluate(()=>window.__audioCount),0);
 const before=await page.locator('#view').screenshot();await page.waitForTimeout(1600);const after=await page.locator('#view').screenshot();assert.ok(!before.equals(after),'creature must animate');
 await page.locator('#generate').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Spawned'));
 const identity=await page.evaluate(()=>JSON.parse(JSON.parse(localStorage.getItem('beastbox-quantum-beast-public-v1')).text));
 await page.locator('#pet').click();await page.waitForFunction(()=>document.querySelector('#care-stats').textContent.includes('XP 4'));
 await page.locator('#rest').click();await page.waitForFunction(()=>document.querySelector('#view').dataset.state==='rest');
 await page.locator('#talk').click();await page.locator('#talk-text').fill('Hello little beast');await page.locator('#talk-form button').click();await page.waitForFunction(()=>document.querySelector('#talk-reply').textContent.length>0);
 await page.locator('#voice').click();await page.waitForFunction(()=>document.querySelector('#voice').getAttribute('aria-pressed')==='true');assert.equal(await page.evaluate(()=>window.__audioContexts[0].state),'running');
 await page.locator('#voice').click();await page.waitForFunction(()=>window.__audioContexts[0].state==='closed');
 await page.locator('.stage-wrap > details summary').click();
 const stages=[];for(const s of [1,2,3]){await page.locator('#pick'+s).click();stages.push((await page.locator('#view').screenshot()).toString('base64'));}assert.equal(new Set(stages).size,3);
 const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')));assert.equal(saved.beast.stage,1);assert.equal(saved.beast.qbeast.profile.id,identity.profile.id);assert.deepEqual(saved.beast.qbeast,identity);
 await page.locator('.recipe summary').click();await page.locator('#run').evaluate((el,key)=>{if(!Array.from(el.options).some(o=>o.value===key)){const o=document.createElement('option');o.value=key;o.textContent=key;el.append(o);}el.value=key;},saved.beast.genome.inputs.quantum_run);
 await page.locator('#regenerate').click();await page.waitForTimeout(200);assert.equal(await page.locator('#view').getAttribute('data-creature-id'),identity.profile.id,'regeneration retains deterministic identity');
 const layout=await page.evaluate(()=>({body:document.documentElement.scrollWidth,w:innerWidth,view:document.querySelector('#view').getBoundingClientRect().toJSON(),buttons:[...document.querySelectorAll('.interactions button,#voice,#generate,#lost-cosmos')].map(el=>el.getBoundingClientRect().toJSON())}));assert.ok(layout.body<=width,`overflow at ${width}: ${layout.body}`);assert.ok(layout.view.width>230);for(const b of layout.buttons)assert.ok(b.x>=0&&b.right<=width);
 await page.screenshot({path:out+`/spark-${width}.png`,fullPage:true});
 console.log('Width',width,'public interaction passed');await page.goto(root+'/beast-cage');await page.waitForFunction(id=>document.querySelector('[data-spark-beast][data-creature-id="'+id+'"]'),identity.profile.id,{timeout:30000});
 await page.getByRole('button',{name:'Close Lost Cosmos player',exact:true}).click();await page.getByRole('button',{name:'Open Lost Cosmos player',exact:true}).click();
 console.log('Width',width,'cage passed');await page.goto(root+'/beast-cage/play');await page.waitForFunction(()=>document.querySelector('canvas'));
 console.log('Width',width,'adventure passed');await page.goto(root+'/beast-cage/guest');await page.waitForFunction(()=>document.querySelector('[data-creature-id]'));
 console.log('Width',width,'guest passed');await page.goto(root+'/sol-game');await page.waitForFunction(id=>document.querySelector('[data-spark-player]')?.dataset.creatureId===id,identity.profile.id);
 console.log('Width',width,'native entry passed');await page.goto(root+'/spark/index.html');await page.waitForFunction(id=>document.querySelector('#view')?.dataset.creatureId===id,identity.profile.id);assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('beastbox-companion-session-v1')).beast.xp),saved.beast.xp);
 await page.reload();await page.waitForFunction(id=>document.querySelector('#view')?.dataset.creatureId===id,identity.profile.id);assert.equal(await page.evaluate(()=>window.__audioCount),0,'sound never autoplays after reopen');
 await page.locator('#generate').click();await page.waitForFunction(id=>document.querySelector('#view').dataset.creatureId!==id,identity.profile.id);
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
    return {hash,peak,rms:Math.sqrt(sum/data.length)};
   }
   return {first:await render(previous,1,'spark'),again:await render(previous,1,'spark'),calm:await render(previous,3,'calm'),other:await render(current,1,'spark')};
  },saved.beast.genome);
  assert.equal(voice.first.hash,voice.again.hash,'same genome produces deterministic audio');assert.notEqual(voice.first.hash,voice.calm.hash,'stage and mood vary the voice');assert.notEqual(voice.first.hash,voice.other.hash,'new beast has a different voice');
  for(const v of Object.values(voice)){assert.ok(v.peak>0&&v.peak<.8);assert.ok(v.rms>0);}
  await fs.writeFile(out+'/voice-report.json',JSON.stringify(voice,null,2));
 }
 assert.equal(await page.locator('a:has-text("Play in Living Universe")').count(),0);results.push({width,identity:identity.profile.id,careXP:saved.beast.xp,audio:'gesture-on/closed-off',navigation:'same QBEAST',overflow:false});await context.close();
}
const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await context.newPage();
page.on('pageerror',e=>errors.push(e.message));await page.goto(root+'/spark/index.html');await page.waitForFunction(()=>document.querySelector('#view')?.dataset.creatureId);
await page.waitForFunction(()=>document.querySelector('#view').dataset.state==='idle');
const stamp=()=>{const c=document.querySelector('#view');return [...c.getContext('2d').getImageData(0,0,c.width,c.height).data].reduce((h,v)=>Math.imul(h^v,16777619)>>>0,2166136261);};
const before=await page.evaluate(stamp);await page.waitForTimeout(1500);assert.equal(await page.evaluate(stamp),before,'reduced motion keeps rendered idle still');
await context.close();await browser.close();assert.deepEqual(errors,[]);await fs.writeFile(out+'/report.json',JSON.stringify({results,reducedMotion:true,consoleErrors:errors},null,2));console.log('PASS: real mobile Chromium, all four widths, care, talk, stage previews, gesture sound, deterministic QBEAST and navigation continuity');})().catch(e=>{console.error(e);process.exit(1)});
