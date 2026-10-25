type Store={put:(name:string,text:string)=>Promise<unknown>};
export const PACKET_PREFIX:string;export const PACKET_MAX_AGE_S:number;
export function savePacket(store:Store,packet:unknown,nowMs:number):Promise<{status:number;body:Record<string,unknown>}>;
export function latestStatus(store:{get:(name:string)=>Promise<string|null>},nowMs:number):Promise<{status:number;body:Record<string,unknown>}>;
