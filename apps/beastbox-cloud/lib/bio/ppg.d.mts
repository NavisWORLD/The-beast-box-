export const PPG_RULES:Readonly<{fs_hz:number;settle_s:number;min_duration_s:number;min_beats:number;min_sqi:number;min_bpm:number;max_bpm:number;min_red:number;min_red_minus_green:number;refractory_s:number;min_hrv_ibis:number}>;
export type PpgResult={valid:boolean;reason:string|null;bpm:number|null;hrv_rmssd_ms:number|null;sqi:number;beats:number;duration_s:number;fs_hz:number;red_mean?:number;green_mean?:number|null;red_ac_dc?:number;ibi_cv?:number};
export function analysePpg(input:{t:number[];v:number[];g?:number[]|null},rules?:typeof PPG_RULES):PpgResult;
export function resampleUniform(t:number[],v:number[],fs?:number):{x:number[];fs:number};
export const PPG_REASONS:Readonly<Record<string,string>>;
