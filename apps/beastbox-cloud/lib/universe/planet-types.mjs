// Which Cosmo planet type a genesis planet gets, plus the LOD maths from ZOOM_GUIDE.md. Pure, seeded, no Math.random.
// Rule = pick() in the pack's pmodels.py, with ONE change (documented, Cory wants real land): the lava cutoff is 1500 K
// (silicate melts), not 700 K. The pack's rule makes 10 of 17 recorded planets volcanic; 700-1500 K worlds are hot desert here.
export const LAVA_K=1500;
export function pickType(p){
  if((p.atmosphere??0)<0.05)return'moon';
  const T=p.temperature_k;
  if(T>=LAVA_K)return'volcanic';
  if(T>=700)return'desert';   // pack: volcanic
  if(T<=150)return'ice';
  if(T<=350)return(p.water??0)>=0.15?'temperate':'ice';
  return'desert';
}
// mean albedo of each type's far map (computed from the 512x256 albedo; tints the far point sprite)
export const SPRITE_TINT={temperate:[0.387,0.604,0.58],desert:[0.673,0.626,0.504],ice:[0.739,0.847,0.894],volcanic:[0.303,0.192,0.214],moon:[0.414,0.361,0.429]};
export function glowSet(tempK){return tempK<4700?'orange':tempK<6200?'yellow':tempK<10000?'white':'blue_white';}
const ss=(a,b,x)=>{const t=Math.min(Math.max((x-a)/(b-a),0),1);return t*t*(3-2*t);};
// ZOOM_GUIDE planetLod: s = tan(angularRadius)/tan(fov/2). sprite+far+near weights always sum to 1.
export function planetLod(d,R,fovDeg){
  const x=Math.min(R/Math.max(d,1e-9),0.999999),s=(x/Math.sqrt(1-x*x))/Math.tan(fovDeg*Math.PI/360);
  const a=ss(0.004,0.012,s),b=ss(0.30,0.55,s);
  return{s,sprite:1-a,far:a*(1-b),farAlpha:a,nearAlpha:b,atmo:ss(0.01,0.03,s)};
}
// Cory's inverse-square star light (genesis-sun.mjs sunIntensity), exposure-compressed the way Cosmo's sun_light_recipe does it
// (sqrt, clamp .35..1.6): irradiance at distance R relative to a planet at 1 AU (R=9).
export function sunExposure(intensity,dist){const rel=intensity/(2.2*81)*(81/Math.max(dist*dist,1));return Math.min(1.6,Math.max(0.35,Math.sqrt(rel)));}
// seeded variants for planets not in the pack's planet_assignments.json
export function variantFor(id,rand){const r=rand('planet-variant:'+id);return{lonDeg:r()*360,tiltDeg:r()*35,spinDegPerS:0.5+r()*3,cloudLonDeg:r()*360};}
