export const STORM_LABEL:'SEEDED';export const STORM_MIN_ATMOSPHERE:number;
export type SeededStorm={id:string;type:'storm';planet:string;intensity:number;lifetime:number;born:number;label:'SEEDED';kind:string;lat:number;lon:number;night:boolean};
export function seededStorms(u:{seed?:any;planets?:any[];storms?:any[]}):SeededStorm[];
export function allStorms(u:{seed?:any;planets?:any[];storms?:any[]}):any[];
