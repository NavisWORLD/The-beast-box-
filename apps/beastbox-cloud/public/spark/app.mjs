import {blit,renderBeast,SPRITE} from './draw.mjs';
import {buildGenome,bucketTraits} from './genome.mjs';
import {bluetoothNote,connectMuse} from './muse.mjs';
import {serializeQbeast} from './qbeast.mjs';
import {PROFILES,simulateStable} from './signal.mjs';
import {Voice} from './voice.mjs';
import {habitatPose} from './habitat.mjs';
import {QBEAST_KEY,SESSION_KEY,selectSpark,saveSparkSession,readSparkSession,replaySpark,withSparkLock} from './identity.mjs';
import {careAction,finishTraining,talk,shownName} from './shared/session.mjs';
import {catalogForms} from './roster.mjs';
const STORE='spark-beasts-bestiary-v1',SCALE=4,$=id=>document.getElementById(id);
const media=matchMedia('(prefers-reduced-motion: reduce)');
let reduceMotion=media.matches,runs=[],byKey=new Map(),current=null,muse=null,voiceOn=false,audioCtx=null,audioOut=null,stage=1,preview=false,drift=false,runtime=null,cache={},bestiary=[],session=null,busy=false;
const target={focus:30,calm:30,spark:20},felt={...target};
media.addEventListener('change',()=>{reduceMotion=media.matches});
function expand(row){return {key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts:Object.fromEntries(row.c.split(',').map(part=>{const [k,v]=part.split(':');return [k,Number(v)]})),counts_sha256:row.h};}
function mulberry32(a){return ()=>{a|=0;a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t=(t+Math.imul(t^(t>>>7),61|t))^t;return ((t^(t>>>14))>>>0)/4294967296};}
function readTraits(){return Object.fromEntries(['focus','calm','spark'].map(k=>[k,Number($(k).value)]));}
function showTraits(traits){for(const k of ['focus','calm','spark']){$(k).value=traits[k];$(`v${k}`).textContent=String(traits[k]);target[k]=traits[k];}const b=bucketTraits(traits,10);$('bucket').textContent=`Seed bucket 10 · focus ${b.focus} / calm ${b.calm} / spark ${b.spark}`;}
function fillRunSelect(list){const sel=$('run');sel.replaceChildren(...list.map(run=>{const opt=document.createElement('option');opt.value=run.key;opt.textContent=`${run.key} · ${run.num_bits}-bit`;return opt}));}
function selectedRun(){return byKey.get($('run').value)||runs[0];}
function searchRuns(){const q=$('q').value.trim().toLowerCase(),list=runs.filter(r=>r.key.toLowerCase().includes(q)).slice(0,40);fillRunSelect(list.length?list:runs.slice(0,12));}
function surpriseRun(){const a=new Uint32Array(1);crypto.getRandomValues(a);const run=runs[a[0]%runs.length];fillRunSelect([run,...runs.slice(0,8).filter(r=>r.key!==run.key)]);$('run').value=run.key;}
function paintStage(canvas,gen,which,eye='open'){canvas.width=SPRITE*2;canvas.height=SPRITE*2;blit(canvas.getContext('2d'),renderBeast(gen,which,eye),0,0,2);}
function cacheEyes(gen){
 cache={};
 for(const which of [1,2,3]){
  cache[which]={};const open=renderBeast(gen,which,'open');
  let left=63,right=0,top=63,bottom=0;
  for(let y=0;y<64;y++)for(let x=0;x<64;x++)if(open[(y*64+x)*4+3]){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}
  const width=right-left+1,height=bottom-top+1,scale=Math.max(1,Math.floor(226/Math.max(width,height)));
  for(const eye of ['open','sleepy','closed','sparkle']){
   const source=document.createElement('canvas');source.width=source.height=64;
   blit(source.getContext('2d'),renderBeast(gen,which,eye),0,0,1);
   const c=document.createElement('canvas');c.width=c.height=256;
   const ctx=c.getContext('2d');ctx.imageSmoothingEnabled=false;
   ctx.drawImage(source,left,top,width,height,(256-width*scale)/2,(256-height*scale)/2,width*scale,height*scale);
   cache[which][eye]=c;
  }
 }
}
function updatePlate(){if(!current)return;const beast=session.beast;$('nameplate').textContent=shownName(beast);$('form').textContent=`${current.gen.names[stage]} · ${preview?'PREVIEW ':''}STAGE ${'I'.repeat(stage)}`;$('care-stats').textContent=`Care XP ${beast.xp} · Bond ${beast.bond} · Energy ${beast.energy}`;$('identity').textContent=`QBEAST ${beast.qbeast.profile.id}`;$('view').dataset.creatureId=beast.qbeast.profile.id;$('view').dataset.stage=String(stage);for(const which of [1,2,3])$(`pick${which}`).setAttribute('aria-pressed',String(stage===which));}
function showCreature(entry,nextSession,spawn=true){
 const run=byKey.get(entry.run);if(!run)throw Error('Recorded seed is unavailable.');
 const gen=buildGenome(entry.traits,run,entry.user||null,10);current={entry,gen,run};session=nextSession;stage=session.beast.nativeStage||1;preview=false;
 cacheEyes(gen);showTraits(entry.traits);$('keeper').value=entry.user||'';
 $('meta').textContent=`${gen.temperament} · ${gen.element} · ${gen.body} · ${gen.island}`;
 $('quantum').textContent=`RECORDED QUANTUM SEED · ${run.backend} · ${run.counts_sha256.slice(0,12)}…`;
 $('provenance').textContent=`Job ${run.job_id} · pub ${run.pub_index} · ${run.num_bits}-bit · ${run.shots} recorded shots · counts SHA-256 ${run.counts_sha256}`;
 $('seed').textContent=gen.seed;for(const which of [1,2,3]){paintStage($(`st${which}`),gen,which);$(`nm${which}`).textContent=gen.names[which];}
 runtime={rnd:mulberry32(gen.behavior.prng_seed),T:0,nextBlink:2,blinkUntil:-1,utt:0,lastSay:-20,nextVoice:12,state:spawn?'spawn':'idle',until:spawn?1.2:0,spawn:spawn?0:1};
 Object.assign(felt,target);updatePlate();drawBestiary();say('neutral',spawn?`${shownName(session.beast)} just sparked in. Let's explore!`:`${shownName(session.beast)} is back. Same paws, same seed.`);
}
async function adopt(entry,spawn=true){const gen=buildGenome(entry.traits,byKey.get(entry.run),entry.user||null,10);const next=await withSparkLock(()=>selectSpark(localStorage,gen));showCreature(entry,next,spawn);}
function drive(){
 const be=current.gen.behavior;
 return Object.fromEntries(['focus','calm','spark'].map(key=>{
  const excess=Math.max(0,Math.min(1,(felt[key]-be.thresholds[key])/(100-be.thresholds[key])));
  return [key,(.3*felt[key]/100+.7*excess)*be.sensitivity[key]];
 }));
}
function say(mood,text){if(!current||!runtime)return;const u=Voice.utterance(current.gen.voice,stage,mood,runtime.utt++,drive());$('bubble').hidden=false;$('bubble').textContent=u.text;$('line').textContent=text||({calm:'A quiet little moment.',focus:'Those eyes miss nothing.',spark:'Tiny paws. Big sparks.',neutral:'Ready to explore.'}[mood]);runtime.bubbleUntil=runtime.T+Math.max(2.4,u.dur+.8);runtime.lastSay=runtime.T;if(voiceOn&&audioCtx?.state==='running'&&audioOut)Voice.schedule(audioCtx,audioOut,audioCtx.currentTime+.03,current.gen.voice,u);}
function tick(dt){
 if(!current||!runtime||document.hidden)return;runtime.T+=dt;const be=current.gen.behavior;
 if(drift&&!reduceMotion){const values={};for(const k of ['focus','calm','spark'])values[k]=Math.round(Math.max(0,Math.min(100,target[k]+Math.sin(runtime.T*.3+k.length)*8*dt)));showTraits(values);}
 const kf=1-Math.exp(-dt/be.latency_s);for(const k of ['focus','calm','spark'])felt[k]+=(target[k]-felt[k])*kf;
 const drv=drive();let mood='neutral',best=.25;for(const k of ['focus','calm','spark'])if(drv[k]>best){best=drv[k];mood=k;}
 if(runtime.state!=='idle'&&runtime.T>runtime.until)runtime.state='idle';
 if(runtime.state==='idle'&&session.beast.energy<30){runtime.state='rest';runtime.until=runtime.T+8;}
 if(runtime.state==='rest')mood='calm';else if(runtime.state==='celebrate'||runtime.state==='spawn')mood='spark';else if(runtime.state==='train'||runtime.state==='listen')mood='focus';
 if(runtime.T>=runtime.nextVoice){runtime.nextVoice=runtime.T+12+runtime.rnd()*16;if(voiceOn&&runtime.T-runtime.lastSay>6)say(mood);}
 let eye='open';if(runtime.T>runtime.nextBlink){runtime.blinkUntil=runtime.T+.14;runtime.nextBlink=runtime.T+be.blink_mean_s*(.7+runtime.rnd());}
 if(runtime.state==='rest')eye='closed';else if(!reduceMotion&&runtime.T<runtime.blinkUntil)eye='closed';else if(mood==='calm')eye='sleepy';else if(mood==='spark')eye='sparkle';
 if(runtime.T>runtime.bubbleUntil)$('bubble').hidden=true;
 const pose=habitatPose(current.gen,runtime.T,runtime.state,reduceMotion),canvas=$('view'),ctx=canvas.getContext('2d');
 ctx.clearRect(0,0,canvas.width,canvas.height);ctx.imageSmoothingEnabled=false;ctx.save();
 const spawn=runtime.state==='spawn'&&!reduceMotion?Math.min(1,runtime.T/1.2):1;
 ctx.globalAlpha=Math.max(.08,spawn);ctx.translate(pose.x+128,pose.y+128);ctx.rotate(pose.rotation);ctx.scale(pose.scale,pose.scale);ctx.drawImage(cache[stage][eye],-128,-128);ctx.restore();
 canvas.dataset.x=pose.x.toFixed(2);canvas.dataset.y=pose.y.toFixed(2);canvas.dataset.gait=be.gait;canvas.dataset.state=runtime.state;
 $('mood').textContent=`${runtime.state==='idle'?(pose.pause?'looking around':mood):runtime.state} · ${be.gait}`;
 if(training){const phase=((performance.now()-training.start)/900)%1;$('train-mark').style.left=`${phase*100}%`;}
}
async function run(work){if(busy)return;busy=true;try{await work()}catch(e){$('status').textContent=e.message||'Could not save this Beast.'}finally{busy=false}}
async function spark(from='sliders'){
 const traits=from==='profile'?simulateStable($('profile').value):bucketTraits(readTraits(),10),user=$('keeper').value.trim();
 if(user&&!/^[A-Za-z0-9 ._-]{1,24}$/.test(user))throw Error('Keeper label must be 1–24 public characters.');
 const entry={traits:{focus:traits.focus,calm:traits.calm,spark:traits.spark},run:selectedRun().key,user:user||null};
 await adopt(entry);
 bestiary=[entry,...bestiary.filter(item=>JSON.stringify(item)!==JSON.stringify(entry))].slice(0,24);localStorage.setItem(STORE,JSON.stringify(bestiary));drawBestiary();$('status').textContent='Spawned and saved on this device. The same QBEAST is ready for Beast Box and LOST COSMOS.';
}
function starterEntries(){const profiles=['serene','focused','sparky','balanced','dreamy','steady','restless','mock'];const keys=['ibm_marrakesh:d93d8pgoamcc73dc3afg','ibm_kingston:d93jnlq47v0s73823aj0','ibm_fez:da55afc3jnrc73agsvv0#pub1','ibm_fez:da55afc3jnrc73agsvv0#pub2'].filter(k=>byKey.has(k));return profiles.map((p,i)=>({traits:(({focus,calm,spark})=>({focus,calm,spark}))(simulateStable(p)),run:keys[i%keys.length]||runs[0].key,user:null}));}
function makeCatalogCard({entry,gen,stage:which,name,body,island,rare,label}){const btn=document.createElement('button'),canvas=document.createElement('canvas'),title=document.createElement('strong'),meta=document.createElement('span');btn.type='button';btn.className='beast-card'+(rare?' rare':'');btn.dataset.catalogStage=String(which);paintStage(canvas,gen,which);title.textContent=name;meta.textContent=`${label||body} · Stage ${'I'.repeat(which)} · ${island}`;btn.append(canvas,title,meta);btn.addEventListener('click',()=>void run(async()=>{await adopt(entry);stage=which;preview=which!==session.beast.nativeStage;updatePlate();runtime.state='celebrate';runtime.until=runtime.T+1.5;$('status').textContent=preview?'Catalog preview selected. Earn evolution in LOST COSMOS to make this stage native.':'This Beast is now active.';}));return btn;}
function drawBestiary(){const saved=$('bestiary'),catalog=$('catalog');saved.replaceChildren();catalog.replaceChildren();if(bestiary.length){for(const entry of bestiary){if(!byKey.has(entry.run))continue;try{const gen=buildGenome(entry.traits,byKey.get(entry.run),entry.user||null,10),btn=document.createElement('button'),canvas=document.createElement('canvas'),title=document.createElement('strong'),meta=document.createElement('span');btn.type='button';btn.className='beast-card saved';paintStage(canvas,gen,1);title.textContent=gen.names[1];meta.textContent=`Saved · ${gen.island}`;btn.append(canvas,title,meta);btn.addEventListener('click',()=>void run(()=>adopt(entry)));saved.append(btn);}catch{}}}else{const note=document.createElement('p');note.className='hint empty-bestiary';note.textContent='No extra saved Beasts yet. Pick any catalog creature below or generate a new one.';saved.append(note);}
 for(const item of catalogForms(byKey))catalog.append(makeCatalogCard(item));
 $('catalog-count').textContent=`${catalog.children.length} core / rare forms · 11 body families · Charlet · 12 rares`;
}
function download(){if(!session?.beast)return;const text=serializeQbeast(session.beast.qbeast),url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=shownName(session.beast)+'.qbeast';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent='Your existing QBEAST identity downloaded. Native evolution is earned in LOST COSMOS.';}
async function enableVoice(){
 try{
  if(voiceOn){voiceOn=false;if(audioOut)audioOut.gain.setValueAtTime(0,audioCtx.currentTime);await audioCtx?.close();audioCtx=null;audioOut=null;}
  else{const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw Error('This browser does not provide local WebAudio.');audioCtx=new AC();audioOut=Voice.master(audioCtx);audioOut.gain.value=.13;await audioCtx.resume();if(audioCtx.state!=='running')throw Error('Tap Sound again to unlock audio.');voiceOn=true;say('spark','That is my own generated voice.');}
  $('voice').textContent=voiceOn?'🔊 SOUND ON':'🔇 SOUND OFF';$('voice').setAttribute('aria-pressed',String(voiceOn));$('voice').classList.toggle('on',voiceOn);
 }catch(e){voiceOn=false;$('status').textContent=e.message;}
}
let training=null;
async function interaction(kind){
 await withSparkLock(()=>{const latest=readSparkSession(localStorage);if(latest.beast?.seed!==current.gen.seed)throw Error('Another page selected a different Beast. Reload to continue.');session=latest;
  if(kind==='train'){
   if(!training)training={start:performance.now(),round:0,hits:0};
   const phase=((performance.now()-training.start)/900)%1;training.hits+=phase>.35&&phase<.65?1:0;training.round++;
   if(training.round>=6){const result=finishTraining(session,training.hits,6);$('status').textContent=`Training complete · ${training.hits}/6 hits · +${result.gain} care XP. Cartridge evolution is earned in the game.`;training=null;$('train').textContent='TRAIN';$('training').hidden=true;}
   else{$('training').hidden=false;$('train').textContent=`TAP ${training.round}/6`;}
  }else careAction(session,kind==='play'?'spark':kind==='care'?'feed':kind);
  saveSparkSession(localStorage,session);
 });
 runtime.state=kind==='rest'?'rest':kind==='train'?'train':'celebrate';runtime.until=runtime.T+(kind==='rest'?12:2.6);updatePlate();say(kind==='rest'?'calm':kind==='train'?'focus':'spark',kind==='rest'?'Curling up for a little rest.':kind==='pet'?'A soft pat. We are getting closer.':kind==='care'?'A snack and a little care.':kind==='train'?'Tap in the bright window. Six tries!':'Catch the spark!');
}
async function speak(event){event.preventDefault();const text=$('talk-text').value.trim();if(!text)return;await run(async()=>{let reply;await withSparkLock(()=>{session=readSparkSession(localStorage);if(session.beast?.seed!==current.gen.seed)throw Error('Reload the current Beast before talking.');reply=talk(session,text).reply;saveSparkSession(localStorage,session)});runtime.state='listen';runtime.until=runtime.T+3;updatePlate();say('focus',reply);$('talk-reply').textContent=reply;$('talk-text').value='';});}
async function museClick(){if(!$('consent').checked){$('status').textContent='Check consent before connecting your headband.';return}try{muse?.stop();muse=await connectMuse(traits=>{showTraits(traits);$('status').textContent='Derived traits updated locally. Raw samples discarded.'});$('status').textContent=`Connected to ${muse.name}. Derived AF7 traits stay here.`;}catch(e){$('status').textContent=e.message||'Muse connection cancelled.'}}
function loop(prev){const now=performance.now();tick(Math.min(.05,(now-prev)/1000)||.016);requestAnimationFrame(()=>loop(now));}
async function main(){
 $('btnote').textContent=bluetoothNote()||'';for(const key of Object.keys(PROFILES)){const opt=document.createElement('option');opt.value=opt.textContent=key;$('profile').append(opt)}$('profile').value='balanced';
 const index=await fetch('/spark/user-seeds-20261004.json').then(r=>r.json()),tables=await Promise.all(['/spark/runs.json',...(index.shards||[])].map(path=>fetch(path).then(r=>{if(!r.ok)throw Error('Recorded seed table unavailable.');return r.json()})));
 runs=[...new Map(tables.flatMap(t=>(t.runs||[]).map(expand)).map(r=>[r.key,r])).values()];byKey=new Map(runs.map(r=>[r.key,r]));$('totals').textContent=`${runs.length} recorded distributions · ${new Set(runs.map(r=>r.job_id)).size} IBM jobs · ${index.totals?.unique_jobs||0} new public jobs added.`;
 try{bestiary=JSON.parse(localStorage.getItem(STORE)||'[]')}catch{bestiary=[]}if(!Array.isArray(bestiary))bestiary=[];
 fillRunSelect(runs.filter(r=>r.num_bits>=2).slice(0,12));showTraits(simulateStable('balanced'));
 const raw=localStorage.getItem(QBEAST_KEY);
 if(raw){const active=replaySpark(JSON.parse(raw).text,byKey);const saved=await withSparkLock(()=>selectSpark(localStorage,active.gen));showCreature(active.entry,saved,false);}
 else await adopt(bestiary[0]&&byKey.has(bestiary[0].run)?bestiary[0]:starterEntries()[0]);
 $('generate').addEventListener('click',()=>void run(async()=>{surpriseRun();await spark()}));$('regenerate').addEventListener('click',()=>void run(()=>spark()));$('use-profile').addEventListener('click',()=>void run(async()=>{showTraits(simulateStable($('profile').value));await spark('profile')}));$('surprise').addEventListener('click',surpriseRun);$('q').addEventListener('input',searchRuns);$('download').addEventListener('click',download);$('voice').addEventListener('click',()=>void enableVoice());$('drift').addEventListener('click',()=>{drift=!drift;$('drift').classList.toggle('on',drift)});$('muse').addEventListener('click',()=>void museClick());$('stop-muse').addEventListener('click',()=>{muse?.stop();muse=null;$('status').textContent='Muse disconnected. Samples cleared.'});
 for(const k of ['focus','calm','spark'])$(k).addEventListener('input',()=>showTraits(readTraits()));for(const kind of ['pet','play','train','rest','care'])$(kind).addEventListener('click',()=>void run(()=>interaction(kind)));$('view').addEventListener('click',()=>void run(()=>interaction('pet')));$('talk').addEventListener('click',()=>{$('talk-form').hidden=!$('talk-form').hidden;if(!$('talk-form').hidden)$('talk-text').focus()});$('talk-form').addEventListener('submit',speak);
 for(const which of [1,2,3])$(`pick${which}`).addEventListener('click',()=>{stage=which;preview=stage!==session.beast.nativeStage;updatePlate();runtime.state='celebrate';runtime.until=runtime.T+1.5;$('status').textContent='Visual preview only. Your earned native stage and QBEAST progression did not change.'});
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&voiceOn)void audioCtx?.suspend();else if(voiceOn)void audioCtx?.resume()});
 requestAnimationFrame(now=>loop(now));
}
main().catch(err=>{$('status').textContent=err.message||'Spark Beasts could not start.'});
