/**
 * ZEREF // MOONWRAITH — the home + support Beast's deterministic "mind".
 *
 * Honest boundary: nothing here is a live quantum measurement. Zeref's
 * temperament is derived from RECORDED IBM hardware counts that already ship
 * with the site (/spark/ibm-moonwraith-cassette-kit-20261010.json, job
 * db4te7slf4us73c3888g on ibm_marrakesh), validated against their published
 * SHA-256 digests, plus the beast's care stats and real interactions (taps,
 * pointer, idle time, time of day). Same seed + same inputs = same behaviour.
 *
 * Pure module: no DOM, no storage writes, no network. The renderer calls
 * stepMind() from requestAnimationFrame and frameFor() to pose the SVG rig.
 */
import {expandRun} from '../../public/spark/runs.mjs';
import {canonicalJson} from '../../public/spark/genome.mjs';
import {sha256Hex} from '../../public/spark/sha.mjs';

/** Verbatim copy of the shipped recorded shard rows. A test pins it to the public file. */
export const ZEREF_RECORDED_SOURCE=Object.freeze({
 path:'/spark/ibm-moonwraith-cassette-kit-20261010.json',
 alias:'Moonwraith-Cassette-Kit',
 source_class:'RECORDED_IBM_HARDWARE',
 backend:'ibm_marrakesh',
 job_id:'db4te7slf4us73c3888g',
 rows:Object.freeze([
  Object.freeze({k:'db4te7slf4us73c3888g:bell-zz',b:'ibm_marrakesh',j:'db4te7slf4us73c3888g',p:0,n:2,s:4096,c:'00:128,01:1918,10:1907,11:143',h:'b6a607eaa2c280862deb047fda827de36324d84dd2f7ac369d810d4551cabe56'}),
  Object.freeze({k:'db4te7slf4us73c3888g:bell-xx',b:'ibm_marrakesh',j:'db4te7slf4us73c3888g',p:1,n:2,s:4096,c:'00:2093,01:31,10:34,11:1938',h:'8389f40a5b10e2caadfd7336ea9597bd06879c07ce4f35bdc88d5d517e2030c4'})
 ])
});

/** Zeref's display profile from Cory's card + sprite atlas. Display defaults, not a saved QBEAST. */
export const ZEREF_PROFILE=Object.freeze({
 id:'bb-7f9c2a03',name:'Zeref',title:'Moonwraith',
 tagline:'A fragment of the void, a companion across realities.',
 stats:Object.freeze({energy:90,signal:78,memory:62,resonance:95}),
 statsSource:"Zeref's profile (sprite-atlas display stats)"
});

export const BEHAVIORS=Object.freeze(['idle','blink','pounce','walk','hover','curious','charge','sleep']);
export const REACTIONS=Object.freeze(['happy','startled','purr']);
export const LOCOMOTION=Object.freeze(['pounce','walk','hover','charge']);
const MOOD={idle:'content',blink:'affectionate',pounce:'playful',walk:'exploring',hover:'floaty',curious:'curious',charge:'charged up',sleep:'sleepy',happy:'happy',startled:'startled',purr:'purring'};
const LINES={
 idle:'*soft moon-purr* I\u2019m right here.',blink:'*slow blink* \u2026that means I like you.',pounce:'Pounce! Got the stardust!',
 walk:'Patrolling my little universe\u2026',hover:'Wings on. Floating between realities.',curious:'Hm? What\u2019s that you\u2019re doing?',
 charge:'Resonance rising\u2026 the crescent is glowing!',sleep:'zzz\u2026 dreaming of moons\u2026',
 happy:'Hehe! Again, again!',startled:'Eep! You surprised me!',purr:'Prrrr\u2026 that\u2019s the good spot.'
};

const clamp=(v,lo=0,hi=1)=>Math.min(hi,Math.max(lo,v));
const num=(v,d)=>Number.isFinite(Number(v))?Number(v):d;

/** Validate the recorded rows (digest-checked by expandRun) and derive seed + count features. */
export function recordedSeed(source=ZEREF_RECORDED_SOURCE){
 const runs=source.rows.map(row=>expandRun(row));
 const material=canonicalJson(runs.map(r=>({backend:r.backend,job_id:r.job_id,key:r.key,pub_index:r.pub_index,counts:r.counts})));
 const digest=sha256Hex(material);
 const even=r=>((r.counts['00']||0)+(r.counts['11']||0))/r.shots;
 const zz=runs.find(r=>/bell-zz$/.test(r.key)),xx=runs.find(r=>/bell-xx$/.test(r.key));
 const byte=i=>parseInt(digest.slice(i*2,i*2+2),16)/255;
 // Bell pubs: zz should be anti-correlated (odd parity), xx correlated (even parity).
 const zzOdd=zz?1-even(zz):byte(0),xxEven=xx?even(xx):byte(1);
 const lean=zz?((zz.counts['01']||0)-(zz.counts['10']||0))/Math.max(1,(zz.counts['01']||0)+(zz.counts['10']||0)):byte(2)-.5;
 return {digest,runs:runs.length,shots:runs.reduce((s,r)=>s+r.shots,0),backend:runs[0]?.backend||'',job_id:runs[0]?.job_id||'',
  features:{zzOdd,xxEven,lean,noise:clamp(1-(zzOdd+xxEven)/2)}};
}

function hash32(text){let h=0x811c9dc5;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}
/** mulberry32 on serialisable mind state. */
export function nextRandom(m){m.rng=(m.rng+0x6D2B79F5)|0;let t=m.rng;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;}

/** Personality = recorded-count features + stats + seeded draws. Stable for a given beast. */
export function temperamentFor(profile=ZEREF_PROFILE,seed=recordedSeed()){
 const s={rng:(parseInt(seed.digest.slice(0,8),16)^hash32(String(profile.id)))|0};
 const st=profile.stats||{},f=seed.features;
 const energy=num(st.energy,60)/100,signal=num(st.signal,50)/100,memory=num(st.memory,50)/100,resonance=num(st.resonance,50)/100;
 return {
  playfulness:clamp(.3+energy*.45+nextRandom(s)*.25),
  curiosity:clamp(.25+signal*.5+nextRandom(s)*.25),
  affection:clamp(.2+memory*.35+f.zzOdd*.25+nextRandom(s)*.2),
  radiance:clamp(resonance),
  steadiness:clamp(.35+f.xxEven*.45+nextRandom(s)*.2),
  sleepiness:clamp(.2+f.noise*2.5+nextRandom(s)*.25),
  blinkEvery:2.4+nextRandom(s)*2.8,
  lean:f.lean>=0?1:-1,
  rng:s.rng
 };
}

const NEUTRAL={open:.92,lower:.1,pupil:1,brow:0,smile:1,grin:0,o:0,frown:0,sleepy:0,blush:.25,glow:.35};
const EXPR={
 idle:{},
 blink:{smile:1,lower:.25,blush:.45},
 pounce:{open:1,lower:0,pupil:1.3,brow:.4,smile:0,grin:1,blush:.3,glow:.55},
 walk:{open:.95,brow:.1,smile:.6,grin:.4,blush:.2},
 hover:{open:1,pupil:1.15,brow:.5,smile:0,grin:.7,o:.3,glow:.65},
 curious:{open:1,lower:0,pupil:1.35,brow:.9,smile:0,o:1,glow:.4},
 charge:{open:.62,lower:.15,pupil:.8,brow:-.8,smile:0,grin:.55,frown:.45,glow:1},
 sleep:{open:0,lower:0,pupil:1,brow:-.1,smile:0,sleepy:1,blush:.2,glow:.2},
 happy:{open:0,lower:1,pupil:1.1,brow:.5,smile:0,grin:1,blush:1,glow:.6},
 startled:{open:1,lower:0,pupil:.62,brow:1,smile:0,o:1,blush:.1,glow:.5},
 purr:{open:0,lower:.8,brow:.2,smile:1,blush:.9,glow:.45}
};
const MOUTHS=['smile','grin','o','frown','sleepy'];

export function createMind({profile=ZEREF_PROFILE,source=ZEREF_RECORDED_SOURCE,care={},reduced=false,hour=12}={}){
 const seed=recordedSeed(source);
 const traits=temperamentFor(profile,seed);
 const st=profile.stats||{};
 const m={
  profileId:String(profile.id),name:String(profile.name||'Zeref'),digest:seed.digest,seed,traits,
  rng:traits.rng,t:0,reduced:Boolean(reduced),hour:num(hour,12),
  energy:clamp(num(care.energy,num(st.energy,70)),0,100),bond:clamp(num(care.bond,0),0,100),
  resonance:clamp(num(st.resonance,50),0,100),
  behavior:'idle',behaviorStart:0,behaviorEnd:1.5,lastAction:'idle',walkDir:1,wakeAt:80,
  reaction:null,reactionStart:0,reactionEnd:0,
  nextBlink:1.2,blinkStart:-9,
  gaze:{x:0,y:0},gazeTarget:{x:0,y:0},nextSaccade:.8,
  pointer:{x:0,y:0,lastMove:-99},lastPresence:0,taps:[],face:1,
  expr:{...NEUTRAL},history:['idle']
 };
 if(m.energy<22)startBehavior(m,'sleep');
 if(m.reduced)snapExpression(m);
 return m;
}

function durationFor(m,b){
 const r=nextRandom(m),slow=.75+m.traits.steadiness*.5;
 switch(b){
  case 'idle':return(1.6+r*2.8)*slow;
  case 'blink':return 1.7;
  case 'pounce':return 1.7;
  case 'walk':return 3.2+r*2;
  case 'hover':return 2.6+r*1.6;
  case 'curious':return 2.4+r*1.8;
  case 'charge':return 2.3+r*.9;
  case 'sleep':return 9+r*6;
  default:return 2;
 }
}
function startBehavior(m,b){
 m.behavior=b;m.behaviorStart=m.t;m.behaviorEnd=m.t+durationFor(m,b);
 if(b==='walk')m.walkDir=nextRandom(m)<.5?-1:1;
 if(b==='sleep')m.wakeAt=72+nextRandom(m)*20;
 if(b!=='idle')m.lastAction=b;
 m.history.push(b);if(m.history.length>40)m.history.shift();
}

/** Seeded, state-weighted choice of the next ambient behaviour. */
export function behaviorWeights(m){
 const T=m.traits,e=m.energy/100,night=m.hour>=22||m.hour<6;
 const idleFor=m.t-m.lastPresence,recentPointer=m.t-m.pointer.lastMove<2.5;
 const w={
  idle:0,
  blink:.5+T.affection*.8+m.bond/100,
  pounce:T.playfulness*1.9*e*e,
  walk:1.2*e,
  hover:(.4+T.curiosity*.6)*1.1*e,
  curious:T.curiosity*1.6+(recentPointer?2.4:0),
  charge:T.radiance*T.radiance*1.8*e+(m.resonance>=85?.5:0),
  sleep:T.sleepiness*(1-e)*3+(night?1.4:0)+(idleFor>45?1.6:0)+(e<.35?2.5:0)
 };
 if(m.reduced){w.pounce=0;w.walk=0;w.hover=0;w.charge=0;}
 if(m.lastAction&&m.lastAction!=='idle')w[m.lastAction]*=.15;
 return w;
}
function chooseNext(m){
 if(m.behavior!=='idle'){startBehavior(m,'idle');return;}
 const w=behaviorWeights(m),keys=BEHAVIORS.filter(k=>k!=='idle');
 const total=keys.reduce((s,k)=>s+w[k],0);let r=nextRandom(m)*total;
 for(const k of keys){r-=w[k];if(r<=0){startBehavior(m,k);return;}}
 startBehavior(m,'idle');
}

function targetExpression(m){
 const key=m.reaction||m.behavior;
 const x={...NEUTRAL,...EXPR[key]};
 if(!m.reaction&&m.behavior!=='sleep'){
  const tired=clamp((40-m.energy)/40);
  x.open*=1-tired*.35;x.sleepy=Math.max(x.sleepy,tired*.6);x.smile*=1-tired*.5;
  if(m.hour>=22||m.hour<6)x.open*=.9;
  x.blush=clamp(x.blush+m.bond/250);
 }
 const sum=MOUTHS.reduce((s,k)=>s+x[k],0)||1;MOUTHS.forEach(k=>x[k]/=sum);
 return x;
}
function snapExpression(m){m.expr=targetExpression(m);}

/** Advance the mind by dt seconds. Inputs are real browser signals only. */
export function stepMind(m,dt,inputs={}){
 dt=clamp(num(dt,0),0,.1);m.t+=dt;
 if(inputs.hour!==undefined)m.hour=num(inputs.hour,m.hour);
 if(inputs.pointer&&inputs.pointer.moved){m.pointer={x:clamp(num(inputs.pointer.x,0),-1,1),y:clamp(num(inputs.pointer.y,0),-1,1),lastMove:m.t};m.lastPresence=m.t;}
 const b=m.behavior,drain={idle:.04,blink:.02,curious:.08,walk:.35,hover:.45,pounce:.7,charge:.6}[b];
 if(b==='sleep')m.energy=clamp(m.energy+2.2*dt,0,100);else m.energy=clamp(m.energy-(drain||.05)*dt,0,100);
 if(m.reaction&&m.t>=m.reactionEnd){m.reaction=null;startBehavior(m,'idle');m.behaviorEnd=m.t+1.2+nextRandom(m)*1.5;}
 if(!m.reaction){
  if(m.behavior!=='sleep'&&m.energy<22)startBehavior(m,'sleep');
  else if(m.behavior==='sleep'){if(m.t>=m.behaviorEnd&&m.energy>=m.wakeAt){startBehavior(m,'blink');}}
  else if(m.t>=m.behaviorEnd)chooseNext(m);
 }
 // Micro-blinks (ambient, seeded). Off while asleep and for reduced motion.
 if(!m.reduced&&m.behavior!=='sleep'&&m.t>=m.nextBlink){
  m.blinkStart=m.t;const r=nextRandom(m);
  m.nextBlink=m.t+(r<.18?.32:m.traits.blinkEvery*(.6+nextRandom(m)*.8));
 }
 // Gaze: real pointer when it moved recently, otherwise seeded saccades.
 if(m.behavior==='sleep'){m.gazeTarget={x:0,y:.2};}
 else if(m.t-m.pointer.lastMove<2.5){m.gazeTarget={x:m.pointer.x,y:m.pointer.y};}
 else if(m.t>=m.nextSaccade){m.gazeTarget={x:(nextRandom(m)-.5)*1.2,y:(nextRandom(m)-.5)*.8};m.nextSaccade=m.t+.8+nextRandom(m)*2;}
 const gk=m.reduced?1:1-Math.exp(-dt*14);
 m.gaze.x+=(m.gazeTarget.x-m.gaze.x)*gk;m.gaze.y+=(m.gazeTarget.y-m.gaze.y)*gk;
 const tgt=targetExpression(m);
 if(m.reduced)m.expr=tgt;else{const k=1-Math.exp(-dt*6);for(const key of Object.keys(tgt))m.expr[key]+=(tgt[key]-m.expr[key])*k;}
 const faceTarget=m.behavior==='walk'?((m.t-m.behaviorStart)/(m.behaviorEnd-m.behaviorStart)<.5?m.walkDir:-m.walkDir):1;
 m.face+=(faceTarget-m.face)*(m.reduced?1:1-Math.exp(-dt*7));
 return m;
}

/** Deterministic hand-off used by the ?zerefDemo=1 evidence mode and tests. */
export function forceBehavior(m,b){
 if(!BEHAVIORS.includes(b))throw Error('Unknown Zeref behaviour.');
 if(m.reduced&&LOCOMOTION.includes(b))b='idle';
 m.reaction=null;startBehavior(m,b);if(b==='sleep')m.energy=Math.min(m.energy,40);
 if(m.reduced)snapExpression(m);
 return m.behavior;
}

/** A real tap / click / key press / long-press. Returns the chosen reaction. */
export function tapMind(m,{hold=false}={}){
 m.taps=m.taps.filter(t=>m.t-t<1.5);m.taps.push(m.t);
 m.bond=clamp(m.bond+2,0,100);m.energy=clamp(m.energy+1,0,100);m.lastPresence=m.t;
 let reaction;
 if(m.behavior==='sleep')reaction='startled';
 else if(m.taps.length>=4)reaction='startled';
 else if(hold)reaction='purr';
 else{
  const wh=1+m.traits.playfulness,wp=.35+m.traits.affection*.6+m.bond/120;
  reaction=nextRandom(m)*(wh+wp)<wh?'happy':'purr';
 }
 m.reaction=reaction;m.reactionStart=m.t;m.reactionEnd=m.t+({happy:1.5,startled:1.1,purr:2.4}[reaction]);
 m.behavior='idle';m.behaviorStart=m.t;m.behaviorEnd=m.reactionEnd+.5;
 m.history.push(reaction);if(m.history.length>40)m.history.shift();
 if(m.reduced)snapExpression(m);
 return reaction;
}

/** Programmatic wave (e.g. the existing "Wave hello" button): a friendly reaction, no bond farming. */
export function greetMind(m){
 if(m.behavior==='sleep'){m.energy=Math.max(m.energy,30);}
 m.reaction='happy';m.reactionStart=m.t;m.reactionEnd=m.t+1.5;m.behavior='idle';m.behaviorStart=m.t;m.behaviorEnd=m.t+2;m.lastPresence=m.t;
 m.history.push('happy');if(m.reduced)snapExpression(m);return 'happy';
}

export function describeMind(m){
 const key=m.reaction||m.behavior;
 return {behavior:m.behavior,reaction:m.reaction,state:key,mood:MOOD[key],line:LINES[key],energy:Math.round(m.energy),bond:Math.round(m.bond)};
}

const ease=x=>x<0?0:x>1?1:x*x*(3-2*x);
const bump=(p,a,b)=>p<a||p>b?0:Math.sin((p-a)/(b-a)*Math.PI);

/** Pure pose for the rig at the mind's current time. Reduced motion = zero motion amplitudes. */
export function frameFor(m){
 const t=m.t,ex=m.expr,b=m.behavior,R=m.reaction;
 const p=clamp((t-m.behaviorStart)/Math.max(.001,m.behaviorEnd-m.behaviorStart));
 const rp=R?clamp((t-m.reactionStart)/Math.max(.001,m.reactionEnd-m.reactionStart)):0;
 const f={floatX:0,floatY:0,rot:0,face:m.face,bodySX:1,bodySY:1,headRot:0,headY:0,earL:0,earR:0,wingL:0,wingR:0,tail:0,wisp:0,
  pawL:0,pawR:0,gazeX:m.gaze.x,gazeY:m.gaze.y,lid:1-ex.open,lower:ex.lower,pupil:ex.pupil,brow:ex.brow,
  mouth:{smile:ex.smile,grin:ex.grin,o:ex.o,frown:ex.frown,sleepy:ex.sleepy},blush:ex.blush,glow:ex.glow,ring:0,charge:0,shadow:1,
  fx:{zzz:b==='sleep'&&!R?1:0,question:b==='curious'&&!R?ease(p*4):0,exclaim:R==='startled'?1-ease(rp*1.2-.2):0,heart:R==='purr'?1:0,sparkle:R==='happy'?1-rp:0}};
 if(m.reduced){f.face=1;f.gazeX=0;f.gazeY=0;return f;}
 const breath=Math.sin(t*(b==='sleep'?1.5:2.4));
 f.bodySY=1+breath*(b==='sleep'?.03:.018);f.bodySX=1-breath*.008;
 f.floatY=Math.sin(t*1.3)*3;f.rot=Math.sin(t*.7)*1.2;
 f.tail=Math.sin(t*1.6)*9;f.wisp=t;
 f.wingL=Math.sin(t*1.1)*4;f.wingR=f.wingL;
 f.earL=Math.max(0,Math.sin(t*.9+1))**8*-10;f.earR=Math.max(0,Math.sin(t*.7+2.4))**8*10;
 f.headRot=Math.sin(t*.5)*2+m.gaze.x*4;
 // Micro-blink overlay.
 const bt=t-m.blinkStart;if(bt>=0&&bt<.18)f.lid=Math.max(f.lid,bump(bt,0,.18));
 switch(b){
  case 'blink':{const c=bump(p,.1,.8);f.lid=Math.max(f.lid,Math.min(1,c*1.4));f.headRot+=c*6*m.traits.lean;break;}
  case 'pounce':{
   const crouch=bump(p,0,.38),air=bump(p,.34,.72),land=bump(p,.68,.86);
   f.floatY+=crouch*10-air*52+land*6;f.bodySY*=1-crouch*.1+air*.06-land*.08;f.bodySX*=1+crouch*.07+land*.07;
   f.rot+=-air*9*m.traits.lean;f.pawL=air*1;f.pawR=air*.85+crouch*.2;f.tail+=air*28;f.wingL+=air*22;f.wingR+=air*22;f.shadow=1-air*.45;
   f.earL-=crouch*12;f.earR+=crouch*12;break;}
  case 'walk':{
   const step=t*7.5;f.floatX=m.walkDir*30*Math.sin(p*Math.PI*2)*.7;f.floatY+=-Math.abs(Math.sin(step))*6;
   f.pawL=Math.max(0,Math.sin(step))*.55;f.pawR=Math.max(0,-Math.sin(step))*.55;f.tail+=Math.sin(step*.5)*14;
   f.headY=Math.abs(Math.sin(step))*2;f.rot+=Math.sin(step)*1.5;break;}
  case 'hover':{
   const up=ease(Math.min(1,p*4))*ease(Math.min(1,(1-p)*4));
   f.floatY+=-34*up+Math.sin(t*3.2)*4*up;f.wingL+=up*(14+Math.sin(t*18)*24);f.wingR=f.wingL;f.ring=up;f.shadow=1-up*.5;
   f.pawL=up*.35;f.pawR=up*.35;f.tail+=up*Math.sin(t*3)*10;break;}
  case 'curious':{
   const tilt=ease(Math.min(1,p*5))*ease(Math.min(1,(1-p)*5));
   f.headRot+=tilt*15*m.traits.lean;f.earL+=tilt*-8;f.earR+=tilt*8;f.headY-=tilt*3;break;}
  case 'charge':{
   const c=bump(p,0,1),pk=ease(Math.min(1,p*3));
   f.floatY+=c*7;f.bodySY*=1-c*.05;f.charge=pk*(1-ease(Math.max(0,(p-.85)/.15)));
   f.rot+=Math.sin(t*38)*c*.9;f.wingL+=c*16;f.wingR+=c*16;f.earL-=c*14;f.earR+=c*14;f.tail+=c*18;break;}
  case 'sleep':{
   const settle=ease(Math.min(1,p*6));
   f.floatY+=settle*16;f.headRot+=settle*-9*m.traits.lean;f.headY+=settle*10;f.tail+=settle*24;f.wingL-=settle*6;f.wingR-=settle*6;
   f.earL+=settle*6;f.earR-=settle*6;f.rot=Math.sin(t*.5)*.4;break;}
 }
 if(R==='happy'){const h=bump(rp,0,.45)+bump(rp,.45,.9)*.6;f.floatY-=h*20;f.tail+=Math.sin(t*22)*16;f.pawL+=h*.6;f.pawR+=h*.6;f.wingL+=h*10;f.wingR+=h*10;}
 if(R==='startled'){const s=bump(rp,0,.55);f.floatY-=s*28;f.bodySY*=1+s*.08;f.wingL+=s*30;f.wingR+=s*30;f.earL-=s*16;f.earR+=s*16;f.tail+=s*30;}
 if(R==='purr'){f.headRot+=10*m.traits.lean*ease(Math.min(1,rp*4));f.rot+=Math.sin(t*44)*.35;f.tail+=Math.sin(t*2)*6;}
 return f;
}
