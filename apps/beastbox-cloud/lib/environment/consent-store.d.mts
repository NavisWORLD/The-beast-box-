export type EnvStore={get(name:string):Promise<string|null>;put(name:string,text:string):Promise<unknown>;del(name:string):Promise<unknown>};
export const ENV_PREFIX:string;export const CONSENT_SCHEMA:string;
type R={status:number;body:Record<string,any>};
export function saveEnvironment(store:EnvStore,userKey:string,raw:unknown,nowMs:number):Promise<R>;
export function readEnvironment(store:EnvStore,userKey:string,nowMs:number):Promise<R>;
export function revokeEnvironment(store:EnvStore,userKey:string):Promise<R>;
