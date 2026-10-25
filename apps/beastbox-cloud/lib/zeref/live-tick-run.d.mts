export const RUN_SCHEMA:string;
export function runLiveTickLoop(o:{io:Record<string,any>;clock:{now():number;sleep(ms:number):Promise<void>};runSeconds:number;batchSeconds?:number;log?:(...a:unknown[])=>void}):Promise<{ok:boolean;reason?:string;batches:number;seconds_run?:number}>;
