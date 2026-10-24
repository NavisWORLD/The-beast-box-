export const STAR_VISUAL:Readonly<{pulseAmp:number;shimmerPhaseRate:number;sizeBase:number;sizeMin:number;sizeMax:number;remnantGlow:number}>;
export type EngineChannels={chaos:number;coherence:number;tick:number};
export function engineChannels(F:any):EngineChannels;
export function starVisual(star:{temperature_k?:number;luminosity?:number;remnant?:string|null},engineState?:Partial<EngineChannels>,distance?:number):{colorRGB:[number,number,number];corona:{intensity:number;noiseScale:number;shimmer:number;phase:number};pulse:number;brightness:number;apparentSize:number;remnant:string|null};
