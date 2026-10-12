import type {StorageConfig} from './azure-blob.mjs';
export const MAX_REGISTERED:number;export const DEFAULT_BATCH:number;
export function registerBeast(cfg:StorageConfig,raw:unknown):Promise<{ok:boolean;status:number;error?:string;registered?:boolean;already?:boolean;id?:string}>;
export function readBeast(cfg:StorageConfig,id:string,o?:{limit?:number}):Promise<any>;
export function listRegistered(cfg:StorageConfig):Promise<string[]>;
export function planBatch(cfg:StorageConfig,o?:{batch?:number;skip?:string[]}):Promise<any>;
export function applyBatch(cfg:StorageConfig,plan:any,receipts:any[],o?:{now?:string}):Promise<any[]>;
export function mirrorZeref(cfg:StorageConfig,o:any):Promise<void>;
