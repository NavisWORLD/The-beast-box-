/** Read-only WebGL receipt. The page patch installs only when the URL has ?gldebug=1.
 *  With the flag off, every export returns before touching a canvas, a prototype, or the DOM.
 *  It counts and records. It never refuses a view and it never calls Math.random. */
export type GlDebugEvent={t:string;kind:'create'|'lose'|'restore'|'dispose';view:string;renderer:string|null;id:number};
export type GlDebugView={id:number;view:string;renderer:string|null;lost:boolean;disposed:boolean};
export type GlDebugSnap={live:number;views:GlDebugView[];events:GlDebugEvent[];flag:true};

export function glDebugEnabled(search?:string):boolean{
 try{
  const q=search!==undefined?search:(typeof location!=='undefined'?location.search:'');
  return /(?:^|[?&])gldebug=1(?:&|$)/.test(q);
 }catch{return false;}
}

export function createGlDebug(clock:()=>string=()=>new Date().toISOString()){
 const views=new Map<number,GlDebugView>();
 const events:GlDebugEvent[]=[];
 let next=1;
 let pending='unattributed';
 const push=(kind:GlDebugEvent['kind'],view:string,id:number,renderer:string|null)=>{
  events.push({t:clock(),kind,view,renderer,id});
  if(events.length>80)events.splice(0,events.length-80);
 };
 return {
  owner(view:string){pending=String(view||'unattributed');},
  create(view:string|undefined,renderer:string|null){
   const id=next++;const name=view||pending;pending='unattributed';
   views.set(id,{id,view:name,renderer,lost:false,disposed:false});
   push('create',name,id,renderer);return id;
  },
  lose(id:number){const v=views.get(id);if(!v)return;v.lost=true;push('lose',v.view,id,v.renderer);},
  restore(id:number){const v=views.get(id);if(!v)return;v.lost=false;push('restore',v.view,id,v.renderer);},
  dispose(view:string){
   const open=[...views.values()].reverse().find(v=>v.view===view&&!v.disposed);
   if(!open){push('dispose',view,0,null);return;}
   open.disposed=true;push('dispose',view,open.id,open.renderer);
  },
  snapshot():GlDebugSnap{
   const list=[...views.values()].map(v=>({...v}));
   return {live:list.filter(v=>!v.lost&&!v.disposed).length,views:list,events:events.map(e=>({...e})),flag:true};
  },
 };
}

type DebugHandle=ReturnType<typeof createGlDebug>;
const g=globalThis as {__glDebug?:DebugHandle};

export function pageGlDebug():DebugHandle|null{
 if(!glDebugEnabled())return null;
 if(!g.__glDebug)g.__glDebug=createGlDebug();
 return g.__glDebug;
}

/** Name the view that is about to create a renderer. No-op when the flag is off. */
export function glDebugOwner(view:string){pageGlDebug()?.owner(view);}
/** Record a renderer.dispose(). No-op when the flag is off. */
export function glDebugDispose(view:string){pageGlDebug()?.dispose(view);}

let patched=false;
/** Patch canvas.getContext only after the flag has already been checked. */
export function installGlDebug(){
 if(!glDebugEnabled()||patched||typeof HTMLCanvasElement==='undefined')return;
 const book=pageGlDebug();if(!book)return;
 patched=true;
 const orig=HTMLCanvasElement.prototype.getContext;
 HTMLCanvasElement.prototype.getContext=function(this:HTMLCanvasElement,type:string,...rest:unknown[]){
  const gl=orig.apply(this,[type,...rest] as never) as WebGLRenderingContext|null;
  if(gl&&/webgl/i.test(String(type))){
   let renderer:string|null=null;
   try{const d=gl.getExtension('WEBGL_debug_renderer_info');renderer=d?String(gl.getParameter(d.UNMASKED_RENDERER_WEBGL)):null;}catch{renderer=null;}
   const id=book.create(undefined,renderer);
   const lost=()=>book.lose(id), restored=()=>book.restore(id);
   this.addEventListener('webglcontextlost',lost);this.addEventListener('webglcontextrestored',restored);
  }
  return gl;
 } as typeof HTMLCanvasElement.prototype.getContext;
}
