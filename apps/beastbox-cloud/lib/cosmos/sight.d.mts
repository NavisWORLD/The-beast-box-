export const SIGHT_LABELS:Readonly<{world:string,visitor:string,absent:string}>;
export const WORLD_DAY_S:number;
export const SIGHT_PREV_S:number;
export const WORLD_ATMOSPHERE:number;
export function worldLightFrom(world:any,nowMs?:number|null):any|null;
export function visitorLightFrom(raw:any,nowMs?:number|null):any|null;
export function composeSight(o?:{world?:any,environment?:any,nowMs?:number|null,maxChars?:number}):{text:string,receipt:any};
