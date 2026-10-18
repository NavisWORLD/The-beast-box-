/** Surface-aligned grounding: an analytic downward ray against every walkable surface (cage floor,
 * floating-island tops, planet spheres, tree branches). Returns the first hit below `p` (highest surface). */
/** @param {{x:number,y:number,z:number}} p @param {{floorY?:number,worlds?:any[],branches?:any[]}} [o] */
export function groundRay(p,{floorY=-.07,worlds=[],branches=[]}={}){
  let best={y:floorY,n:{x:0,y:1,z:0},kind:'floor'};
  for(const w of worlds){const dx=p.x-w.x,dz=p.z-w.z,h2=dx*dx+dz*dz;
    if(w.kind==='planet'){if(h2<w.r*w.r){const y=w.y+Math.sqrt(w.r*w.r-h2);if(y<=p.y+.5&&y>best.y)best={y,n:{x:dx/w.r,y:(y-w.y)/w.r,z:dz/w.r},kind:'planet'};}}
    else if(h2<w.r*w.r){const y=w.y+w.top;if(y<=p.y+.5&&y>best.y)best={y,n:{x:0,y:1,z:0},kind:'island'};}}
  for(const b of branches){// capsule top surface (only near-horizontal limbs are walkable)
    const ax=b.b.x-b.a.x,az=b.b.z-b.a.z,L2=ax*ax+az*az;if(L2<1e-6)continue;const t=Math.max(0,Math.min(1,((p.x-b.a.x)*ax+(p.z-b.a.z)*az)/L2));
    const cx=b.a.x+ax*t,cz=b.a.z+az*t,d=Math.hypot(p.x-cx,p.z-cz);if(d>b.r)continue;const cy=b.a.y+(b.b.y-b.a.y)*t,y=cy+Math.sqrt(b.r*b.r-d*d);
    if(y<=p.y+.5&&y>best.y)best={y,n:{x:(p.x-cx)/b.r,y:(y-cy)/b.r,z:(p.z-cz)/b.r},kind:'branch'};}
  return best;
}
/** Point on a planet surface after walking `arc` radians from the top along heading `h`. */
export function planetWalk(c,r,arc,h){const s=Math.sin(arc),n={x:s*Math.cos(h),y:Math.cos(arc),z:s*Math.sin(h)};
  return {pos:{x:c.x+n.x*r,y:c.y+n.y*r,z:c.z+n.z*r},n};}
/** Foot plant: snap the base to the surface (never float or sink beyond tol) unless airborne. */
export const plantFoot=(baseY,surfY,air,tol=.002)=>air>.5?baseY:Math.abs(baseY-surfY)<=tol?baseY:surfY;
/** Grounded↔airborne blend target from travel phase. */
export const airTarget=phase=>phase==='go'||phase==='back'?1:0;
