export const OCEAN3:Readonly<Record<string,any>>;
export function bayFrom(rand:()=>number):{bearing:number;halfWidth:number;innerM:number;outerM:number};
export function oceanAt(o:{field?:any;storm?:number;day?:number;sunElev?:number}):{label:string;motion:string;dir:number;wind:number;storm:number;chop:number;whitecap:number;ampM:number;rough:number;glint:number;glintWidth:number;glintColor:number[];darken:number;day:number};
export function waveLayers():number[][];
export function inBayWater(bay:{bearing:number;halfWidth:number;innerM:number},x:number,z:number,margin?:number):boolean;
export function landArcAngle(bay:{bearing:number;halfWidth:number;innerM:number},rM:number,theta:number,margin?:number):number;
