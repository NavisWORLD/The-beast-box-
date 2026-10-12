export type StorageConfig={mode:'key'|'sas';containerUrl:string;account?:string;key?:string;sas?:string;container?:string};
export function storageConfig(env?:Record<string,string|undefined>):StorageConfig|null;
export function ensureContainer(cfg:StorageConfig):Promise<boolean>;
export function getBlob(cfg:StorageConfig,name:string):Promise<{text:string;etag:string|null}|null>;
export function putBlob(cfg:StorageConfig,name:string,text:string,o?:{contentType?:string;ifNoneMatch?:string;ifMatch?:string}):Promise<string|null>;
export function deleteBlob(cfg:StorageConfig,name:string,o:{ifMatch:string}):Promise<boolean>;
export function listBlobs(cfg:StorageConfig,prefix:string,o?:{max?:number}):Promise<string[]>;
