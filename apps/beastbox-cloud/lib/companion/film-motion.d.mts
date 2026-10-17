export type Persona={hop:number;walk:number;curiosity:number;fidget:number;tempo:number;source:'seed+labelled-counts'|'recorded-seed'|'id-only'};
export type Pose={x:number;z:number;lift:number;sx:number;sy:number;heading:number;head:number;lean:number;tail:number;ear:number;state:string};
export function prng(seed:string):()=>number;
export function countsEntropy(counts:Record<string,number>|null|undefined):number|null;
export function motionPersona(o?:{id?:string;seed?:string|null;counts?:Record<string,number>|null}):Persona;
export function createActor(p:Persona,o?:{x?:number;z?:number;radius?:number;seed?:string;universe?:number}):any;
export function stepActor(a:any,dt:number,ctx?:{lookAt?:{x:number;z:number}|null;reduced?:boolean}):Pose;
export const STATES:string[];
