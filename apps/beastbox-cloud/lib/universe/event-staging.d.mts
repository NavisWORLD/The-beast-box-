export const PHASES:readonly string[];
export function phaseT(phase:string,u:number):number;
export function boomStage(star:any,eventTick:number,tick:number,distanceAu:number,sunUp?:number):null|{phase:string;u:number;t:number;intensity:number;skyTerm:number;shellFrac:number;shellRadiusAu:number;ring:{angDeg:number;alpha:number;outer:number[];inner:number[];shadow:number[]};waterLit:{mix:number;colour:number[];underMax:number};bloom:{radiusFrac:number;colour:number[];gain:number;halo:number[]};label:string};
export function stageBooms(list:any[],tick:number,sunUp?:number):null|{stage:NonNullable<ReturnType<typeof boomStage>>;dir:number[]|null;star:any};
export function limbPoint(bearing:number[],camDir:number[]):number[]|null;
