import {blit,renderBeast,SPRITE} from './draw.mjs';
import {BODIES,buildGenome,bucketTraits} from './genome.mjs';
import {expandQvmReceipt,growthFromQvmBatch,scenarioRuns} from './qvm-growth.mjs';
import {bluetoothNote,connectMuse} from './muse.mjs';
import {serializeQbeast} from './qbeast.mjs';
import {PROFILES,simulateStable} from './signal.mjs';
import {Voice} from './voice.mjs';
import {getBeastAudio} from './shared/beast-audio-engine.mjs';
import {habitatPose} from './habitat.mjs';
import {QBEAST_KEY,SESSION_KEY,selectSpark,saveSparkSession,readSparkSession,replaySpark,withSparkLock} from './identity.mjs';
import {careAction,finishTraining,talk,shownName} from './shared/session.mjs';
const STORE='spark-beasts-bestiary-v1',QVM_STORE='spark-qvm-growth-v1',SOUND_KEY='spark-beast-sound-v2',SCALE=4,$=id=>document.getElementById(id);
const media=matchMedia('(prefers-reduced-motion: reduce)');
const beastAudio=getBeastAudio();
let reduceMotion=media.matches,runs=[],qvmRuns=[],byKey=new Map(),current=null,muse=null,voiceOn=false,soundWanted=true,voiceBus=null,stage=1,preview=false,drift=false,runtime=null,cache={},bestiary=[],session=null,busy=false,starterCache=[],qvmGrowth=0,lastViewportWidth=innerWidth;
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
function audioSceneFor(gen=current?.gen){
 if(!gen)return null;
 return {id:'spark-public',seedKey:gen.seed,element:gen.element||'spark',temperament:gen.temperament||'Curious',enabled:soundWanted};
}
function voiceOutput(){
 const output=beastAudio.output();if(!output)return null;
 if(!voiceBus||voiceBus.ctx!==output.ctx){
  const gain=output.ctx.createGain();gain.gain.value=.13;gain.connect(output.dest);voiceBus={ctx:output.ctx,gain};
 }
 return voiceBus;
}
function audioSfx(kind){
 if(!current||!soundWanted||!voiceOn)return false;
 return beastAudio.sfx(kind,{element:current.gen.element||'spark',seedKey:current.gen.seed});
}
function syncAudioUi(){
 const snap=beastAudio.getSnapshot(),music=$('music'),volume=$('music-volume'),state=$('audio-state');
 if(music){music.textContent=snap.musicOn?'♫ MUSIC ON':'♫ MUSIC OFF';music.setAttribute('aria-pressed',String(snap.musicOn));}
 if(volume&&document.activeElement!==volume)volume.value=String(Math.round(snap.volume*100));
 if(state)state.textContent=!soundWanted?'Muted on this device':voiceOn?(snap.musicOn?'Creature voice + procedural music active':'Creature voice active · music off'):'Wakes on your first tap · synthesized locally';
}
beastAudio.subscribe(syncAudioUi);
function readQvmGrowth(seed){try{const saved=JSON.parse(localStorage.getItem(QVM_STORE)||'{}');return saved.seed===seed?Math.max(0,Math.min(1,Number(saved.growth)||0)):0;}catch{return 0;}}
function saveQvmGrowth(){if(!current)return;try{localStorage.setItem(QVM_STORE,JSON.stringify({seed:current.gen.seed,growth:qvmGrowth,source_sha256:'7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599'}));}catch{}}
function updateQvmGrowth(){const label=$('qvm-growth'),bar=$('qvm-growth-bar');if(!label||!bar)return;const pct=Math.round(qvmGrowth*100);bar.style.width=`${pct}%`;label.textContent=`SIM GROWTH ${pct}% · browser-local · native stage unchanged`;label.parentElement?.setAttribute('aria-valuenow',String(pct));}
function updatePlate(){if(!current)return;const beast=session.beast;$('nameplate').textContent=shownName(beast);$('form').textContent=`${current.gen.names[stage]} · ${preview?'PREVIEW ':''}STAGE ${'I'.repeat(stage)}`;$('care-stats').textContent=`Care XP ${beast.xp} · Bond ${beast.bond} · Energy ${beast.energy}`;$('identity').textContent=`QBEAST ${beast.qbeast.profile.id}`;$('view').dataset.creatureId=beast.qbeast.profile.id;$('view').dataset.stage=String(stage);$(
'view').dataset.simGrowth=qvmGrowth.toFixed(3);for(const which of [1,2,3])$(`pick${which}`).setAttribute('aria-pressed',String(stage===which));updateQvmGrowth();}
function showCreature(entry,nextSession,spawn=true){
 const run=byKey.get(entry.run);if(!run)throw Error('Recorded seed is unavailable.');
 const gen=buildGenome(entry.traits,run,entry.user||null,10);current={entry,gen,run};session=nextSession;stage=session.beast.nativeStage||1;preview=false;
 cacheEyes(gen);showTraits(entry.traits);$('keeper').value=entry.user||'';
 $('meta').textContent=`${gen.temperament} · ${gen.element} · ${gen.body} · ${gen.island}`;
 $('quantum').textContent=`RECORDED QUANTUM SEED · ${run.backend} · ${run.counts_sha256.slice(0,12)}…`;
 $('provenance').textContent=`Job ${run.job_id} · pub ${run.pub_index} · ${run.num_bits}-bit · ${run.shots} recorded shots · counts SHA-256 ${run.counts_sha256}`;
 $('seed').textContent=gen.seed;for(const which of [1,2,3]){paintStage($(`st${which}`),gen,which);$(`nm${which}`).textContent=gen.names[which];}
 qvmGrowth=readQvmGrowth(gen.seed);
 const scene=audioSceneFor(gen);if(scene)beastAudio.setScene(scene);syncAudioUi();
 runtime={rnd:mulberry32(gen.behavior.prng_seed),T:0,nextBlink:2,blinkUntil:-1,utt:0,lastSay:-20,nextVoice:12,state:spawn?'spawn':'idle',until:spawn?1.2:0,spawn:spawn?0:1,qvmPulseUntil:-1,qvmStep:0};
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
function say(mood,text){
 if(!current||!runtime)return;
 const u=Voice.utterance(current.gen.voice,stage,mood,runtime.utt++,drive());
 $('bubble').hidden=false;$('bubble').textContent=u.text;$('line').textContent=text||({calm:'A quiet little moment.',focus:'Those eyes miss nothing.',spark:'Tiny paws. Big sparks.',neutral:'Ready to explore.'}[mood]);
 runtime.bubbleUntil=runtime.T+Math.max(2.4,u.dur+.8);runtime.lastSay=runtime.T;
 if(voiceOn){const out=voiceOutput();if(out)Voice.schedule(out.ctx,out.gain,out.ctx.currentTime+.03,current.gen.voice,u);}
}
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
 ctx.globalAlpha=Math.max(.08,spawn);ctx.translate(pose.x+128,pose.y+128);ctx.rotate(pose.rotation);const grown=pose.scale*(1+qvmGrowth*.22);ctx.scale(grown,grown);ctx.drawImage(cache[stage][eye],-128,-128);
 if(!reduceMotion&&runtime.T<runtime.qvmPulseUntil){const pulse=Math.max(0,Math.min(1,runtime.qvmPulseUntil-runtime.T));ctx.globalCompositeOperation='lighter';ctx.strokeStyle=`rgba(126,231,255,${.24+pulse*.34})`;ctx.lineWidth=2;for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(0,0,72+i*17+(1-pulse)*18,0,Math.PI*2);ctx.stroke();}for(let i=0;i<7;i++){const a=runtime.T*(1.8+i*.07)+i*.9,r=88+i*4;ctx.fillStyle=i%2?'#f3c15b':'#7ee7ff';ctx.fillRect(Math.cos(a)*r,Math.sin(a)*r,3,3);}}
 ctx.restore();
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
function starterEntries(){
 if(starterCache.length)return starterCache;
 const profiles=['serene','focused','sparky','balanced','dreamy','steady','restless','mock'];
 const pool=runs.filter(row=>row.num_bits>=2),candidates=[];
 for(const profile of profiles){const traits=(({focus,calm,spark})=>({focus,calm,spark}))(simulateStable(profile));for(const seedRun of pool){try{const entry={traits,run:seedRun.key,user:null},gen=buildGenome(traits,seedRun,null,10);candidates.push({entry,gen});}catch{}}}
 const picked=[],used=new Set(),bodies=new Set(),islands=new Set();
 const take=item=>{const key=JSON.stringify(item.entry);if(used.has(key))return false;used.add(key);picked.push(item.entry);bodies.add(item.gen.body);islands.add(item.gen.island);return true;};
 for(const item of candidates){if(!bodies.has(item.gen.body))take(item);if(bodies.size===BODIES.length)break;}
 for(const item of candidates){if(!islands.has(item.gen.island))take(item);if(islands.size>=8)break;}
 for(const item of candidates){if(picked.length>=18)break;take(item);}
 starterCache=picked;return starterCache;
}
function drawBestiary(){const grid=$('bestiary');grid.replaceChildren();const combined=[...bestiary,...starterEntries()],seen=new Set();for(const entry of combined){const key=JSON.stringify(entry);if(seen.has(key)||!byKey.has(entry.run))continue;seen.add(key);try{const gen=buildGenome(entry.traits,byKey.get(entry.run),entry.user||null,10),btn=document.createElement('button'),canvas=document.createElement('canvas'),label=document.createElement('span');btn.type='button';btn.className='beast-card';paintStage(canvas,gen,1);label.textContent=`${gen.names[1]} · ${gen.body} · ${gen.island}`;btn.append(canvas,label);btn.addEventListener('click',()=>void run(()=>adopt(entry)));grid.append(btn);if(seen.size>=24)break;}catch{}}}
function download(){if(!session?.beast)return;const text=serializeQbeast(session.beast.qbeast),url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=shownName(session.beast)+'.qbeast';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('status').textContent='Your existing QBEAST identity downloaded. Native evolution is earned in LOST COSMOS.';}
function readSoundWanted(){try{return localStorage.getItem(SOUND_KEY)!=='off';}catch{return true;}}
function saveSoundWanted(){try{localStorage.setItem(SOUND_KEY,soundWanted?'on':'off');}catch{}}
function updateVoiceButton(){
 const button=$('voice');if(!button)return;
 button.textContent=voiceOn?'🔊 SOUND ON':soundWanted?'🔊 SOUND READY':'🔇 SOUND OFF';
 button.setAttribute('aria-pressed',String(soundWanted));button.classList.toggle('on',soundWanted);syncAudioUi();
}
async function startVoice(announce=false){
 if(!soundWanted||voiceOn)return;
 beastAudio.sparkUnmute();beastAudio.unlock();const scene=audioSceneFor();if(scene)beastAudio.setScene(scene);
 const out=voiceOutput();if(!out)throw Error('This browser does not provide local WebAudio.');
 voiceOn=true;updateVoiceButton();if(announce){audioSfx('confirm');say('spark','Sound is on. Tiny beast noises and music are unlocked.');}
}
async function stopVoice(){
 voiceOn=false;
 try{if(voiceBus?.gain&&voiceBus?.ctx){const t=voiceBus.ctx.currentTime;voiceBus.gain.gain.cancelScheduledValues(t);voiceBus.gain.gain.setTargetAtTime(0,t,.015);setTimeout(()=>{try{voiceBus?.gain?.disconnect?.()}catch{}},120);}}catch{}
 voiceBus=null;beastAudio.sparkMute();updateVoiceButton();
}
async function enableVoice(){
 try{
  if(soundWanted){soundWanted=false;saveSoundWanted();await stopVoice();}
  else{soundWanted=true;saveSoundWanted();await startVoice(true);}
 }catch(e){voiceOn=false;updateVoiceButton();$('status').textContent=e.message;}
}
function unlockPreferredSound(event){
 if(!soundWanted||voiceOn)return;
 if(event?.target?.closest?.('#voice'))return;
 void startVoice(false).catch(e=>{$('status').textContent=e.message;});
}
function toggleMusic(){
 beastAudio.unlock();const snap=beastAudio.getSnapshot();beastAudio.setMusic(!snap.musicOn);audioSfx('blip');syncAudioUi();
}
function setMusicVolume(event){beastAudio.setVolume(Number(event.target.value)/100);syncAudioUi();}
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
function qvmScenarioForCurrent(){if(!current||!qvmRuns.length)return 1;return 1+(parseInt(current.gen.seed.slice(0,8),16)%8);}
async function processQvmBatch(row){
 if(!current||!runtime)throw Error('Spark a Beast before replaying the simulator.');
 const metrics=growthFromQvmBatch(row);qvmGrowth=Math.min(1,qvmGrowth+metrics.delta);saveQvmGrowth();runtime.qvmPulseUntil=runtime.T+1.35;runtime.state='celebrate';runtime.until=runtime.T+1.6;runtime.qvmStep++;
 updatePlate();say('spark',`Rigetti QVM simulator · scenario ${row.qvm.scenario} · ${row.qvm.phase} processed. Visual growth is now ${Math.round(qvmGrowth*100)}%.`);
 $('status').textContent=`Processed archived Azure-hosted Rigetti QVM simulator job ${row.job_id}. No QPU and no new cloud job was used.`;
 await new Promise(resolve=>setTimeout(resolve,620));
}
async function replayQvmScenario(){
 const scenario=qvmScenarioForCurrent(),rows=scenarioRuns(qvmRuns,scenario);if(rows.length!==3)throw Error('Pinned Rigetti QVM simulator scenario is unavailable.');
 for(const row of rows)await processQvmBatch(row);
 $('status').textContent=`Scenario ${scenario} complete: 3 archived Rigetti QVM simulator batches changed this Beast's browser-local growth and effects. Native LOST COSMOS stage is still earned only in the game.`;
}
function browserReact(kind){
 if(!current||!runtime)return;
 const copy={online:'Browser link is back. I can see this page is online.',offline:'Browser link went offline. I will stay local.',visible:'You came back to my browser habitat.',resize:'My browser habitat changed size. Scooting into the new space.'}[kind];
 if(!copy)return;runtime.state=kind==='offline'?'rest':'listen';runtime.until=runtime.T+2.2;say(kind==='offline'?'calm':'focus',copy);
}
function loop(prev){const now=performance.now();tick(Math.min(.05,(now-prev)/1000)||.016);requestAnimationFrame(()=>loop(now));}
async function main(){
 soundWanted=readSoundWanted();updateVoiceButton();
 $('btnote').textContent=bluetoothNote()||'';for(const key of Object.keys(PROFILES)){const opt=document.createElement('option');opt.value=opt.textContent=key;$('profile').append(opt)}$('profile').value='balanced';
 const [index,qvmReceipt]=await Promise.all([
  fetch('/spark/user-seeds-20261004.json').then(r=>r.json()),
  fetch('/spark/rigetti-qvm-sim.json').then(r=>r.ok?r.json():null).catch(()=>null)
 ]);
 const tables=await Promise.all(['/spark/runs.json',...(index.shards||[])].map(path=>fetch(path).then(r=>{if(!r.ok)throw Error('Recorded seed table unavailable.');return r.json()})));
 qvmRuns=qvmReceipt?expandQvmReceipt(qvmReceipt):[];
 const ibmRuns=tables.flatMap(t=>(t.runs||[]).map(expand));
 runs=[...new Map([...ibmRuns,...qvmRuns].map(r=>[r.key,r])).values()];byKey=new Map(runs.map(r=>[r.key,r]));starterCache=[];
 $('totals').textContent=`${ibmRuns.length} recorded IBM distributions · ${new Set(ibmRuns.map(r=>r.job_id)).size} IBM jobs · ${qvmRuns.length} archived Azure Rigetti QVM simulator batches.`;
 try{bestiary=JSON.parse(localStorage.getItem(STORE)||'[]')}catch{bestiary=[]}if(!Array.isArray(bestiary))bestiary=[];
 fillRunSelect(runs.filter(r=>r.num_bits>=2).slice(0,12));showTraits(simulateStable('balanced'));
 const raw=localStorage.getItem(QBEAST_KEY);
 if(raw){const active=replaySpark(JSON.parse(raw).text,byKey);const saved=await withSparkLock(()=>selectSpark(localStorage,active.gen));showCreature(active.entry,saved,false);}
 else await adopt(bestiary[0]&&byKey.has(bestiary[0].run)?bestiary[0]:starterEntries()[0]);
 window.addEventListener('pointerdown',unlockPreferredSound,{capture:true});window.addEventListener('keydown',unlockPreferredSound,{capture:true});
 $('generate').addEventListener('click',()=>void run(async()=>{surpriseRun();await spark()}));$('regenerate').addEventListener('click',()=>void run(()=>spark()));$('use-profile').addEventListener('click',()=>void run(async()=>{showTraits(simulateStable($('profile').value));await spark('profile')}));$('surprise').addEventListener('click',surpriseRun);$('q').addEventListener('input',searchRuns);$('download').addEventListener('click',download);$('voice').addEventListener('click',()=>void enableVoice());$('drift').addEventListener('click',()=>{drift=!drift;$('drift').classList.toggle('on',drift)});$('muse').addEventListener('click',()=>void museClick());$('stop-muse').addEventListener('click',()=>{muse?.stop();muse=null;$('status').textContent='Muse disconnected. Samples cleared.'});$('qvm-replay').addEventListener('click',()=>void run(()=>replayQvmScenario()));
 for(const k of ['focus','calm','spark'])$(k).addEventListener('input',()=>showTraits(readTraits()));for(const kind of ['pet','play','train','rest','care'])$(kind).addEventListener('click',()=>void run(()=>interaction(kind)));$('view').addEventListener('click',()=>void run(()=>interaction('pet')));$('talk').addEventListener('click',()=>{$('talk-form').hidden=!$('talk-form').hidden;if(!$('talk-form').hidden)$('talk-text').focus()});$('talk-form').addEventListener('submit',speak);
 for(const which of [1,2,3])$(`pick${which}`).addEventListener('click',()=>{stage=which;preview=stage!==session.beast.nativeStage;updatePlate();runtime.state='celebrate';runtime.until=runtime.T+1.5;$('status').textContent='Visual preview only. Your earned native stage and QBEAST progression did not change.'});
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&voiceOn)void audioCtx?.suspend();else{if(voiceOn)void audioCtx?.resume();browserReact('visible');}});
 window.addEventListener('online',()=>browserReact('online'));window.addEventListener('offline',()=>browserReact('offline'));
 let resizeTimer=0;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(Math.abs(innerWidth-lastViewportWidth)>=80){lastViewportWidth=innerWidth;browserReact('resize');}},220);});
 requestAnimationFrame(now=>loop(now));
}
main().catch(err=>{$('status').textContent=err.message||'Spark Beasts could not start.'});
