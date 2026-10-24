export const DOOR_FAR:number,DOOR_NEAR:number,DOOR_PRELOAD:number;
export function ss(a:number,b:number,x:number):number;
export function doorProgress(ratio:number):number;
export function doorPreload(ratio:number):boolean;
export function altFull(Rm:number):number;
export function groundAlpha(altM:number,Rm:number):number;
export function doorZoomStep(z:number,dir:number,step?:number):{z:number;leave:boolean};
