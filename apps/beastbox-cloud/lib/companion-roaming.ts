/**
 * Screen-safe deterministic roam target selection.
 * The entire engine is decorative, does not access sensors or permissions,
 * and runs without model inference or external services.
 */
export type Rect={left:number;top:number;width:number;height:number};
export type Spot=Rect&{id:string};
const GAP=10;
export function rectanglesIntersect(a:Rect,b:Rect,gap=GAP):boolean{
 if([a.left,a.top,a.width,a.height,b.left,b.top,b.width,b.height].some(n=>!Number.isFinite(n)))return true;
 return a.left<b.left+b.width+gap&&a.left+a.width+gap>b.left&&
        a.top<b.top+b.height+gap&&a.top+a.height+gap>b.top;
}
export function selectSafeRoamSpot(
 width:number,height:number,exclusions:Rect[],tick=0
):Spot|null{
 if(!Number.isFinite(width)||!Number.isFinite(height)||
    width<320||height<400||!Number.isSafeInteger(tick)||tick<0)return null;
 const size=width<680?78:width<900?102:138;
 const edge=width<680?10:24;
 const left=edge,right=Math.max(edge,width-size-edge);
 const ceiling=width<680?Math.max(95,height*.33):Math.max(105,height*.19);
 const center=height*.53,bottom=Math.min(height-size-80,height*.74);
 const all:Spot[]=[
  {id:'bottom-right',left:right,top:bottom,width:size,height:size},
  {id:'middle-right',left:right,top:center,width:size,height:size},
  {id:'top-right',left:right,top:ceiling,width:size,height:size},
  {id:'bottom-left',left,top:bottom,width:size,height:size},
  {id:'middle-left',left,top:center,width:size,height:size}
 ];
 const candidates=all.filter(p=>
  p.top>=10 && p.top+p.height<=height-48 &&
  exclusions.every(e=>!rectanglesIntersect(p,e))
 );
 return candidates.length?candidates[tick%candidates.length]:null;
}
