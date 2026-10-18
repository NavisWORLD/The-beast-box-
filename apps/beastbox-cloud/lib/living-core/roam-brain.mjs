import {caveSpots} from '../worlds/terrain-math.mjs';
/**
 * Living-core roam brain (Oct 16). Pure logic, no three.js: where the creature goes next,
 * how chat words / gameplay / its own exploration change its mood and its world, and the
 * persistence of the CST particle constructs it makes. Drives off EXISTING signals only:
 * session.chat (useBeastSession), 'beastbox:beast-chat' / 'beastbox:gba-input' events,
 * deriveEmotions(beast), the CHSH game world and the browser-local pocket journal.
 */
export const MOTION={squash:.82,stretch:1.18,flapHz:1.1,downstroke:.35};
/** Favorite spots + mini libraries on the pocket floor (world units, radius ~5). */
export const SPOTS=Object.freeze([
 {id:'moon-pool',kind:'favorite',label:'Moon pool',x:-2.6,z:1.4,color:'#7fb4ff'},
 {id:'nap-moss',kind:'favorite',label:'Nap moss',x:2.8,z:1.8,color:'#9a7cff'},
 {id:'star-perch',kind:'favorite',label:'Star perch',x:.4,z:-3.2,color:'#ffd27a'},
 {id:'lib-stars',kind:'library',label:'Star library',topic:'stars',x:-3.4,z:-1.6,color:'#c8a8ff'},
 {id:'lib-quantum',kind:'library',label:'Quantum library',topic:'quantum',x:3.5,z:-1.2,color:'#7af0ff'},
 {id:'lib-creatures',kind:'library',label:'Creature library',topic:'creatures',x:-.6,z:3.4,color:'#ff9ad8'},
 // Distant points of interest (unit coords ×0.55 in the Cage ≈ 9–26 world units out): reasons to travel the whole universe.
 {id:'far-crystal-arch',kind:'far',label:'Crystal arch',x:18,z:-24,color:'#c8a8ff'},
 {id:'far-nebula-well',kind:'far',label:'Nebula well',x:-30,z:-14,color:'#7af0ff'},
 {id:'far-old-signal',kind:'far',label:'Old signal tower',x:34,z:20,color:'#ffd27a'},
 {id:'far-dream-reef',kind:'far',label:'Dream reef',x:-16,z:36,color:'#ff9ad8'},
 {id:'far-edge-lantern',kind:'far',label:'Edge lantern',x:4,z:-46,color:'#9a7cff'},
 // Caves carved into the home-world hills: creatures roam inside the tunnels.
 ...caveSpots().map(c=>({id:c.id,kind:'far',label:c.label,x:c.x,z:c.z,color:c.color,cave:true})),
]);
export const SHAPES=Object.freeze(['spiral','ring','star','heart','helix','bloom']);
const WORDS=[
 [/\b(love|cute|good|yay|great|happy|thank|awesome|nice)\b/i,'happy'],
 [/\b(scary|scared|afraid|bad|no|ghost|danger)\b/i,'scared'],
 [/\b(sleep|tired|night|nap|rest|dream)\b/i,'sleepy'],
 [/\b(angry|mad|fight|battle|attack|grr)\b/i,'angry'],
 [/(\?|\b(why|what|how|where|look|explore|learn|show)\b)/i,'curious'],
];
const SHAPE_WORDS={star:'star',stars:'star',heart:'heart',love:'heart',spiral:'spiral',galaxy:'spiral',ring:'ring',circle:'ring',dna:'helix',helix:'helix',flower:'bloom',bloom:'bloom'};
/** A chat line -> {emotion, shape|null, burst}. */
export function reactToWords(text){
 const s=String(text||'');let emotion=null;for(const [re,e] of WORDS)if(re.test(s)){emotion=e;break;}
 let shape=null;for(const w of s.toLowerCase().match(/[a-z]+/g)||[])if(SHAPE_WORDS[w]){shape=SHAPE_WORDS[w];break;}
 return {emotion:emotion||(s.trim()?'happy':null),shape,burst:Math.min(1,.25+s.length/160)};
}
/** Mood from the saved Beast's derived emotions + visual state. */
export function baseMood(emo,state){
 if(state==='sleeping')return 'sleepy';
 const e=emo?.emotions||emo||{};const top=Object.entries(e).filter(([,v])=>typeof v==='number').sort((a,b)=>b[1]-a[1])[0]?.[0];
 return {joy:'happy',curiosity:'curious',fear:'scared',calm:'calm',mischief:'happy'}[top]||'calm';
}
export function rng(seed){let a=(typeof seed==='number'?seed:[...String(seed||'bb')].reduce((h,c)=>Math.imul(h^c.charCodeAt(0),16777619),2166136261))>>>0;return()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
/** Next goal: sleepy -> nap moss, curious -> a library, else weighted spots / free wander. */
/** True universe limit (pocket edge is ~4.6): creatures may roam past the pocket, turning back only here. */
export const UNIVERSE_R=30;
export function nextGoal(r,mood,visits={}){
 if(mood==='sleepy')return SPOTS.find(s=>s.id==='nap-moss');
 const libs=SPOTS.filter(s=>s.kind==='library');
 if(r()<.3){const far=SPOTS.filter(s=>s.kind==='far');return far[Math.floor(r()*far.length)];}
 if(mood==='curious'||r()<.35){const least=[...libs].sort((a,b)=>(visits[a.id]||0)-(visits[b.id]||0));return least[r()<.7?0:Math.floor(r()*least.length)];}
 if(r()<.55){const f=SPOTS.filter(s=>s.kind==='favorite');return f[Math.floor(r()*f.length)];}
 const a=r()*Math.PI*2,d=1+r()*(UNIVERSE_R-1.4);return {id:'wander',kind:'wander',x:Math.cos(a)*d,z:Math.sin(a)*d};
}
/** Construct points (unit scale, local), deterministic per seed. */
export function constructPoints(shape,seed,n=160){
 const r=rng(seed),P=new Float32Array(n*3);
 for(let i=0;i<n;i++){const t=i/n,j=(r()-.5)*.04;let x=0,y=0,z=0;const a=t*Math.PI*2;
  if(shape==='spiral'){const k=t*3*Math.PI*2;x=Math.cos(k)*t*.5;z=Math.sin(k)*t*.5;y=.1+t*.15;}
  else if(shape==='ring'){x=Math.cos(a)*.42;y=.45+Math.sin(a)*.42;}
  else if(shape==='star'){const rr=(i%2?.18:.45)*(1+.0*t);const k=Math.floor(t*10)/10*Math.PI*2,f=(t*10)%1;const k2=k+Math.PI/5;const r1=(Math.floor(t*10)%2)?.2:.45,r2=r1===.2?.45:.2;x=Math.sin(k)*r1*(1-f)+Math.sin(k2)*r2*f;y=.45+Math.cos(k)*r1*(1-f)+Math.cos(k2)*r2*f;void rr;}
  else if(shape==='heart'){x=.026*16*Math.pow(Math.sin(a),3);y=.45+.026*(13*Math.cos(a)-5*Math.cos(2*a)-2*Math.cos(3*a)-Math.cos(4*a));}
  else if(shape==='helix'){x=Math.cos(t*4*Math.PI*2+(i%2)*Math.PI)*.18;z=Math.sin(t*4*Math.PI*2+(i%2)*Math.PI)*.18;y=t*.9;}
  else {const p=Math.floor(t*6),f=(t*6)%1;const k=p/6*Math.PI*2;const rr=Math.sin(f*Math.PI)*.4;x=Math.cos(k+f*.5)*rr;y=.4+Math.sin(k+f*.5)*rr*.6;z=Math.sin(k)*rr*.3;}
  P[i*3]=x+j;P[i*3+1]=y+j;P[i*3+2]=z+j;}
 return P;
}
export const CREATIONS_KEY='beastbox-lc-creations-v1';
export const MAX_CREATIONS=12;
/** Pure add: newest last, capped, positions kept clear of the libraries' pedestals. */
export function addCreation(list,c){const out=[...(Array.isArray(list)?list:[]),{shape:SHAPES.includes(c.shape)?c.shape:'spiral',x:+c.x||0,z:+c.z||0,seed:c.seed>>>0,from:c.from||'explore',at:c.at||new Date().toISOString(),hue:+c.hue||.75}];return out.slice(-MAX_CREATIONS);}
export function loadCreations(store,id){try{const v=JSON.parse(store.getItem(CREATIONS_KEY)||'{}');return Array.isArray(v[id])?v[id]:[];}catch{return [];}}
export function saveCreations(store,id,list){try{const v=JSON.parse(store.getItem(CREATIONS_KEY)||'{}');v[id]=list.slice(-MAX_CREATIONS);store.setItem(CREATIONS_KEY,JSON.stringify(v));}catch{/* private mode */}}
/** Hop curve for one step: squash at take-off/landing, stretch mid-air (motion bible). */
export function hopPose(p){const air=Math.sin(Math.PI*Math.min(1,Math.max(0,p)));const land=p<.12?1-p/.12:p>.88?(p-.88)/.12:0;const sy=1+(MOTION.stretch-1)*air-(1-MOTION.squash)*land;return {lift:air*.32,sy,sx:1/Math.sqrt(sy)};}
/** Wing flap: 35% fast downstroke, 65% recovery, 1.1 Hz. */
export function flap(t){const p=(t*MOTION.flapHz)%1;return p<MOTION.downstroke?1-2*(p/MOTION.downstroke):-1+2*((p-MOTION.downstroke)/(1-MOTION.downstroke));}
