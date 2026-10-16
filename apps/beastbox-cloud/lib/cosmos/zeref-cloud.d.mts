import type {StorageConfig} from './azure-blob.mjs';
export const ZEREF_RAWRPHOS_ID:string;export const ZEREF_DIR:string;
export function storeLesson(cfg:StorageConfig,record:any):Promise<boolean>;
export function syncZerefCloud(cfg:StorageConfig,o:{pin:any;releases:any[]}):Promise<any>;
