/** GL budget (ONE UNIVERSE round two, P0): a live WebGL context counter, one entry per mounted 3D view.
 *  It COUNTS and REPORTS only; it never refuses a view. Pure bookkeeping: no clock, no Math.random, no network.
 *  Readable at window.__glBudget.snapshot() for receipts. Callers must go through safeGlBudget() so that a
 *  throwing or missing module leaves every view behaving exactly as before (fail soft, per view). */
export type GlEntry={id:number;view:string;soft:boolean;lost:boolean};
export type GlBudget={acquire(view:string,opts?:{soft?:boolean}):{id:number;lost(v:boolean):void;release():void};live():number;snapshot():{live:number;lost:number;views:GlEntry[]}};
export function createGlBudget():GlBudget{let next=1;const m=new Map<number,GlEntry>();
 return {acquire(view,opts){const id=next++;m.set(id,{id,view:String(view),soft:!!opts?.soft,lost:false});
   return {id,lost(v){const e=m.get(id);if(e)e.lost=!!v;},release(){m.delete(id);}};},
  live(){let n=0;m.forEach(e=>{if(!e.lost)n++;});return n;},
  snapshot(){const views=[...m.values()].map(e=>({...e}));return {live:views.filter(e=>!e.lost).length,lost:views.filter(e=>e.lost).length,views};}};}
const NOOP={id:0,lost(){},release(){}};
/** Fail-soft wrapper: any throw from the loader or the budget becomes a no-op handle. Never throws. */
export function safeGlBudget(load:()=>GlBudget|null|undefined){let b:GlBudget|null=null;try{b=load()||null;}catch{b=null;}
 return {acquire(view:string,opts?:{soft?:boolean}){if(!b)return NOOP;try{const h=b.acquire(view,opts);return {id:h.id,lost(v:boolean){try{h.lost(v);}catch{}},release(){try{h.release();}catch{}}};}catch{return NOOP;}},
  live():number|null{try{return b?b.live():null;}catch{return null;}}};}
/** Page-wide shared budget (created lazily, exposed for receipts). */
export function pageGlBudget():GlBudget{const w:any=typeof window!=='undefined'?window:globalThis;if(!w.__glBudget)w.__glBudget=createGlBudget();return w.__glBudget;}
/** Per-view renderer creation guard: returns the renderer, or null so THIS view can fall back to its 2D land.
 *  A failure here never propagates, so a neighbouring view is unaffected. */
export function tryCreateGl<T>(create:()=>T):{ok:true;value:T}|{ok:false;error:string}{try{const v=create();if(v==null)return {ok:false,error:'no context'};return {ok:true,value:v};}catch(e:any){return {ok:false,error:String(e?.message||e)};}}
