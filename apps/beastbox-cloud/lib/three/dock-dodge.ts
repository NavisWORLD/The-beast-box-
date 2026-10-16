/**
 * Keeps the fixed bottom bars (mini player, sound dock, chat launcher) from covering a caption:
 * while `el` sits inside the bottom band of the viewport, <html data-dock-dodge> slides them away.
 */
const hits=new Set<HTMLElement>();
const sync=()=>{const r=document.documentElement;if(hits.size)r.setAttribute('data-dock-dodge','');else r.removeAttribute('data-dock-dodge');};
export function dockDodge(el:HTMLElement,band=140):()=>void{
 if(typeof window==='undefined')return()=>{};
 let raf=0;
 const check=()=>{raf=0;const r=el.getBoundingClientRect();const hit=r.bottom>innerHeight-band&&r.top<innerHeight;
  if(hit)hits.add(el);else hits.delete(el);sync();};
 const on=()=>{if(!raf)raf=requestAnimationFrame(check);};
 addEventListener('scroll',on,{passive:true});addEventListener('resize',on);check();
 return()=>{removeEventListener('scroll',on);removeEventListener('resize',on);if(raf)cancelAnimationFrame(raf);hits.delete(el);sync();};
}
