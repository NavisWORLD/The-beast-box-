export const SPARK_SEED:string;export const SPARK_JOB:string;export const SPARK_EPOCH_MS:number;export const BEAT_MS:number;
export const RECORDED_PAIRS:[string,number][];export function pulseHash(n:number):string;export function beatAt(ms:number):number;
export type SparkPulse={schema:string;label:'RECORDED';applies_to:string;honesty:string;source:{heart_seed_v11_sha256:string;ibm_job:string;backend:string;label:string};rule:string;beat:number;pulse_sha256:string;glow:number;question_pair:string;recorded_win_rate:number;next_beat_utc:string;at_utc:string};
export function sparkPulse(ms:number):SparkPulse;
