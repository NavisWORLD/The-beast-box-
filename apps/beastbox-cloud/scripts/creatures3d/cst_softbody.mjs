// CST soft-body relax for cloth props (Nyxbean's sack hat): reads {v:[[x,y,z]..],e:[[i,j]..],pin:[i..],head:{x,y,z,r},seed}
// from stdin, runs the repo's XPBD Verlet solver at 120 Hz under gravity + Lorenz-driven wind from the creature's CST state,
// with the head as a sphere collider and the band ring pinned, and writes the settled positions to stdout. Z-up.
import {createCSTState,stepCSTState,motionParams,verletPoint,verletIntegrate,solveDistance,solveSphereCollision,turbulence3} from '../../lib/physics/cst-integrator.mjs';
let raw='';process.stdin.on('data',d=>raw+=d).on('end',()=>{
 const J=JSON.parse(raw),S=createCSTState(J.seed||'res_nyxbean');
 const P=J.v.map(([x,y,z])=>verletPoint(x,y,z,1));for(const i of J.pin)P[i].w=0;
 const C=J.e.map(([i,j])=>[P[i],P[j],Math.hypot(P[i].x-P[j].x,P[i].y-P[j].y,P[i].z-P[j].z)]);
 const steps=J.steps||360,dt=1/120,g=J.gravity??-.7,stiff=J.compliance??2e-7,pr=J.pressure??1.4;
 const cen={x:0,y:0,z:0};for(const p of P){cen.x+=p.x/P.length;cen.y+=p.y/P.length;cen.z+=p.z/P.length;}
 for(let s=0;s<steps;s++){stepCSTState(S,dt);const m=motionParams(S);
  // gravity + CST wind (Lorenz direction), plus the 4D turbulence field (xyz + time) as cloth flutter
  for(const p of P){if(!p.w)continue;const t=turbulence3(p.x*9,p.y*9,p.z*9,s*dt,7);p.x+=t.x*m.turbulence*2e-6;p.z+=t.z*m.turbulence*2e-6;}
  // puffer loft: inflation pressure from the crown centroid, scaled by CST coherence (coherent = fuller, rounder puff)
  for(const p of P){if(!p.w)continue;const dx=p.x-cen.x,dy=p.y-cen.y,dz=p.z-cen.z,l=Math.hypot(dx,dy,dz)||1,k=pr*(.6+.6*S.ch.coherence)*dt*dt;p.x+=dx/l*k;p.y+=dy/l*k;p.z+=dz/l*k;}
  verletIntegrate(P,dt,{acc:{x:m.wind.x*.3,y:.9+m.wind.z*.3,z:g},damping:.04+.04*m.damping});
  for(let it=0;it<6;it++){for(const [a,b,r] of C)solveDistance(a,b,r,{compliance:stiff,dt});for(const p of P)solveSphereCollision(p,J.head);}}
 process.stdout.write(JSON.stringify(P.map(p=>[+p.x.toFixed(5),+p.y.toFixed(5),+p.z.toFixed(5)])));
});
