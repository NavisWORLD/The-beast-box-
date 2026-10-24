export const OCEAN_LABEL:string;
export type School={id:string;kind:'fish'|'ray'|'whale';n:number[];radius:number;count:number;speed:number;phase:number;hue:number;size:number};
export function tangentBasis(n:number[]):number[][];
export function oceanLife(seed:string|number,isWater:(n:number[])=>boolean,o?:{schools?:number;rays?:number;whales?:number;plankton?:number;life?:number}):{label:string;schools:School[];plankton:{n:number[];p:number}[]};
export function memberAt(s:School,i:number,t:number):number[];
export function headingAt(s:School,i:number,t:number):number[];
export function surfacing(s:School,t:number):number;
export function planktonGlow(p:number,t:number,night:number):number;
