export const LAND:Readonly<Record<string,any>>;
export function snowAmount(type:string,tempK?:number):number;
export function snowCover(a:{snowAmount:number;normalY?:number;rockiness?:number;noise?:number}):number;
export function wetnessTarget(moisture:number,baseline:number):number;
export function wetnessStep(prev:number,target:number,dayLengthTicks?:number,dtTicks?:number):number;
export function groundTint(base:number[],o?:{snowTint?:number[];cover?:number;wet?:number}):number[];
export function wetSheen(wet:number,roughness:number,f0?:number):{roughness:number;f0:number;on:number};
