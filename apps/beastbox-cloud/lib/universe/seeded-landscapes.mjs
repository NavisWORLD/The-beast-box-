// Seeded landscapes for the Tiny Universe (Oct 24 2026): composed little PLACES set on the land (a pad, a play ring, a shelter, lamps, seats,
// rim trees) that give a world visible life. Spec: docs/TINY_UNIVERSE_SPEC.md "Landscapes (SEEDED)".
// HONESTY, in plain words:
//   - PLACEMENT is SEEDED. A landscape is a pure function of (seed, planet), drawn from lwStream(seed+':landscapes:'+planet.id); the seed is the
//     sha256 of the RECORDED IBM ibm_marrakesh counts, but the recording holds no landscape data. Every landscape carries label:'SEEDED'.
//   - ANIMATION uses the existing labelled signals only: world-field insolation and storm tension, the genesis-sun nightFactor, alive-props life volume.
//   - GENESIS stays RECORDED and growth stays SIMULATED. Nothing here touches genesis, ticks, pairs, storms, life or growth nodes.
// No new creatures: inhabitants are the planet's existing life; this module only gives them places and a mode. No Math.random, no clock, no stored state.
// Own stream only, fixed-length draw vector per attempt, so stars/planets/storms/life/pairs/growth-nodes are byte-identical with landscapes on or off.
// Names come from the authored table (data/landscape_names.json); the implementer invents none. This module does not import growth-nodes.
import {lwStream} from './living-world.mjs';
import {biomeOf} from './tiny-universe-view.mjs';
import {LANDSCAPE_NAMES} from './landscape-names-data.mjs';
import {LW_LINES} from './living-world-lines.mjs';

export const LANDSCAPE_LABEL='SEEDED';
/** UI label for the home-world exception: the planet the beast lives on gets a place even below minHabitability. The exception is SEEDED; the recorded habitability is carried unchanged. */
export const HOME_WORLD_LANDSCAPE_LABEL='Home world · place SEEDED';
export const LANDSCAPE_KINDS=Object.freeze(['court','grove','sun_court','shore_camp','shrine','garden']);
export const LANDSCAPE_MODES=Object.freeze(['gather','shelter','sleep','empty']);
export const LANDSCAPE=Object.freeze({
 minHabitability:0.35,// below this the world gets no places (the home world is the one SEEDED exception)
 minSeparationRad:0.9,// min angular distance between two landscapes on one planet
 maxPerPlanet:2,
 secondAt:0.65,// habitability at which a second attempt is allowed
 worldRadiusM:27,// the ~27 m living world: pad metres -> radians
 padM:[6,10],
 maxWater:0.9,// land-bearing: planet.water below this
 mix:Object.freeze({sleep:1,shelter:0.6,gather:0.05,empty:0}),// lamp mode factors (spec section 4)
 draws:12,// per attempt: lat, lon, kindJitter, yaw, padScale, shelterKind, treeCount, treeSpread, lampCount, seatCount, nameA, nameB
});
/** World-field LEGEND biome -> kind (spec section 3). Savanna is a court with a dry tint (look pack: court_dry). Hostile biomes are absent: no landscape. */
export const KIND_BY_BIOME=Object.freeze({grassland:'court',savanna:'court',heartwood_forest:'grove',pine_forest:'grove',rainforest:'grove',sunflower_ring:'sun_court',beach:'shore_camp',crystal_moss:'shrine',paper_marsh:'garden'});
/** Fallback when the view has no world-field cell: the planet's own home biome (tiny-universe-view biomeOf) in LEGEND names. */
export const HOME_BIOME_LEGEND=Object.freeze({paper:'paper_marsh',sunflower:'sunflower_ring',moss:'crystal_moss',jelly:'deep_ocean',glacier:'glacier',ember:'ember_fields'});

const f4=x=>+x.toFixed(4);
const TAU=Math.PI*2;
const cl=(x,a,b)=>Math.max(a,Math.min(b,x));
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const norm=v=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l];};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
/** Unit direction from degrees lat/lon (same convention as the other seeded modules: y up). */
export function dirOf(latDeg,lonDeg){const la=latDeg*Math.PI/180,lo=lonDeg*Math.PI/180;return [Math.cos(la)*Math.cos(lo),Math.sin(la),Math.cos(la)*Math.sin(lo)];}
/** Tangent frame at n: east, north. */
function frame(n){let e=cross([0,1,0],n);if(Math.hypot(e[0],e[1],e[2])<1e-6)e=[1,0,0];e=norm(e);const no=norm(cross(n,e));return {e,no};}
/** The point `dist` radians from n toward `bearing` (0 = north, clockwise). Unit length. */
export function pointAt(n,bearing,dist){const {e,no}=frame(n);const s=Math.sin(dist),c=Math.cos(dist);const t=[e[0]*Math.sin(bearing)+no[0]*Math.cos(bearing),e[1]*Math.sin(bearing)+no[1]*Math.cos(bearing),e[2]*Math.sin(bearing)+no[2]*Math.cos(bearing)];return norm([n[0]*c+t[0]*s,n[1]*c+t[1]*s,n[2]*c+t[2]*s]);}
export const angleBetween=(a,b)=>Math.acos(cl(dot(a,b),-1,1));

/** The planet the beast lives on for the exception: most habitable with habitability > 0 (same rule as the growth module, kept local so neither imports the other). */
export function landscapeHomeWorld(u){const p=[...(u?.planets||[])].filter(x=>(+x.habitability||0)>0).sort((a,b)=>(+b.habitability||0)-(+a.habitability||0)||String(a.id).localeCompare(String(b.id)))[0];return p?p.id:null;}

/** Placement + composition, tick-independent. Optional o.biomeAt(planet, dir) returns a world-field LEGEND biome at the anchor (the view's biomeAt); without it the planet's home biome is used.
 *  o.home overrides the home-world exception planet (null = none). @param {{seed?:any,planets?:any[]}} u @param {{home?:string|null,biomeAt?:(p:any,dir:number[])=>string|null|undefined}} [o] */
export function seededLandscapes(u,o={}){
 const out=[];const seed=String(u?.seed??'tiny');const home=o.home===undefined?landscapeHomeWorld(u):o.home;
 for(const p of u?.planets||[]){
  const hab=+p.habitability||0;const isHome=p.id===home&&hab>0;
  const r=lwStream(seed+':landscapes:'+p.id);
  const D=[Array.from({length:LANDSCAPE.draws},()=>r()),Array.from({length:LANDSCAPE.draws},()=>r())];// both attempts drawn up front: skipping never shifts the next planet
  const qualifies=(+p.water||0)<LANDSCAPE.maxWater&&hab>=LANDSCAPE.minHabitability;
  if(!qualifies&&!isHome)continue;
  const exception=!qualifies&&isHome;
  const placed=[];
  const attempts=exception?1:hab>=LANDSCAPE.secondAt?2:1;
  for(let a=0;a<attempts&&placed.length<LANDSCAPE.maxPerPlanet;a++){
   if(a===1&&!placed.length)break;
   const d=D[a];const lat=f4((d[0]*2-1)*65),lon=f4((d[1]*2-1)*180);const n=dirOf(lat,lon);
   if(placed.some(q=>angleBetween(dirOf(q.lat,q.lon),n)<LANDSCAPE.minSeparationRad))continue;// consumes its draws, places nothing
   const biome=(o.biomeAt?o.biomeAt(p,n):null)||HOME_BIOME_LEGEND[biomeOf(p)]||null;
   let kind=KIND_BY_BIOME[biome]||null;if(!kind&&exception)kind='court';// the home world keeps a place even where its field biome is unmapped (the pocket ground is green)
   if(!kind)continue;
   const [m0,m1]=LANDSCAPE.padM;const radiusM=f4(m0+d[4]*(m1-m0));const bl=LANDSCAPE_NAMES.B[kind];
   const A=LANDSCAPE_NAMES.A;const name=A[Math.floor(d[10]*A.length)%A.length]+' '+bl[Math.floor(d[11]*bl.length)%bl.length];
   const ls={id:'landscape-'+p.id+'-'+placed.length,type:'landscape',planet:p.id,kind,name,lat,lon,yaw:f4(d[3]*TAU),radiusM,label:LANDSCAPE_LABEL,
    biome:biome||null,dry:biome==='savanna',jitter:f4(d[2]),recorded_habitability:hab,
    slots:{shelter:d[5]<0.5?'canopy':'stones',trees:Math.floor(d[6]*4),lamps:1+Math.floor(d[8]*3),seats:1+Math.floor(d[9]*3),treeSpread:f4(d[7])},
    ...(exception?{home_exception:true,home_label:HOME_WORLD_LANDSCAPE_LABEL}:{})};
   ls.anchors=landscapeAnchors(ls);
   placed.push(ls);
  }
  out.push(...placed);
 }
 return out;
}

/** Unit-direction anchors: play ring centre, shelter (inside the pad), lamp cluster, garden (pad rim, opposite the shelter; reserved for a growth node, never used here). */
export function landscapeAnchors(ls){
 const n=dirOf(ls.lat,ls.lon);const R=ls.radiusM/LANDSCAPE.worldRadiusM;const y=ls.yaw;
 return {play:n,shelter:pointAt(n,y,0.62*R),lamp:pointAt(n,y+0.35,0.7*R),garden:pointAt(n,y+Math.PI,0.92*R)};
}
/** Slot positions for the view: lamps around the shelter, seats on the ring, trees at the rim. Pure arithmetic on the landscape's own draws (no extra stream). */
export function landscapeSlots(ls){
 const n=dirOf(ls.lat,ls.lon);const R=ls.radiusM/LANDSCAPE.worldRadiusM;const y=ls.yaw;const s=ls.slots;
 const lamps=Array.from({length:s.lamps},(_,i)=>pointAt(n,y+(i-(s.lamps-1)/2)*0.5,0.7*R));
 const seats=Array.from({length:s.seats},(_,i)=>pointAt(n,y+Math.PI/2+i*(TAU/s.seats)*0.8,0.34*R));
 const trees=Array.from({length:s.trees},(_,i)=>pointAt(n,y+Math.PI+(i-(s.trees-1)/2)*0.9,(0.86+0.1*s.treeSpread*((i%2)?1:-1)*0.5+0.05)*R));
 return {lamps,seats,trees,shelter:landscapeAnchors(ls).shelter};
}

/** Pure life-mode from environment signals (spec section 4). env = {ins, storm, hasLife}; evaluated in this order: empty, shelter, sleep, gather. */
export function landscapeMode(ls,env){
 const {ins=1,storm=0,hasLife=true}=env||{};
 if(!hasLife)return 'empty';
 if(storm>=0.5)return 'shelter';
 if(ins<=0.05)return 'sleep';
 return 'gather';
}
const smooth=(a,b,x)=>{const t=cl((x-a)/(b-a),0,1);return t*t*(3-2*t);};
/** Gather<->sleep crossfade weight on world-field insolation (Cosmo's look pack: night_t = 1 - smoothstep(0.05, 0.35, ins)). 1 = full night. */
export const nightT=ins=>1-smooth(0.05,0.35,ins);
/** Lamp level 0..1.5-ish multiplier: nightFactor x lifeVolume x mode factor.
 *  DEVIATION (documented in the spec and by Cory's rule): spec section 4 says shelter lamps are on if ins < 0.35, but in a daytime storm nightFactor is 0 and the lamps would stay dark.
 *  So nf_eff=max(nightFactor, 0.5 * storm_t); a storm that sits on the planet lifts the lamps to at most half. Night values are unchanged. */
export function lampLevel({nightFactor=0,storm_t=0,lifeVolume=1,mode='gather'}={}){const nf=Math.max(nightFactor,0.5*cl(storm_t,0,1));return nf*lifeVolume*(LANDSCAPE.mix[mode]??0);}

const KIND_LABEL=Object.freeze({court:'court',grove:'grove',sun_court:'sun court',shore_camp:'shore camp',shrine:'shrine',garden:'garden'});
const pick=(pool,seed,key)=>{if(!Array.isArray(pool)||!pool.length)return null;const r=lwStream(seed+':landscape-line:'+key);return pool[Math.floor(r()*pool.length)%pool.length];};
const fill=(t,v)=>t==null?null:t.replace(/\{beast\}/g,v.beast||'The beast').replace(/\{place\}/g,v.place).replace(/\{planet\}/g,v.planet||'this world');
/** Authored notice for a mode (landscape_notices.<mode> (a top-level group: the authored lines are longer than creature_notices' toast limit and must stay exact)); the picks are seeded by (seed, place, n). */
export function landscapeNotice(ls,mode,{beast,planet,seed='tiny',n=0}={}){return fill(pick(LW_LINES.landscape_notices[mode],String(seed),ls.id+':'+mode+':'+n),{beast,place:ls.name,planet});}
export function landscapeTapLine(ls,{beast,planet,seed='tiny',n=0}={}){return fill(pick(LW_LINES.landscape_notices.tap,String(seed),ls.id+':tap:'+n),{beast,place:ls.name,planet});}
/** Zoom line: "{place} · {kind}" plus the live mode line, derived from landscapeMode (shelter text is the spec's; the others are the authored notice for that mode). */
export function landscapeZoom(ls,mode,{beast,planet,seed='tiny',n=0}={}){
 const title=ls.name+' · '+KIND_LABEL[ls.kind];
 const pool=LW_LINES.landscape_zoom?.[mode];// Emeth's short zoom lines (seeded pick); the longer authored notice is the fallback
 const line=pick(pool,String(seed),ls.id+':zoom:'+mode+(n?':'+n:''))?fill(pick(pool,String(seed),ls.id+':zoom:'+mode+(n?':'+n:'')),{beast,place:ls.name,planet}):mode==='shelter'?ls.name+' is sheltering from the storm.':landscapeNotice(ls,mode,{beast,planet,seed});
 return {title,line,mode};
}

// ---- LIFE LAYER (landscapes 3/3). View-model only; none of this is written into the engine JSON.
/** Which landscape is this life entry's home? A seeded pick from the entry's OWN key: lwStream(seed+':home:'+key) (never the growth or landscape streams). null when the list is empty. */
export function homeLandscapeId(seed,key,landscapes){const L=(landscapes||[]);if(!L.length)return null;return L[Math.floor(lwStream(String(seed)+':home:'+key)()*L.length)%L.length].id;}
/** The view model of the planet's life: a COPY of u.life where each entry gains `home_landscape` (u itself is never touched). Entries on a planet with no landscape get null. */
export function withHomeLandscapes(u,landscapes){return (u?.life||[]).map(l=>{const here=(landscapes||[]).filter(x=>x.planet===l.planet);return {...l,home_landscape:homeLandscapeId(u.seed,l.id,here)};});}
/** Roam targets for a mode, in the roam-brain SPOTS pattern: gather = play ring + seats; shelter/sleep = the shelter anchor; empty = none. */
export function landscapeTargets(ls,mode){const a=landscapeAnchors(ls);if(mode==='gather')return [a.play,...landscapeSlots(ls).seats];if(mode==='shelter'||mode==='sleep')return [a.shelter];return [];}
/** One resident's goal: {target (unit vector), arrive (radians)} or null (empty mode). Stable per (seed, key, mode); the huddle sits within the pack's 0.55 m cluster radius of the shelter. */
export function landscapeGoal(ls,mode,key,seed='tiny'){const T=landscapeTargets(ls,mode);if(!T.length)return null;const r=lwStream(String(seed)+':slot:'+ls.id+':'+key+':'+mode);const R=ls.radiusM/LANDSCAPE.worldRadiusM;
 if(mode==='gather'){const t=T[Math.floor(r()*T.length)%T.length];return {target:t,arrive:0.16*R};}
 const huddle=0.55/LANDSCAPE.worldRadiusM;return {target:pointAt(T[0],r()*TAU,Math.sqrt(r())*huddle),arrive:0.2*huddle+0.05*R};}
