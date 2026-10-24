export const MOONS_LABEL:string;export const MOON_SEED_TAG:'seeded';
export function rng(seed:string):()=>number;
export type Moon={id:string;planet:string;seeded:true;tag:'seeded';index:number;radiusFrac:number;aPlanetR:number;periodS:number;phase:number;incl:number;lonDeg:number};
export function seedMoons(universeSeed:string,planets:{id:string;radius_earth?:number}[]):Moon[];
export function moonOffset(m:Moon,t:number):{x:number;y:number;z:number;theta:number};
export function pickOccluder<T extends {x:number;y:number;z:number;r:number}>(p:{x:number;y:number;z:number},sunDir:{x:number;y:number;z:number},cands:T[]):T|null;
