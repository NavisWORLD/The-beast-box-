export function loadPrivateChat(beast:any,options?:{fetchImpl?:typeof fetch;signal?:AbortSignal;expectedOwner?:string}):Promise<{owner:string;id:string;seed:string;version:number;consented:boolean;rows:any[]}>;
export function savePrivateExchange(beast:any,exchange:any,options:{fetchImpl?:typeof fetch;signal?:AbortSignal;expectedOwner:string}):Promise<any>;
export function mergePrivateChat(local:any[],remote:any[]):any[];
export type PrivateChatQueueState={busy:boolean;pending:number;paused:boolean;error:string|null;lastSavedEvent:string|null};
export type PrivateChatBinding={key:string;owner:string;beast:any;enabled?:boolean;consented?:boolean};
export function createPrivateChatQueue(options?:{fetchImpl?:typeof fetch;onChange?:(state:PrivateChatQueueState)=>void;limit?:number}):{
 snapshot():PrivateChatQueueState;
 select(binding:PrivateChatBinding|null):void;
 enqueue(value:PrivateChatBinding&{exchange:any}):void;
 retry():Promise<void>;
 dispose():void;
};
