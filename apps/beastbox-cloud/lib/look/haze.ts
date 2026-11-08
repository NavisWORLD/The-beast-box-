// Layered aerial perspective. Classic keeps FogExp2; this is the Genesis shader term.
// Far colour is the sky along the view, faded by 1 - exp(-d * sigma * exp(-y / H)).
import {skyAir} from './sky-math.ts';
export const HAZE_LAYERS=Object.freeze([
 {name:'near',density:.0045,falloff:1.15,weight:.4},
 {name:'mid',density:.0012,falloff:.4,weight:.35},
 {name:'far',density:.00035,falloff:.1,weight:.25},
]);

export const AERIAL_SIGMA=0.00135;
export const AERIAL_SCALE_H=48;

/** Height-exponential fade into the sky. 0 near the camera, about 1 on the far hills. */
export function aerialAmount(distance:number,height:number,sigma=AERIAL_SIGMA,scaleH=AERIAL_SCALE_H){
 const d=Math.max(0,distance),y=Math.max(0,height);
 return 1-Math.exp(-d*sigma*Math.exp(-y/scaleH));
}

/** Sky colour a far surface fades toward. The sun disc stays on the dome, so the hills do not fade into it. */
export function hazeColour(viewDir:number[],sunDir:number[],horizon:number[],zenith:number[],drift=0){
 return skyAir(viewDir,sunDir,horizon,zenith,drift,1,1);
}

export function hazeAmount(distance:number,height:number,density=.012,falloff=.35){
 const d=Math.max(0,distance),h=Math.max(0,height);
 return 1-Math.exp(-d*density*Math.exp(-h*falloff));
}

/** Three stacked bands. Near haze is thick and low; the far band carries the horizon. */
export function hazeStack(distance:number,height:number){
 const layers=HAZE_LAYERS.map(L=>({name:L.name,amount:hazeAmount(distance,height,L.density,L.falloff)}));
 const amount=Math.min(1,layers.reduce((s,L,i)=>s+L.amount*HAZE_LAYERS[i].weight,0));
 return {amount,layers};
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
}
float hazeStackAmt(float dist,float height){
 float a=hazeAmt(dist,height,${HAZE_LAYERS[0].density},${HAZE_LAYERS[0].falloff})*${HAZE_LAYERS[0].weight};
 a+=hazeAmt(dist,height,${HAZE_LAYERS[1].density},${HAZE_LAYERS[1].falloff})*${HAZE_LAYERS[1].weight};
 a+=hazeAmt(dist,height,${HAZE_LAYERS[2].density},${HAZE_LAYERS[2].falloff})*${HAZE_LAYERS[2].weight};
 return clamp(a,0.0,1.0);
}
float aerialAmt(float dist,float height){
 float d=max(dist,0.0);float y=max(height,0.0);
 return 1.0-exp(-d*${AERIAL_SIGMA}*exp(-y/${AERIAL_SCALE_H}.0));
}`;
