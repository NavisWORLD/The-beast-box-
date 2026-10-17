/** Shared living-core build cache: the marching-cubes body is built once per creature per page life
 * and reused by the Home roamer and the Cage residents. Phones get fewer fur shells. */
import {CREATURES} from './creatures.js';
import {attachSurfaceLife} from './surface-life';
const CACHE=new Map<string,Promise<any>>();
export const isLowDevice=()=>typeof navigator!=='undefined'&&(/iPhone|iPad|Android/i.test(navigator.userAgent)||((navigator as any).hardwareConcurrency||8)<=4);
export function getLivingCore(THREE:any,name:string,low=isLowDevice()):Promise<{LC:any;light:any}>{
 const key=name+(low?':low':'');let p=CACHE.get(key);
 if(!p){p=(async()=>{const {MarchingCubes}=await import('three/examples/jsm/objects/MarchingCubes.js');const {buildLivingCore}=await import('./living-core.js');
  const C=(CREATURES as any)[name];if(!C)throw new Error('no living-core config '+name);const opts={...C.opts};if(low&&opts.furShells)opts.furShells={...opts.furShells,layers:Math.min(6,opts.furShells.layers||6)};
  const LC=await buildLivingCore({THREE,MarchingCubes,src:'/living-core/'+C.src,opts});LC.setEmotion?.('calm');if(LC.forceMorph)LC.forceMorph(1);else LC.transform?.(1);
  // ?surf=0 shows the old surface (before/after review)
  if(!(typeof location!=='undefined'&&new URLSearchParams(location.search).get('surf')==='0'))(LC as any).__surf=attachSurfaceLife(THREE,LC,name,low);return {LC,light:C.light||{}};})();
  CACHE.set(key,p);p.catch(()=>CACHE.delete(key));}
 return p;
}
/** Explicit CST field: substep at 1/120 s or it diverges. */
export function stepLivingCore(LC:any,d:number){if(!(d>1e-4))return;const n=Math.max(1,Math.ceil(d*120));for(let i=0;i<n;i++)LC.step(d/n);LC.__surf?.step(d);}
/** World scale so a living-core body stands `h` units tall (particle pools park at -999, so no Box3). */
export const livingCoreScale=(LC:any,h=1.7)=>h/2/Math.max(.5,Math.abs(LC.footY||2.5));
/** Creatures that fly/float in the pocket (wings or serpent levitation). */
/** Believable world height for every living-core creature (cage grid cell = 0.75; library pedestal ≈ 0.3). */
export const LC_WORLD_H=.62;
export const LC_FLYERS=Object.freeze(['zeref','velvetcoil']);
/** Birth/morph particles are sized in screen pixels for the full-screen prototype; refit them to this body's world scale. */
export function fitLivingCoreParticles(LC:any,k:number,viewH:number){const u=LC?.pmat?.uniforms?.uSize;if(u)u.value=0.045*1.55*Math.max(200,viewH)*.85*k*.9;}
