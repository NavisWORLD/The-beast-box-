/** Near-lens safety for every dot particle in a scene:
 *  - PointsMaterial points get a hard pixel cap and shrink to nothing inside the lens radius;
 *  - pushCameraOut keeps the camera outside a minimum radius around each creature.
 *  (ShaderMaterial points carry the same cap/fade in their own shaders.) */
export const MAX_POINT_PX=40,FADE_NEAR=.35,FADE_FAR=1.1,LENS_RADIUS=1.0;
export const POINT_CAP_GLSL=`gl_PointSize=min(gl_PointSize,${MAX_POINT_PX.toFixed(1)})*smoothstep(${FADE_NEAR},${FADE_FAR},-mvPosition.z);`;
export function capScenePoints(root:any){root.traverse((o:any)=>{const m=o.material;if(!o.isPoints||!m||!m.isPointsMaterial||m.userData.lcCap)return;m.userData.lcCap=1;
 const prev=m.onBeforeCompile;m.onBeforeCompile=(sh:any,r:any)=>{prev?.call(m,sh,r);sh.vertexShader=sh.vertexShader.replace('#include <logdepthbuf_vertex>',POINT_CAP_GLSL+'\n#include <logdepthbuf_vertex>');};
 const key=m.customProgramCacheKey?.bind(m);m.customProgramCacheKey=()=>(key?key():'')+':lccap';m.needsUpdate=true;});}
/** Push `cam` (THREE.Vector3) out of any sphere {x,y,z,r}; returns how far it moved. */
export function pushCameraOut(cam:{x:number;y:number;z:number},bodies:{x:number;y:number;z:number;r?:number}[],R=LENS_RADIUS){let moved=0;
 for(const b of bodies){const rr=(b.r??0)+R;const dx=cam.x-b.x,dy=cam.y-b.y,dz=cam.z-b.z;const d=Math.hypot(dx,dy,dz);
  if(d<rr){const k=d>1e-4?(rr-d)/d:0;if(d>1e-4){cam.x+=dx*k;cam.y+=dy*k;cam.z+=dz*k;}else cam.y+=rr;moved+=rr-d;}}
 return moved;}
