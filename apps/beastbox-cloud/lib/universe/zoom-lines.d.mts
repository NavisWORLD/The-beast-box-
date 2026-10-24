export const STAGE_RANK:Record<string,number>;
export function zoomLineKind(prev:string,next:string,o?:{blackHole?:boolean}):{kind:'zoom_out'|'zoom_in';key:string|null}|null;
export function doorLineKind(prevV:number,v:number):{kind:'zoom_out'|'zoom_in';key:string}|null;
export function zoomLine(kind:'zoom_out'|'zoom_in',key:string,seed:string,n?:number):string|null;
export const NOTICE_KEYS:readonly string[];
export function noticeLine(key:string,beast:string|null|undefined,seed:string,n?:number):string|null;
export function noticeGate(state:any,key:string,tMs:number,gapMs?:number,repeatMs?:number):{state:any;show:boolean};
