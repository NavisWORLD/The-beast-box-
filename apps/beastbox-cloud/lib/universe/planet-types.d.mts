export const LAVA_K:number;
export function pickType(p:{atmosphere?:number;temperature_k:number;water?:number}):'moon'|'volcanic'|'desert'|'ice'|'temperate';
export const SPRITE_TINT:Record<string,number[]>;
export function glowSet(tempK:number):'orange'|'yellow'|'white'|'blue_white';
export function planetLod(d:number,R:number,fovDeg:number):{s:number;sprite:number;far:number;farAlpha:number;nearAlpha:number;atmo:number};
export function sunExposure(intensity:number,dist:number):number;
export function variantFor(id:string,rand:(s:string)=>()=>number):{lonDeg:number;tiltDeg:number;spinDegPerS:number;cloudLonDeg:number};
