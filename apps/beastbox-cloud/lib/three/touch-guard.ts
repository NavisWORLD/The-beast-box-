/**
 * Touch guard for draggable 3D canvases (iPhone fix, Oct 2026).
 * Inside the element a one-finger drag rotates/explores and must not scroll the page:
 *  - touch-action:none so Safari doesn't start a pan/zoom gesture,
 *  - pointer capture so the drag keeps tracking when the finger leaves the canvas,
 *  - a non-passive touchmove that preventDefaults only while a drag that began inside is active.
 * Outside the element the page scrolls normally. Adds a small "drag to spin" affordance that fades after first use.
 */
export function guardCanvasTouch(el:HTMLElement,{hint='☝ Drag to spin · scroll outside the circle'}:{hint?:string|false}={}){
 el.style.touchAction='none';(el.style as any).webkitUserSelect='none';el.style.userSelect='none';el.dataset.touchGuard='on';
 let dragging=false;let chip:HTMLSpanElement|null=null;
 const fade=()=>{if(chip){chip.style.opacity='0';const c=chip;chip=null;setTimeout(()=>c.remove(),600);}};
 const isControl=(t:EventTarget|null)=>t instanceof Element&&!!t.closest('button,a,summary,input,select,textarea,label,[role="button"]');
 const down=(e:PointerEvent)=>{if(e.pointerType==='mouse'&&e.button!==0)return;if(isControl(e.target)){dragging=false;return;}dragging=true;try{el.setPointerCapture(e.pointerId);}catch{}fade();};
 const up=(e:PointerEvent)=>{dragging=false;try{if(el.hasPointerCapture?.(e.pointerId))el.releasePointerCapture(e.pointerId);}catch{}};
 const touchmove=(e:TouchEvent)=>{if(dragging&&e.cancelable)e.preventDefault();};
 el.addEventListener('pointerdown',down);el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);
 el.addEventListener('touchmove',touchmove,{passive:false});
 let timer=0;
 if(hint&&matchMedia('(pointer: coarse)').matches){
  chip=document.createElement('span');chip.textContent=hint;chip.setAttribute('aria-hidden','true');chip.dataset.touchHint='on';
  Object.assign(chip.style,{position:'absolute',left:'50%',bottom:'6%',transform:'translateX(-50%)',zIndex:'6',padding:'4px 10px',borderRadius:'999px',
   background:'#0b0a22cc',border:'1px solid #b9a2ff55',color:'#dcd2ff',font:'600 11px/1.3 system-ui,sans-serif',letterSpacing:'.03em',whiteSpace:'nowrap',
   pointerEvents:'none',transition:'opacity .5s',opacity:'1'});
  if(getComputedStyle(el).position==='static')el.style.position='relative';
  el.appendChild(chip);timer=window.setTimeout(fade,7000);
 }
 return ()=>{clearTimeout(timer);chip?.remove();el.removeEventListener('pointerdown',down);el.removeEventListener('pointerup',up);el.removeEventListener('pointercancel',up);el.removeEventListener('touchmove',touchmove);};
}
