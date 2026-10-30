export const FLASH_LABEL:string;export const FLASH_SAFETY:any;export function flashTier(t:string):any;export function stormCount(field:any):number|null;export function lightningRate(s:number|null):number;
export function limitFlashes(times:number[]):number[];export function strikesInMinute(seed:string,planet:string,T:number,storms:number|null):number[];export function strikesNear(seed:string,planet:string,t:number,storms:number|null):number[];
export function skyFlashEnvelope(age:number):number;export function lightningAt(seed:string,planet:string,t:number,storms:number|null,tier:string,reduced?:boolean):{sky:number;bolt:number;boltSeed:number;glow:number;strikes:number;label:string};
export function boltPath(seed:number):number[][];export function shimmerAt(tick:number|null,prev:number|null,tier:string,reduced?:boolean):{on:boolean;level:number;burstTick:number|null;particles?:number;label:string};
export function nebulaRamp(u:number):number[];export const FLASH_PACK_INFO:any;
