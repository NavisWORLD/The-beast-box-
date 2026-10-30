export const RINGED_LABEL:string;export const NEVER_RINGS:readonly string[];export function isRinglessWorld(id:any):boolean;export function ringPresetFor(id:any):any;export function ringTier(t:string):any;
export const RING_SCATTER_G:number;export const RING_PEN:number;export const EARTHSHINE_CAP:number;
export function planetShadowOnRing(Q:number[],C:number[],R:number,sun:number[],pen?:number):number;
export function ringShadowOnPlanet(P:number[],C:number[],n:number[],sun:number[],R:number,inner:number,outer:number,opacity:number,band?:(u:number)=>number):number;
export function forwardScatter(V:number[],sun:number[],g?:number):number;
export function ringLook(id:any,tier:string):{preset:string;tint:number[];opacity:number;bands:number[];useBands:number;scatter:number;planetShadow:number;ringShadow:number};
export const RING_FRAG:string;export const RING_VERT:string;export const RING_SHADOW_DECL:string;export function withRingShadow(frag:string):string;export const RINGED_PACK_INFO:any;
