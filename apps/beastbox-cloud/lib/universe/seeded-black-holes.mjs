// Seeded black holes for the Tiny Universe (Oct 24 2026). The recorded genesis has no black hole (stars/planets only; remnants appear
// only if the simulated growth makes one), so this adds ONE, drawn only from lwStream(seed+':blackhole:'+i) (seed = recorded IBM
// ibm_marrakesh counts). The numbers are Cory's from his a.html createBlackHole(): size 15-25, distance 1000-3000, height +-100,
// mass = size*5000, accretion disk RingGeometry(size*1.2, size*3), disk colour mix(orange, violet, radius*2) * hash noise.
// His scene is ~6x wider than ours, so lengths are scaled by SCALE. Every entry is label:'SEEDED' so the UI never calls it recorded.
import {lwStream} from './living-world.mjs';
export const BH_LABEL='SEEDED';
export const BH_SCALE=0.16;      // Cory's world units -> this scene's units (his 1000-3000 -> 160-480, past the star field)
export const BH_RADIUS_K=0.2;    // Cory's size 15-25 -> radius 3-5 here
/** @param {{seed:any,stars?:any[]}} u */
export function seededBlackHoles(u){
 if((u?.stars||[]).some(s=>s.remnant==='black_hole'))return []; // a real remnant already exists: never add a second kind
 const seed=String(u?.seed??'tiny'),out=[];
 for(let i=0;i<1;i++){
  const r=lwStream(seed+':blackhole:'+i);const d=[r(),r(),r(),r(),r(),r()];
  const size=+(15+d[0]*10).toFixed(3),dist=(1000+d[1]*2000)*BH_SCALE,angle=d[2]*Math.PI*2,y=(d[3]*200-100)*BH_SCALE;
  out.push({id:'seeded-bh-'+i,label:BH_LABEL,size,radius:+(size*BH_RADIUS_K).toFixed(3),mass:+(size*5000).toFixed(1),
   x:+(Math.cos(angle)*dist).toFixed(3),y:+y.toFixed(3),z:+(Math.sin(angle)*dist).toFixed(3),diskInner:1.2,diskOuter:3,tilt:+((d[4]-0.5)*0.9).toFixed(4),spin:+(0.04+d[5]*0.08).toFixed(4)});
 }
 return out;
}
/** Keplerian angular speed (rad/s) around a seeded hole at radius r (scene units): w = sqrt(G*M/r^3), G*M normalised so the disk edge (3R) takes 30 s per turn. */
export function orbitOmega(bh,r){const edge=bh.radius*bh.diskOuter,w0=2*Math.PI/30;return Math.sqrt((w0*w0*edge**3)/(r**3));}
/** Orbiting material (Cory's gravity: bodies fall in on Kepler orbits). Positions come from lwStream only. */
export function seededInfall(bh,seed,n=160){
 const r=lwStream(String(seed)+':bh-infall:'+bh.id);const out=[];
 for(let i=0;i<n;i++){const d=[r(),r(),r(),r()];const rad=bh.radius*(1.25+d[0]*d[0]*3.2);out.push({r:+rad.toFixed(3),a0:+(d[1]*Math.PI*2).toFixed(4),h:+((d[2]-0.5)*bh.radius*0.12).toFixed(4),w:+orbitOmega(bh,rad).toFixed(5),hot:+d[3].toFixed(3)});}
 return out;
}
