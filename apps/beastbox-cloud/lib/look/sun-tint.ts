// Black-body tint for the one sun. Tanner Helland, the same fit as Cory's Genesis Engine.
// K = 2000 + 4500 * smoothstep(-0.05, 0.4, sin(elevation)). The rig is wrapped, not edited.
// Label: the sun is SEEDED. This file does not move the sun or write the world.
import {blackBodyToRGB} from '../universe/genesis-sun.mjs';

export const SUN_LABEL='Sun · SEEDED';

export function smoothstep(edge0:number,edge1:number,x:number){
 const t=Math.min(1,Math.max(0,(x-edge0)/(edge1-edge0)));
 return t*t*(3-2*t);
}

/** Kelvin from the one sun's elevation in degrees. Noon settles at 6500 K. A low sun stays warm. */
export function sunKelvinFromDeg(elevationDeg:number){
 const e=Math.sin((Number(elevationDeg)||0)*Math.PI/180);
 return 2000+4500*smoothstep(-0.05,0.4,e);
}

export function sunTintFor(elevationDeg:number){
 const kelvin=sunKelvinFromDeg(elevationDeg);
 const rgb=blackBodyToRGB(kelvin) as [number,number,number];
 return {label:SUN_LABEL,kelvin,rgb};
}

type Rig={sunElevationDeg?:number};

/** Copy of a lightRigFor result with a sunColour multiplier. The input rig is left as it was. */
export function tintRig<T extends Rig>(rig:T,base:[number,number,number]){
 const tint=sunTintFor(rig?.sunElevationDeg??0);
 const sunColor:[number,number,number]=[
  base[0]*tint.rgb[0],
  base[1]*tint.rgb[1],
  base[2]*tint.rgb[2],
 ];
 return {...rig,sunColor,tint};
}
