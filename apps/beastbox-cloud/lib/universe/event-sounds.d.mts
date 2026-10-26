export const SOUND:{stormEdges:number[];growthStep:number;minGapTicks:Record<string,number>;maxGain:number};
export type SoundState={boomPhase:string;stormBand:number;growthMark:number|null;last:Record<string,number>;primed?:boolean};
export function initialState():SoundState;
export function detectEvents(state:SoundState|null,ch:{tick:number;boomPhase?:string;boomTerm?:number;storm:number;grow:number}):{state:SoundState;events:{kind:string;magnitude:number;tick:number}[]};
export function recipe(kind:string,magnitude:number):null|{kind:string;parts:{wave:string;freq:number;freqEnd:number;at:number;dur:number;gain:number}[];noise:null|{dur:number;gain:number;lp:number}};
export function noiseSamples(n:number,seed?:number):Float32Array;
