/**
 * ZEREF // DIMENSIONAL POCKET — a pure, seeded exploration state machine.
 *
 * The beast wanders between points of interest (moon pools, crystals,
 * portals) inside the Beast Cage pocket. Places are seeded from the recorded
 * digest, so the same beast always gets the same pocket. Travel gait, what it
 * does on arrival and how long it stays come from the deterministic mind
 * (zeref-mind.mjs): energy, temperament and the seeded RNG. No DOM, no
 * storage, no network. Used both by the browser (requestAnimationFrame) and by
 * the server-side diary loop (fixed dt replay), so both see the same rules.
 *
 * "Discovered combos" are new combinations of rig parameters (action, gait,
 * place, wings, tail, eyes, mouth) that the blend produced for the first time.
 * They are combinations of existing animation channels, not new animations.
 */
import {forceBehavior} from './zeref-mind.mjs';

export const POCKET_SCHEMA='zeref-pocket/v1';
export const POI_KINDS=Object.freeze(['moon-pool','crystal','portal']);
const POI_NAMES=Object.freeze({
 'moon-pool':['Selene Pool','Tidewell','Hollow Mirror','Lunar Basin'],
 'crystal':['Resonance Spire','Violet Shard','Echo Prism','Quartz Choir','Star Geode'],
 'portal':['Rift Gate','Fold Door','Lattice Arch','Seam of Worlds']
});
export const GAITS=Object.freeze(['walk','hover','pounce']);
const SPEED={walk:.085,hover:.15,pounce:.2};
export const PHASES=Object.freeze(['rest','travel','interact']);

const clamp=(v,lo=0,hi=1)=>Math.min(hi,Math.max(lo,v));
function hash32(text){let h=0x811c9dc5;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,0x01000193);}return h>>>0;}
/** mulberry32 on the pocket's own serialisable rng (separate from the mind's). */
export function pocketRandom(p){p.rng=(p.rng+0x6D2B79F5)|0;let t=p.rng;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;}

/** Seeded points of interest in normalised pocket space: x,y in [-1,1] (y>0 = nearer the viewer). */
export function createPocket({digest='',key='',reduced=false}={}){
 const p={schema:POCKET_SCHEMA,rng:hash32(String(digest)+'|pocket|'+String(key))|0,reduced:Boolean(reduced),
  t:0,x:0,y:.15,face:1,phase:'rest',phaseStart:0,phaseEnd:1.2,gait:'walk',target:null,lastTarget:null,
  pois:[],visits:{},order:[],arrivals:0,seen:{},sampleAt:0};
 const kinds=['moon-pool','moon-pool','crystal','crystal','crystal','portal','portal'];
 const used={};
 for(const kind of kinds){
  let best=null;
  for(let tries=0;tries<24;tries++){
   const c={x:-.82+pocketRandom(p)*1.64,y:-.55+pocketRandom(p)*1.15};
   const d=Math.min(9,...p.pois.map(o=>Math.hypot(o.x-c.x,(o.y-c.y)*1.4)));
   if(!best||d>best.d)best={...c,d};
   if(d>.42)break;
  }
  const names=POI_NAMES[kind];used[kind]=used[kind]||new Set();
  let name=names[Math.floor(pocketRandom(p)*names.length)];
  while(used[kind].has(name))name=names[(names.indexOf(name)+1)%names.length];
  used[kind].add(name);
  p.pois.push({id:kind+'-'+p.pois.length,kind,name,x:+best.x.toFixed(3),y:+best.y.toFixed(3)});
 }
 return p;
}

/** Seeded, mind-weighted choice of the next place to visit. */
export function poiWeights(p,m){
 const T=m.traits||{},e=clamp((m.energy??60)/100);
 return p.pois.map(poi=>{
  let w=1;
  if(poi.kind==='moon-pool')w=.6+(1-e)*3+(T.sleepiness||0);
  if(poi.kind==='crystal')w=.5+(T.radiance||.5)*1.6*e;
  if(poi.kind==='portal')w=.5+(T.curiosity||.5)*1.8;
  w/=1+(p.visits[poi.id]||0)*.35; // novelty: unexplored places pull harder
  if(poi.id===p.target?.id||poi.id===p.lastTarget)w*=.08;
  return w;
 });
}

function pickTarget(p,m){
 const w=poiWeights(p,m),total=w.reduce((s,v)=>s+v,0);let r=pocketRandom(p)*total;
 for(let i=0;i<w.length;i++){r-=w[i];if(r<=0)return p.pois[i];}
 return p.pois[p.pois.length-1];
}
function gaitFor(p,m,dist){
 const e=(m.energy??60)/100,T=m.traits||{};
 if(m.reduced)return 'walk';
 if(dist>.8&&e>.45)return 'hover';
 if(dist<.55&&e>.5&&pocketRandom(p)<(T.playfulness||.5)*.8)return 'pounce';
 if(e>.7&&pocketRandom(p)<(T.curiosity||.5)*.5)return 'hover';
 return 'walk';
}
function arrivalBehavior(p,m,poi){
 const e=m.energy??60;
 if(poi.kind==='moon-pool')return e<55?'sleep':(pocketRandom(p)<.5?'blink':'curious');
 if(poi.kind==='crystal')return pocketRandom(p)<.75?'charge':'curious';
 return pocketRandom(p)<.6?'curious':'hover';
}
function setPhase(p,phase,dur){p.phase=phase;p.phaseStart=p.t;p.phaseEnd=p.t+dur;}

/**
 * Advance the pocket by dt seconds. `busy` (an attack in progress) plants the
 * beast's feet. Returns the events that happened this step.
 */
export function stepPocket(p,m,dt,{busy=false}={}){
 dt=clamp(Number(dt)||0,0,.1);p.t+=dt;const events=[];
 if(busy||m.reaction)return events;
 if(p.phase==='rest'){
  if(p.t>=p.phaseEnd&&m.behavior!=='sleep'){
   const poi=pickTarget(p,m);
   p.lastTarget=p.target?.id||null;p.target=poi;
   const dist=Math.hypot(poi.x-p.x,poi.y-p.y);
   p.gait=gaitFor(p,m,dist);
   if(p.reduced){p.x=poi.x;p.y=poi.y;arrive(p,m,poi,events);}
   else{setPhase(p,'travel',30);forceBehavior(m,p.gait);events.push({type:'depart',poi:poi.id,gait:p.gait});}
  }
 }else if(p.phase==='travel'){
  const poi=p.target;
  if(m.behavior==='sleep'){setPhase(p,'rest',2);return events;} // too tired to keep going
  if(m.behavior!==p.gait)forceBehavior(m,p.gait);
  const dx=poi.x-p.x,dy=poi.y-p.y,dist=Math.hypot(dx,dy);
  const speed=SPEED[p.gait]*(.6+clamp((m.energy??60)/100)*.6);
  if(dist<=speed*dt||dist<.01||p.t>=p.phaseEnd){p.x=poi.x;p.y=poi.y;arrive(p,m,poi,events);}
  else{p.x+=dx/dist*speed*dt;p.y+=dy/dist*speed*dt;if(Math.abs(dx)>.02)p.face=dx<0?-1:1;}
 }else if(p.phase==='interact'){
  if(p.t>=p.phaseEnd&&m.behavior!=='sleep'){setPhase(p,'rest',1.2+pocketRandom(p)*2.6);if(!m.reduced)forceBehavior(m,'idle');}
 }
 return events;
}
function arrive(p,m,poi,events){
 p.visits[poi.id]=(p.visits[poi.id]||0)+1;p.arrivals++;p.order.push(poi.id);if(p.order.length>40)p.order.shift();
 const b=arrivalBehavior(p,m,poi);
 forceBehavior(m,b);
 setPhase(p,'interact',3.5+pocketRandom(p)*4.5);
 events.push({type:'arrive',poi:poi.id,name:poi.name,kind:poi.kind,behavior:m.behavior});
}

/** The place the beast is at (within reach) or 'open-pocket'. */
export function placeOf(p){
 let best=null,bd=.14;
 for(const poi of p.pois){const d=Math.hypot(poi.x-p.x,poi.y-p.y);if(d<bd){bd=d;best=poi;}}
 return best;
}

/** Growth stage (1..5) -> rig scale/aura. Pure display mapping. */
export function growthLook(stage=1){
 const s=Math.round(clamp(Number(stage)||1,1,5));
 return {stage:s,scale:+(.84+s*.06).toFixed(2),aura:+(.25+s*.15).toFixed(2),rings:Math.max(0,s-2)};
}

/**
 * Blend pocket travel into the rig frame (in place). Hover height, wing beat
 * and tail energy rise with travel speed; facing follows the path.
 */
export function blendFrame(f,p,m,{stage=1}={}){
 const g=growthLook(stage);
 const travel=p.phase==='travel'?1:0;
 f.face=p.face*Math.abs(f.face||1);
 if(!m.reduced){
  if(travel&&p.gait==='hover'){f.floatY-=10;f.wingL+=6;f.wingR+=6;}
  if(travel&&p.gait==='walk'){f.floatX*=.25;}
  f.tail*=1+travel*.25;
 }
 f.glow=clamp(f.glow*(.8+g.aura*.4));
 f.scale=g.scale;f.auraStage=g.aura;
 return f;
}

const band=(v,cuts,names)=>{for(let i=0;i<cuts.length;i++)if(v<cuts[i])return names[i];return names[names.length-1];};
/** A combination of rig channels, quantised so it can be recognised again. */
export function comboOf(f,p,m){
 const place=placeOf(p);
 const mouth=Object.entries(f.mouth||{}).sort((a,b)=>b[1]-a[1])[0]?.[0]||'smile';
 const parts={
  action:m.reaction||m.behavior,
  gait:p.phase==='travel'?p.gait:'still',
  place:place?place.kind:'open-pocket',
  wings:band(Math.max(Math.abs(f.wingL),Math.abs(f.wingR)),[8,22],['folded','beating','full-spread']),
  tail:band(Math.abs(f.tail),[12,28],['sway','flick','lash']),
  eyes:band(f.lid,[.3,.7],['open','half','closed']),
  mouth
 };
 const key=[parts.action,parts.gait,parts.place,parts.wings,parts.tail,parts.eyes,parts.mouth].join('|');
 const where=parts.place==='open-pocket'?'in the open pocket':'at a '+parts.place.replace('-',' ');
 const moving=parts.gait==='walk'?'walking':parts.gait==='hover'?'hovering':'pouncing';
 const lead=parts.gait==='still'?parts.action:parts.action===parts.gait?moving:`${parts.action} while ${moving}`;
 const name=`${lead} · ${parts.wings} wings · ${parts.tail} tail · ${parts.eyes} eyes · ${parts.mouth} mouth ${where}`;
 return {key,name,parts};
}

/** Sample the current combo at most every 0.5 s; returns it only when first seen in this pocket. */
export function sampleCombo(p,f,m){
 if(p.t<p.sampleAt)return null;p.sampleAt=p.t+.5;
 const c=comboOf(f,p,m);
 if(p.seen[c.key])return null;p.seen[c.key]=1;
 return c;
}
