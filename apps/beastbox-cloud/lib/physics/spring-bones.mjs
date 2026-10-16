/**
 * Spring bones for skinned creatures (tail, ears, wings, crescent charm), solved with the shared
 * CST integrator: Verlet tips + XPBD length constraints + stiffness pull toward the animated rest
 * pose, with Lorenz wind / chaos turbulence / phi phase from motionParams(). Pure math on plain
 * {x,y,z}; a thin adapter (applyToBones) writes rotations into THREE.Bone objects.
 */
import {verletPoint,verletIntegrate,solveDistance,solveSphereCollision,turbulence3,fnv1a} from './cst-integrator.mjs';

/** chain: rest positions in world space [{x,y,z}...], first point is the pinned root. */
export function createSpringChain(rest,{stiffness=.35,drag=.12,gravity=-.4,name='chain'}={}){
 const pts=rest.map((p,i)=>verletPoint(p.x,p.y,p.z,i===0?0:1));
 const len=rest.slice(1).map((p,i)=>Math.hypot(p.x-rest[i].x,p.y-rest[i].y,p.z-rest[i].z));
 return {name,pts,len,rest:rest.map(p=>({...p})),stiffness,drag,gravity,seed:fnv1a(name)};
}
/**
 * One fixed step. rest = current animated (target) world positions of the chain points.
 * mp = motionParams(cstState). colliders = spheres.
 */
export function stepSpringChain(ch,dt,{rest=ch.rest,mp=null,colliders=[],t=0,iterations=2}={}){
 const k=ch.stiffness*(mp?mp.stiffness:1),drag=Math.min(.9,ch.drag/(mp?mp.damping:1)*1.0);
 const wind=mp?mp.wind:{x:0,y:0,z:0},turb=mp?mp.turbulence:0;
 // root follows animation exactly
 const r0=rest[0];Object.assign(ch.pts[0],{x:r0.x,y:r0.y,z:r0.z,px:r0.x,py:r0.y,pz:r0.z});
 verletIntegrate(ch.pts,dt,{acc:{x:wind.x,y:ch.gravity+wind.y,z:wind.z},damping:drag});
 for(let i=1;i<ch.pts.length;i++){const p=ch.pts[i],q=rest[i],ph=mp?mp.phase+i*mp.phaseStep:0;
  const n=turbulence3(q.x,q.y,q.z,t+ph,ch.seed);const a=turb*.04*i/ch.pts.length;
  p.x+=(q.x-p.x)*k+n.x*a;p.y+=(q.y-p.y)*k+n.y*a;p.z+=(q.z-p.z)*k+n.z*a;}
 for(let it=0;it<iterations;it++){
  for(let i=1;i<ch.pts.length;i++)solveDistance(ch.pts[i-1],ch.pts[i],ch.len[i-1],{dt});
  for(const s of colliders)for(let i=1;i<ch.pts.length;i++)solveSphereCollision(ch.pts[i],s);
 }
 return ch;
}
/**
 * Write the simulated chain into THREE bones: each bone rotates so its child direction matches
 * the simulated segment. bones[i] corresponds to pts[i]; restDirs are captured at bind time.
 */
export function applyToBones(THREE,ch,bones){
 const q=new THREE.Quaternion(),from=new THREE.Vector3(),to=new THREE.Vector3(),pw=new THREE.Quaternion();
 for(let i=0;i<bones.length-1&&i<ch.pts.length-1;i++){
  const b=bones[i],c=bones[i+1];if(!b||!c)continue;
  b.quaternion.copy(b.userData.bindQuat||(b.userData.bindQuat=b.quaternion.clone()));
  b.updateMatrixWorld(true);
  const bw=new THREE.Vector3().setFromMatrixPosition(b.matrixWorld),cw=new THREE.Vector3().setFromMatrixPosition(c.matrixWorld);
  from.copy(cw).sub(bw).normalize();
  to.set(ch.pts[i+1].x-ch.pts[i].x,ch.pts[i+1].y-ch.pts[i].y,ch.pts[i+1].z-ch.pts[i].z).normalize();
  if(!Number.isFinite(to.x))continue;
  q.setFromUnitVectors(from,to);
  b.parent.getWorldQuaternion(pw);const wq=new THREE.Quaternion();b.getWorldQuaternion(wq);
  const nw=q.multiply(wq);b.quaternion.copy(pw.invert().multiply(nw));
  b.updateMatrixWorld(true);
 }
}
