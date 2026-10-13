export const PRIVATE_SCHEMA:string;
export const LIMITS:Readonly<Record<string,number>>;
export type PrivateIO={get:(name:string)=>Promise<{text:string;etag:string}|null>;put:(name:string,text:string,options?:any)=>Promise<string>;list:(prefix:string)=>Promise<string[]>;delete:(name:string,options:any)=>Promise<any>};
export function azurePrivateIO(config:any):PrivateIO;
export class PrivateCosmos {
 scope:string;io:PrivateIO;limits:Record<string,number>;
 constructor(io:PrivateIO,options?:{scope?:string;limits?:Record<string,number>});
 ownerPath(owner:string):string;
 assertOwner(owner:string):Promise<{text:string;etag:string}>;
 admit(owner:string):Promise<void>;
 read(owner:string,id:string):Promise<any>;
 create(owner:string,profile:any,eventId:string,options?:{qbeastText?:string|null;quantumGenesis?:any}):Promise<any>;
 update(owner:string,id:string,action:any,eventId:string,version:number):Promise<any>;
 applyQvm(owner:string,id:string,plan:any,receipt:any,eventId:string,version:number,secret:string):Promise<any>;
 recover(owner:string,id:string):Promise<any>;
 remove(owner:string,id:string):Promise<{deleted:boolean}>;
 revoke(owner:string):Promise<{revoked:boolean}>;
}
