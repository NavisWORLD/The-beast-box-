// GENESIS X horizon terrain (SEEDED look, DERIVED aerial haze) from Cosmo's horizonterrain pack: the flat first-person patch, the R1-R4
// ridges, and two far layers F5 (9 km) and F6 (18 km) that fade into the live sky horizon. Each ridge ring is world-fixed and only recentres
// on the camera after the camera has moved 5% of that ring's distance, so near ridges slide past far ones as you walk (depth holds).
// Lit only by the one sun. Pure functions: no random calls, no clock. A designed look, not a survey of a real place.
import {HORIZON_PACK as P} from './horizon-terrain-data.mjs';
export const HORIZON_LABEL='SEEDED layered terrain, DERIVED aerial haze, lit by the one sun';
export const HORIZON_TIERS=Object.freeze(['LOW','MED','HIGH','GOD']);
export const HORIZON_LAYERS=Object.freeze(P.layers.map(l=>Object.freeze({...l})));
/** the layer ids a quality tier draws (unknown tier -> MED) */
export function horizonLayerIds(tier){return (P.tiers[tier]||P.tiers.MED).layer_ids.slice();}
/** the far layers (beyond the R1-R4 ridges already on main) a tier adds */
export function farLayersFor(tier){const ids=horizonLayerIds(tier);return HORIZON_LAYERS.filter(l=>/^F\d/.test(l.id)&&ids.includes(l.id));}
/** aerial fade at distance d metres: 1 - exp(-k d) */
export function aerialFade(d){return 1-Math.exp(-Math.max(0,d)*P.aerial.k_per_m);}
/** recentre rule: keep the anchor until the camera is more than 5% of the layer distance away, then snap to the camera. Returns the new anchor (same object when kept). */
export function recentreAnchor(anchor,cam,distanceM,mPerUnit=1){const lim=.05*distanceM*mPerUnit;const dx=cam[0]-anchor[0],dy=cam[1]-anchor[1],dz=cam[2]-anchor[2];
 return dx*dx+dy*dy+dz*dz>lim*lim?[cam[0],cam[1],cam[2]]:anchor;}
/** a fixed phase triple for a layer from its seed tag (FNV hash, no stream draws, so older layers keep their seeded shapes) */
export function layerPhase(tag){const out=[];for(let k=0;k<3;k++){let h=2166136261>>>0;const s=tag+'|ph|'+k;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)>>>0;}out.push(+(h/4294967296*6.2832).toFixed(4));}return out;}
/** vertex estimate for a tier (patch grid + ridge rings), from the pack formula */
export function vertexEstimate(tier){const t=P.tiers[tier]||P.tiers.MED;return (t.patch_grid+1)**2+(t.layers-1)*t.ridge_segments*t.ridge_rows;}
export function vertexBudget(tier){return (P.tiers[tier]||P.tiers.MED).vertex_budget;}
export const HORIZON_AERIAL=P.aerial;export const HORIZON_PACK_INFO=Object.freeze({label:P.label,honesty:P.honesty,seed:P.seed,version:P.version});
