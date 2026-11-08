// A viewport of 0×0 must not reach the renderer, the composer, or a render target.
// EffectComposer.setSize(0, 0) allocates a framebuffer with a zero-size attachment.
// WebGL then reports GL_INVALID_FRAMEBUFFER_OPERATION until the context is lost,
// and the canvas stays black until a reload.

export function positiveSize(w:number,h:number):{w:number;h:number}|null{
 const W=Number(w),H=Number(h);
 if(!(W>0)||!(H>0)||!Number.isFinite(W)||!Number.isFinite(H))return null;
 return {w:W,h:H};
}

type SizeTarget={setSize:(w:number,h:number,...rest:never[])=>void};

/** Resize one target. Returns false, and does not call setSize, when either side is missing. */
export function guardedSetSize(target:SizeTarget|null|undefined,w:number,h:number):boolean{
 const s=positiveSize(w,h);
 if(!s||!target)return false;
 target.setSize(s.w,s.h);
 return true;
}

type ViewportParts={
 renderer?:{setSize:(w:number,h:number,updateStyle?:boolean)=>void}|null;
 composers?:Array<{setSize:(w:number,h:number)=>void}|null|undefined>;
 targets?:Array<{setSize:(w:number,h:number)=>void}|null|undefined>;
 camera?:{aspect:number;updateProjectionMatrix:()=>void}|null;
};

/**
 * Apply a layout size to the renderer, every composer and render target, and the camera.
 * A 0×0 reading is ignored so the previous complete framebuffer stays on screen.
 */
export function applyViewport(w:number,h:number,parts:ViewportParts):boolean{
 const s=positiveSize(w,h);
 if(!s)return false;
 parts.renderer?.setSize(s.w,s.h,false);
 for(const c of parts.composers||[])c?.setSize(s.w,s.h);
 for(const t of parts.targets||[])t?.setSize(s.w,s.h);
 if(parts.camera){
  parts.camera.aspect=s.w/s.h;
  parts.camera.updateProjectionMatrix();
 }
 return true;
}
