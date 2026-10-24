export const BH_LABEL:'SEEDED';export const BH_SCALE:number;export const BH_RADIUS_K:number;
export type SeededBH={id:string;label:'SEEDED';size:number;radius:number;mass:number;x:number;y:number;z:number;diskInner:number;diskOuter:number;tilt:number;spin:number};
export function seededBlackHoles(u:{seed?:any;stars?:any[]}|null|undefined):SeededBH[];
export function orbitOmega(bh:SeededBH,r:number):number;
export function seededInfall(bh:SeededBH,seed:any,n?:number):{r:number;a0:number;h:number;w:number;hot:number}[];
