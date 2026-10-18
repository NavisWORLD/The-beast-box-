/** Wireframe companion critters (Cory's spider/jellyfish wireframe designs): pure themes, IK, feeding, growth. */
import {fnv1a,seededRng} from '../physics/cst-integrator.mjs';
export const COMPANION_LIMITS=Object.freeze({maxCompanions:8,motesLow:18,motesHigh:32,growMax:1.35,growStep:.03});
const T=(name,motif,color,accent,legs,wings,tentacles)=>Object.freeze({name,motif,color,accent,legs,wings,tentacles});
export const COMPANION_THEMES=Object.freeze({
  'zeref':T('Mothwhisk','cat-moth',0xb48cff,0x7fe6ff,4,true,0),
  'art-nyxbean':T('Starbeetle','star-beetle',0x8f7bff,0xffffff,6,false,0),
  'art-frostmitt':T('Rimespinner','ice-spider',0x9fe8ff,0xe8fbff,8,false,0),
  'art-kairo':T('Hornfly','horn-firefly',0xffc46b,0xfff1c9,4,true,0),
  'art-shardhowl':T('Shardmite','crystal-mite',0xff8fd8,0x7fffe0,6,false,0),
  'art-velvetcoil':T('Scalejelly','scaled-jelly',0xd16bff,0xffb8f0,0,false,7),
});
const MOTIFS=['ice-spider','crystal-mite','scaled-jelly','cat-moth','star-beetle'];
/** Theme for any creature id; generated/saved Beasts get a procedural one from their seed. */
export function companionTheme(id){
  if(COMPANION_THEMES[id])return COMPANION_THEMES[id];
  const r=seededRng('companion:'+id),motif=MOTIFS[fnv1a(id)%MOTIFS.length];
  const hue=r(),hsl=(h,s,l)=>{const f=n=>{const k=(n+h*12)%12,a=s*Math.min(l,1-l);return Math.round(255*(l-a*Math.max(-1,Math.min(k-3,9-k,1))));};return (f(0)<<16)|(f(8)<<8)|f(4);};
  const jelly=motif==='scaled-jelly';
  return Object.freeze({name:'Wisp-'+(fnv1a(id)%997),motif,color:hsl(hue,.75,.68),accent:hsl((hue+.45)%1,.8,.8),legs:jelly?0:[4,6,8][Math.floor(r()*3)],wings:motif==='cat-moth',tentacles:jelly?5+Math.floor(r()*3):0});
}
/** Analytic two-bone IK (equal bones): knee lifted toward `up` (spider style). */
export function kneeIK(hip,foot,len){
  const mx=(hip.x+foot.x)/2,my=(hip.y+foot.y)/2,mz=(hip.z+foot.z)/2,d=Math.hypot(foot.x-hip.x,foot.y-hip.y,foot.z-hip.z);
  const h=Math.sqrt(Math.max(0,len*len-(d/2)*(d/2)));return {x:mx,y:my+h,z:mz,reach:d<=2*len};
}
/** Step decision: replant when the foot drifts beyond `stride` from its rest target; arc lift while stepping. */
export function legStep(leg,target,dt,{stride=.12,speed=7,lift=.05}={}){
  if(leg.t<1){leg.t=Math.min(1,leg.t+dt*speed);const s=leg.t;leg.foot.x=leg.from.x+(leg.to.x-leg.from.x)*s;leg.foot.z=leg.from.z+(leg.to.z-leg.from.z)*s;leg.foot.y=leg.to.y+Math.sin(Math.PI*s)*lift;return true;}
  if(Math.hypot(target.x-leg.foot.x,target.z-leg.foot.z)>stride){leg.from={...leg.foot};leg.to={...target};leg.t=0;}
  else leg.foot.y=target.y;// planted: exactly on the surface
  return false;
}
/** Feeding: absorb a mote within reach; returns energy shared with the owner (0 if none). */
export function feed(c,motes,{reach=.12}={}){
  for(const m of motes){if(!m.alive)continue;if(Math.hypot(m.x-c.x,m.y-c.y,m.z-c.z)<reach){m.alive=false;c.pulse=1;c.grow=Math.min(COMPANION_LIMITS.growMax,(c.grow||1)+COMPANION_LIMITS.growStep);c.fed=(c.fed||0)+1;return .05+m.e*.1;}}
  return 0;
}
export function nearestMote(c,motes,maxD=2.5){let best=null,bd=maxD;for(const m of motes){if(!m.alive)continue;const d=Math.hypot(m.x-c.x,m.z-c.z);if(d<bd){bd=d;best=m;}}return best;}
export const COMPANION_KEY='beastbox-companions-v1';
export function loadGrowth(storage){try{const o=JSON.parse(storage?.getItem(COMPANION_KEY)||'{}');return o&&typeof o==='object'?o:{};}catch{return {};}}
export function saveGrowth(storage,map){try{const o={};for(const [k,v] of Object.entries(map))if(typeof v==='number'&&isFinite(v))o[k]=Math.min(COMPANION_LIMITS.growMax,Math.max(1,v));storage?.setItem(COMPANION_KEY,JSON.stringify(o));return o;}catch{return {};}}
