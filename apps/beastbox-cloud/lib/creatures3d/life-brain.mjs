/**
 * LIFE BRAIN: the autonomous "live feed" behaviour loop for a creature in the pocket cage.
 * Pure + deterministic: same seed + same inputs → same life. No DOM, clock or network.
 * Modes: wander · nap · sniff (flowers/treats) · chase (fireflies) · shelter (rain) · play (residents)
 *        · glance (brief look at the camera) · approach (comes to the camera when poked/curious).
 * Weights come from the CST mood (lib/physics/cst-integrator.mjs creatureMood) so the engine drives life.
 * The creature mostly ignores the camera: glance/approach are rare unless poked or attention-seeking.
 */
import {seededRng,clamp} from '../physics/cst-integrator.mjs';

export const LIFE_MODES=Object.freeze(['wander','nap','sniff','chase','shelter','play','glance','approach','splash','greet','follow']);
const SPEED={wander:.55,nap:0,sniff:.4,chase:1.25,shelter:.95,play:.9,glance:0,approach:.7,splash:.8,greet:.5,follow:.6};
export const POCKET_RADIUS=3.4;

export function createLife(seed,{x=0,z=0}={}){
 const r=seededRng('life:'+seed);
 return {r,seed:String(seed),mode:'wander',timer:1+r()*2,x,z,heading:r()*Math.PI*2,speed:0,
  target:{x:(r()-.5)*4,z:(r()-.5)*4},energy:.7+r()*.3,hunger:.3+r()*.3,attn:null,lookCam:0,
  sleep:0,poked:0,startle:0,lastMode:'',bob:0,t:0,history:[]};
}

const night0=env=>(env.night??0)<.5;
function pickTarget(L,R=POCKET_RADIUS*.85){const a=L.r()*Math.PI*2,d=Math.sqrt(L.r())*R;return {x:Math.cos(a)*d,z:Math.sin(a)*d};}
const nearest=(L,list)=>{let b=null,bd=Infinity;for(const o of list||[]){const d=Math.hypot(o.x-L.x,o.z-L.z);if(d<bd){bd=d;b=o;}}return b?{...b,d:bd}:null;};

/** Weighted mode choice from mood + world. Exported for tests. */
export function modeWeights(L,env){
 const m=env.mood||{joy:.5,curiosity:.5,fear:.1,calm:.6,mischief:.3},night=env.night??0,rain=env.rain??0;
 const w={
  wander:.6+m.curiosity*.9,
  nap:(1-L.energy)*1.6+night*.7+m.calm*.4,
  sniff:L.hunger*1.2*((env.flowers?.length||0)>0?1:.2)+m.calm*.2,
  chase:m.mischief*1.2*night*((env.fireflies?.length||0)>0?1:0),
  shelter:rain>.25?rain*4+m.fear*2:0,
  play:m.joy*.9*((env.residents?.length||0)>0?1:0),
  glance:.05+m.curiosity*.08,            // rare: it is living its own life
  approach:.02+m.joy*m.curiosity*.08,
  // lived-in pocket (Oct 16): puddles after rain, sniff-hello and following other creatures
  splash:(env.puddles?.some(p=>p.wet>.3)?1:0)*(m.joy*1.1+m.mischief*.6)*(rain<.3?1:0),
  greet:(env.residents?.length?1:0)*(L.t-(L.lastGreet??-99)>20?.3+m.curiosity*.5:0),
  follow:(env.residents?.length?1:0)*(m.calm*.25+m.joy*.2),
 };
 // sunny favourite spot makes daytime naps more likely
 if(env.spots?.length&&night<.5)w.nap*=1.4;
 if(rain>.25){w.nap*=.4;w.chase=0;w.play*=.3;}
 return w;
}
function choose(L,w){let s=0;for(const k in w)s+=w[k];let u=L.r()*s;for(const k of LIFE_MODES){u-=w[k]||0;if(u<=0)return k;}return 'wander';}

/** Poke / talk: the creature notices. Joy → approach, fear → startle and back away. */
export function pokeLife(L,{fear=.1,joy=.5}={},cam=null){
 L.poked=1;L.sleep=0;
 if(fear>joy){L.startle=1;L.mode='wander';L.timer=2.5;if(cam){const a=Math.atan2(L.z-cam.z,L.x-cam.x);L.target={x:L.x+Math.cos(a)*1.5,z:L.z+Math.sin(a)*1.5};}}
 else{L.mode='approach';L.timer=4.5;}
}

/**
 * Advance one step. env: {mood, night, rain, flowers:[{x,z}], treats:[{x,z,id}], fireflies:[{x,y,z}],
 * residents:[{x,z}], shelter:{x,z}, cam:{x,z}}. Returns the life state (mutated).
 */
export function stepLife(L,dt,env={}){
 if(!(dt>0))return L;L.t+=dt;L.timer-=dt;
 const m=env.mood||{joy:.5,curiosity:.5,fear:.1,calm:.6,mischief:.3};
 L.energy=clamp(L.energy+(L.mode==='nap'?dt*.05:-dt*.006*(1+(SPEED[L.mode]||0))));
 L.hunger=clamp(L.hunger+dt*.004-(L.mode==='sniff'&&L.speed<.05?dt*.05:0));
 L.poked=Math.max(0,L.poked-dt*.4);L.startle=Math.max(0,L.startle-dt*.8);
 const rain=env.rain??0;
 const treat=nearest(L,env.treats);
 if(treat&&L.mode!=='sniff'&&L.mode!=='approach'){L.mode='sniff';L.timer=8;}
 if(rain>.35&&L.mode!=='shelter'&&L.mode!=='approach'&&L.startle<=0){L.mode='shelter';L.timer=6+L.r()*4;}
 if(L.timer<=0){const next=choose(L,modeWeights(L,env));L.mode=next;
  L.timer=next==='nap'?10+L.r()*14:next==='glance'?1.4+L.r()*1.2:next==='approach'?4+L.r()*2:4+L.r()*6;
  if(next==='wander'||next==='play')L.target=pickTarget(L);}
 if(L.mode!==L.lastMode){L.history.push(L.mode);if(L.history.length>40)L.history.shift();L.lastMode=L.mode;}
 // targets + attention
 let tgt=L.target,attn=null;
 switch(L.mode){
  case 'sniff':{const f=treat||nearest(L,env.flowers);if(f){tgt={x:f.x-Math.cos(L.heading)*.25,z:f.z-Math.sin(L.heading)*.25};attn={kind:treat?'treat':'flower',x:f.x,y:.1,z:f.z,id:f.id};}break;}
  case 'chase':{const f=nearest(L,env.fireflies);if(f){tgt=f;attn={kind:'firefly',x:f.x,y:f.y??.8,z:f.z};}break;}
  case 'shelter':{const s=env.shelter||{x:0,z:0};tgt=s;attn={kind:'sky',x:L.x,y:3,z:L.z};break;}
  case 'play':{const o=nearest(L,env.residents);if(o){if(o.d<.9){const a=Math.atan2(L.z-o.z,L.x-o.x)+.9;tgt={x:o.x+Math.cos(a)*.55,z:o.z+Math.sin(a)*.55};}else tgt=o;attn={kind:'resident',x:o.x,y:.5,z:o.z,id:o.id};}break;}
  case 'approach':case 'glance':{const c=env.cam;if(c){attn={kind:'camera',x:c.x,y:1,z:c.z};if(L.mode==='approach'){const a=Math.atan2(c.z-L.z,c.x-L.x);tgt={x:L.x+Math.cos(a)*.6,z:L.z+Math.sin(a)*.6};const r=Math.hypot(tgt.x,tgt.z);if(r>POCKET_RADIUS*.8){tgt.x*=POCKET_RADIUS*.8/r;tgt.z*=POCKET_RADIUS*.8/r;}}}break;}
  case 'nap':{const s=night0(env)&&nearest(L,env.spots);if(s&&s.d>.25){tgt={x:s.x,z:s.z};attn={kind:'spot',x:s.x,y:0,z:s.z};}break;}
  case 'splash':{const p=nearest(L,(env.puddles||[]).filter(q=>q.wet>.3));if(p){if(p.d<p.r*.8){if(Math.hypot(tgt.x-L.x,tgt.z-L.z)<.15||Math.hypot(tgt.x-p.x,tgt.z-p.z)>p.r)L.target=tgt={x:p.x+(L.r()-.5)*p.r*1.4,z:p.z+(L.r()-.5)*p.r*1.4};}else tgt={x:p.x,z:p.z};attn={kind:'puddle',x:p.x,y:0,z:p.z};}break;}
  case 'greet':{const o=nearest(L,env.residents);if(o){const a=Math.atan2(L.z-o.z,L.x-o.x);tgt={x:o.x+Math.cos(a)*.5,z:o.z+Math.sin(a)*.5};attn={kind:'resident',x:o.x,y:.35,z:o.z,id:o.id};if(o.d<.65){L.lastGreet=L.t;}}break;}
  case 'follow':{const o=nearest(L,env.residents);if(o){const a=Math.atan2(L.z-o.z,L.x-o.x);tgt={x:o.x+Math.cos(a)*.75,z:o.z+Math.sin(a)*.75};attn={kind:'resident',x:o.x,y:.4,z:o.z,id:o.id};}break;}
  case 'wander':{if(Math.hypot(tgt.x-L.x,tgt.z-L.z)<.3)L.target=tgt=pickTarget(L);attn={kind:'ground',x:tgt.x,y:0,z:tgt.z};break;}
 }
 L.attn=attn;
 // locomotion: steer, ease speed (CST calm → smoother), stay in the pocket
 const dx=tgt.x-L.x,dz=tgt.z-L.z,d=Math.hypot(dx,dz);
 const napWalk=L.mode==='nap'&&L.attn?.kind==='spot';const want=(L.mode==='nap'&&!napWalk||L.mode==='glance')?0:d<.12?0:(SPEED[L.mode]||.5)*(L.startle>0?1.8:1)*(.75+m.mischief*.5)*Math.min(1,d*1.5);
 L.speed+=(want-L.speed)*Math.min(1,dt*(1.5+m.calm));
 if(d>.05&&want>0){const h=Math.atan2(dz,dx);let dh=((h-L.heading+Math.PI*3)%(Math.PI*2))-Math.PI;L.heading+=dh*Math.min(1,dt*(2.2+m.curiosity));}
 L.x+=Math.cos(L.heading)*L.speed*dt;L.z+=Math.sin(L.heading)*L.speed*dt;
 const r=Math.hypot(L.x,L.z);if(r>POCKET_RADIUS){L.x*=POCKET_RADIUS/r;L.z*=POCKET_RADIUS/r;L.target=pickTarget(L);}
 // eat a treat on arrival
 if(treat&&treat.d<.35&&env.onEat){env.onEat(treat.id);L.hunger=clamp(L.hunger-.4);}
 L.sleep+=((L.mode==='nap'&&L.speed<.05?1:0)-L.sleep)*Math.min(1,dt*.8);
 // moments other systems react to (splash particles, resident turns, tussle hops)
 {const p=nearest(L,(env.puddles||[]).filter(q=>q.wet>.3));L.inPuddle=!!(p&&p.d<p.r);}
 L.moment=L.mode==='splash'&&L.inPuddle&&L.speed>.15?'splash':L.mode==='greet'&&L.attn&&Math.hypot(L.attn.x-L.x,L.attn.z-L.z)<.7?'sniff-hello':L.mode==='play'&&L.attn&&Math.hypot(L.attn.x-L.x,L.attn.z-L.z)<.9?'play-fight':L.mode==='follow'?'follow':L.mode==='nap'&&L.attn?.kind==='spot'?'to-nap-spot':null;
 L.lookCam+=(((L.mode==='glance'||L.mode==='approach')?1:0)-L.lookCam)*Math.min(1,dt*3);
 L.bob+=dt*(2+L.speed*7);
 return L;
}
