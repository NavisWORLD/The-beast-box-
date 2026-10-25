export function unit(x:number,lo:number,hi:number):number;
export function heartFeatures(p:any):Record<string,number>;
export function audioFeatures(p:any):Record<string,number>|null;
export function buildFeaturePosts(p:any):{kind:string;opt_in:true;features:Record<string,number>}[];
export const FEED_NOTE:string;
