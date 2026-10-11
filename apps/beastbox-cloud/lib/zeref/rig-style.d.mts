export type Skin={canonical:boolean;fur:string[];furSolid:string;lid:string;stroke:string;ear:string[];iris:string[];wing:string[];moon:string[];tail:string[];beans:string;brow:string;mouth:string;accent:string;glow:string;features:{wings:boolean;moonHorns:boolean;crescent:boolean;horns:boolean;tailTip:string}};
export const ZEREF_SKIN:Skin;
export function isZerefBeast(o?:{id?:string;name?:string}):boolean;
export function skinFromGenome(gen:any,o?:{id?:string;name?:string}):Skin;
export function seedFromGenome(gen:any):import('./zeref-mind.mjs').ZerefSeed|null;
