// GENESIS X planets (SEEDED look on SIMULATED planet data): neighbour planets in the sky, lit only by the one sun.
// Which planets carry rings and what colour their atmosphere rim is come from each planet's own numbers
// (radius_earth, atmosphere, temperature_k, water) plus a lwStream-style hash of its id. No random calls, no clock.
export const NEIGHBOUR_LABEL='SEEDED look on SIMULATED planets, lit by the one sun';
import {isRinglessWorld} from './ringed-planets.mjs';
const hash=(s)=>{let h=2166136261>>>0;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}return h/4294967296;};
/** ring plan for a shown list of planets: the three fixed worlds (home, desert, volcano) never get rings, even when biggest; otherwise the biggest always has rings; others when large (>=3.5 Earth radii) or by their id hash (1 in 4). */
export function ringPlan(planets){const list=planets||[];let big=-1,br=-1;list.forEach((p,i)=>{if(isRinglessWorld(p?.id))return;const r=+p?.radius_earth||0;if(r>br){br=r;big=i;}});
 return list.map((p,i)=>{if(isRinglessWorld(p?.id))return null;const h=hash(String(p?.id??i)+':rings');const on=i===big||(+p?.radius_earth||0)>=3.5||h<.25;if(!on)return null;
  return {inner:1.35+.25*hash(String(p?.id??i)+':ri'),outer:2.1+.5*hash(String(p?.id??i)+':ro'),tilt:.25+.6*hash(String(p?.id??i)+':tilt'),spin:6.2832*hash(String(p?.id??i)+':spin')};});}
/** atmosphere rim colour + strength from the planet's own atmosphere, temperature and water. Airless bodies get no rim. */
export function atmoRim(p){const a=Math.max(0,Math.min(1,+p?.atmosphere||0));if(a<.05)return {color:[0,0,0],strength:0};const t=+p?.temperature_k||288,w=Math.max(0,Math.min(1,+p?.water||0));
 const warm=Math.max(0,Math.min(1,(t-260)/240));const c=[.35+.55*warm,.55+.15*w-.1*warm,1-.6*warm];return {color:c.map(v=>+Math.max(0,Math.min(1,v)).toFixed(3)),strength:+(.35+.9*a).toFixed(3)};}
