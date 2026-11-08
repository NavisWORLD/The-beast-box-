// Height-exponential aerial perspective. Classic keeps FogExp2; this is the Genesis shader term.
export function hazeAmount(distance:number,height:number,density=.012,falloff=.35){
 const d=Math.max(0,distance),h=Math.max(0,height);
 return 1-Math.exp(-d*density*Math.exp(-h*falloff));
}

/** Horizon colour lifted a little toward the zenith. The sun direction only warms the result. */
export function hazeTint(sunDir:number[],horizon:number[],zenith:number[],drift=0){
 const h=horizon?.length===3?horizon:[.62,.74,.82];
 const z=zenith?.length===3?zenith:[.15,.35,.62];
 const up=Math.max(0,Math.min(1,(sunDir?.[1]??0)*.5+.5));
 const k=Math.pow(up,.45);
 const wobble=Math.sin(drift)*.04;
 return [0,1,2].map(i=>{
  const base=h[i]+(z[i]-h[i])*k;
  return Math.max(0,Math.min(1,base+wobble*(z[i]-h[i])));
 });
}

export const HAZE_GLSL=`float hazeAmt(float dist,float height,float density,float falloff){
 float d=max(dist,0.0);float h=max(height,0.0);
 return 1.0-exp(-d*density*exp(-h*falloff));
}`;
