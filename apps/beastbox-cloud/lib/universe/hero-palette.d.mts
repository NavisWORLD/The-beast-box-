export function planetType(p:{atmosphere:number;temperature_k:number;water:number}):'moon'|'desert'|'temperate'|'ice'|'volcanic';
export function palette(p:{atmosphere:number;temperature_k:number;water:number;hue?:number}):{type:string;class:string;hero_role:string;hero:number[];colours:Record<string,number[]|null>;weights:Record<string,number>;tilt:number;waterRamp:null|{shallow:number[];mid:number[];deep:number[]}};
export function biomeHero(type:string,biomeId:string):string|null;
export function heroLegend(type:string,biomes:{id:string;rgb:string}[]):string[];
