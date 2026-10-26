export const FOAM:Readonly<Record<string,number>>;
export type FoamField={W:number;H:number;N:number;tick:number;born:Float32Array;age:Float32Array;foam:Float32Array;drift:number[];dirs:Float32Array;gate:Float32Array;sea:any};
export function createFoamField(F:any):FoamField;
export function stepFoam(f:FoamField,F:any,sea?:any):FoamField;
export function syncFoam(f:FoamField,F:any,maxSteps?:number):number;
export function foamAt(f:FoamField,F:any,d:number[]):number;
export function foamStats(f:FoamField,F:any):{cover:number;peak:number;waterCells:number;wind:number;dir:number;tick:number};
export function foamBytes(f:FoamField,out?:Uint8Array):Uint8Array;
