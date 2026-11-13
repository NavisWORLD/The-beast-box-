// One continuous zoom, read as named depth bands (Cory, Nov 12: "the 12D / cosmic-depth hooks drive the camera depth and LOD").
// The bands are a 12D model simulation depth scale: a designed visual projection of camera altitude, not physics.
// Pure math, no clock, no randomness. The living world reads it every frame; tests read it directly.
export const DEPTH_LABEL='Depth · 12D model simulation (visual projection, not physics)';
/** Camera altitude above the planet surface, in planet radii. */
export function altitudeOf(camLen,R){return Math.max(0,camLen/R-1);}
/** Band edges in planet radii (meadow is walking height, deep is past the moons). */
export const DEPTH_BANDS=Object.freeze([
 Object.freeze({id:'meadow',label:'Meadow',maxAlt:.08}),
 Object.freeze({id:'canopy',label:'Canopy',maxAlt:.25}),
 Object.freeze({id:'sky',label:'Sky',maxAlt:.5}),
 Object.freeze({id:'orbit',label:'Orbit',maxAlt:3}),
 Object.freeze({id:'deep',label:'Deep space',maxAlt:Infinity}),
]);
/** LOD fade edges (planet radii): ground cover shrinks away from canopy to sky; orbit shells come in over the same span; the 12D lattice trace shows from orbit out. */
export const DEPTH_LOD=Object.freeze({groundIn:.25,groundOut:.5,latticeIn:.3,latticeOut:1.2});
const sm=(a,b,x)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t);};
export function depthBand(alt){for(const b of DEPTH_BANDS)if(alt<b.maxAlt)return b;return DEPTH_BANDS[DEPTH_BANDS.length-1];}
/** Per-frame depth read: band plus 0..1 LOD weights. ground: ground cover scale; lattice: 12D lattice trace weight; orbit: orbit-shell weight. */
export function depthLOD(alt){
 const a=Math.max(0,Number(alt)||0);
 const ground=1-sm(DEPTH_LOD.groundIn,DEPTH_LOD.groundOut,a);
 return {alt:+a.toFixed(3),band:depthBand(a).id,ground,orbit:1-ground,lattice:sm(DEPTH_LOD.latticeIn,DEPTH_LOD.latticeOut,a)};
}
