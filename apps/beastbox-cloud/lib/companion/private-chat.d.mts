export function loadPrivateChat(beast:any,options?:{fetchImpl?:typeof fetch;signal?:AbortSignal;expectedOwner?:string}):Promise<{owner:string;id:string;seed:string;version:number;consented:boolean;rows:any[]}>;
export function savePrivateExchange(beast:any,exchange:any,options:{fetchImpl?:typeof fetch;signal?:AbortSignal;expectedOwner:string}):Promise<any>;
export function mergePrivateChat(local:any[],remote:any[]):any[];
