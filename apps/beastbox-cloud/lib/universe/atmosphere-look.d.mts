export function atmoClass(a:number):'thin'|'mid'|'thick';
export function limbRim(a:number):{enabled:boolean;thicknessFrac:number;gain:number;cls:string};
export function limbAt(a:number,cosL:number):{alpha:number;colour:number[]};
export function fogMul(a:number,moisture:number,storm:number):number;
export function stormHaze(a:number,storm:number):{mix:number;colour:number[]};
export function hazeFor(o:{atmo:number;sunElevSin:number;nightFactor:number;moisture?:number;storm?:number}):{enabled:boolean;cls:string;colour:number[];density:number;cap:number;mul:number;stormMix:number;stormColour:number[]};
export function hazeMixAt(h:any,d:number):number;
