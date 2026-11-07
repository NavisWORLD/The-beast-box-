export const ONE_WORLD_KEY:string;export const ONE_WORLD_TICK_MS:number;export const ONE_WORLD_TICK_CAP:number;
export type WorldClock={seed:string;get():any;subscribe(f:(u:any,prev:any)=>void):()=>void;start():WorldClock;stop():void;running():boolean;setPaused(p:boolean):void;paused():boolean;step():void};
export function worldClockCount():number;
export function createWorldClock(o:{genesis:any;grow:(u:any,n:number)=>any;storage?:Pick<Storage,'getItem'|'setItem'>|null;tickMs?:number;cap?:number;setTimer?:(f:()=>void,ms:number)=>any;clearTimer?:(id:any)=>void}):WorldClock;
export function oneWorldClock(o?:Parameters<typeof createWorldClock>[0]):WorldClock|null;
export function currentWorldClock():WorldClock|null;
export function whenWorldClock():Promise<WorldClock>;
