// Presentation-only camera poses for one Living World view.
// Reads traveler, beast and world positions. Returns a camera pose or null.
// Null means the caller keeps the camera it already computed.
import {VIEW_MODES} from './view-mode.mjs';

/** Order shown on the view-local switch: Orbit, Behind, First person. */
export const CAMERA_SWITCH_ORDER=Object.freeze(['orbit','behind','first']);
const EYE=0.47; // same 1.6 m eye the renderer uses (.47 world units)
const TRAV_H=.5;
const ORBIT_K=4.3;
const ORBIT_LOOK_K=.15;

function vec(x,y,z){return {x:+x||0,y:+y||0,z:+z||0};}
function clone(a){return vec(a?.x,a?.y,a?.z);}
function len(a){return Math.hypot(a.x,a.y,a.z);}
function scale(a,s){return {x:a.x*s,y:a.y*s,z:a.z*s};}
function add(a,b,s=1){return {x:a.x+b.x*s,y:a.y+b.y*s,z:a.z+b.z*s};}
function dot(a,b){return a.x*b.x+a.y*b.y+a.z*b.z;}
function cross(a,b){return {x:a.y*b.z-a.z*b.y,y:a.z*b.x-a.x*b.z,z:a.x*b.y-a.y*b.x};}
function norm(a){const l=len(a);return l>1e-8?scale(a,1/l):null;}
function mix(a,b,k){if(!a||k>=1)return clone(b);return {x:a.x+(b.x-a.x)*k,y:a.y+(b.y-a.y)*k,z:a.z+(b.z-a.z)*k};}
function placed(p){if(!p)return null;const c=clone(p);return len(c)>1e-6?c:null;}
function tangent(n,f){const t=add(f,n,-dot(f,n));return norm(t);}
function fallbackForward(n){return tangent(n,Math.abs(n.y)<.9?{x:0,y:1,z:0}:{x:1,y:0,z:0})||{x:1,y:0,z:0};}

/**
 * @param {string|null|undefined} mode orbit | behind | first, or null/'' for the unchanged camera
 * @param {{traveler?:{n?:object,f?:object,position?:object},beast?:{n?:object,f?:object,position?:object},radius?:number,ground?:number}} read
 * @returns {null|{mode:string,position:{x:number,y:number,z:number},up:{x:number,y:number,z:number},lookAt:{x:number,y:number,z:number}}}
 */
export function presentationCamera(mode,read){
 if(mode==null||mode==='')return null;
 if(!VIEW_MODES.includes(mode))return null;
 const radius=+read?.radius;
 if(!(radius>0))return null;
 const ground=Number.isFinite(+read?.ground)?+read.ground:0;
 const travelerN=norm(clone(read?.traveler?.n));
 const beastN=norm(clone(read?.beast?.n));
 const travelerF=clone(read?.traveler?.f);
 const beastF=clone(read?.beast?.f);
 const travelerP=placed(read?.traveler?.position);
 const beastP=placed(read?.beast?.position);
 const worldN=beastN||norm(beastP)||travelerN||norm(travelerP);
 if(!worldN)return null;
 if(mode==='orbit'){
  const position=scale(worldN,radius*ORBIT_K);
  const lookAt=beastP||scale(worldN,radius*ORBIT_LOOK_K);
  const up=Math.abs(worldN.y)>.92?{x:1,y:0,z:0}:{x:0,y:1,z:0};
  return {mode,position,up,lookAt};
 }
 if(mode==='behind'){
  const n=beastN||worldN;
  const f=tangent(n,beastF)||fallbackForward(n);
  const side=norm(cross(n,f))||fallbackForward(n);
  const anchor=beastP||scale(n,radius+ground);
  const position=add(add(add(anchor,n,TRAV_H*2.6),f,-2.7),side,-.55);
  const lookAt=add(add(anchor,n,TRAV_H*.9),f,1.6);
  return {mode,position,up:n,lookAt};
 }
 const n=travelerN||beastN||worldN;
 const f=tangent(n,travelerN?travelerF:beastF)||fallbackForward(n);
 const anchor=(travelerN?travelerP:null)||(travelerN?null:beastP)||scale(n,radius+ground);
 const position=add(anchor,n,EYE);
 const lookAt=add(position,f,10);
 return {mode,position,up:n,lookAt};
}

/**
 * Ease a view-local pose toward the target. Reduced motion snaps. A mode change snaps.
 * A null pose returns null so the caller leaves its camera alone. Never mutates prev or pose.
 */
export function stepPresentationCamera(prev,pose,{reduced=false,alpha=1}={}){
 if(!pose)return null;
 const same=!!(prev&&prev.mode===pose.mode);
 const k=reduced||!same?1:Math.max(0,Math.min(1,Number.isFinite(+alpha)?+alpha:1));
 const up=norm(mix(same?prev.up:null,pose.up,k))||clone(pose.up);
 return {mode:pose.mode,position:mix(same?prev.position:null,pose.position,k),up,lookAt:mix(same?prev.lookAt:null,pose.lookAt,k)};
}
