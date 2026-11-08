// Genesis post on the one renderer. ACES stays on the renderer. Exposure eases toward the
// sun elevation (the one clock), never a read of the framebuffer. Bloom is HIGH and GOD only.
// Software GL skips the chain. God rays, film grain and RGB shift stay out of this pass.
// Label: a designed screen effect, SIMULATED.
import {budgetFor} from './tiers.ts';
import {smoothstep} from './sun-tint.ts';
import {positiveSize} from './viewport.ts';

export const POST_LABEL='Post · SIMULATED';

export function exposureTarget(elevationDeg:number){
 const e=Math.sin((Number(elevationDeg)||0)*Math.PI/180);
 const up=smoothstep(-0.08,0.55,e);
 return 1.02-up*0.34;
}

/** L += (target-L) * min(1, 2 dt). dt is seconds from the caller. */
export function stepExposure(current:number,target:number,dt:number){
 const k=Math.min(1,Math.max(0,dt)*2);
 return current+(target-current)*k;
}

export function postPlan(tier:string,softGL=false){
 const heavy=!softGL;
 const bloom=heavy&&(tier==='HIGH'||tier==='GOD');
 const fxaa=heavy&&(tier==='MED'||tier==='HIGH'||tier==='GOD');
 return {
  label:POST_LABEL,
  aces:true,
  bloom,
  fxaa,
  bloomScale:tier==='GOD'?1:0.5,
  heavy:bloom||fxaa,
 };
}

export function bloomFor(plan:{bloom:boolean},elevationDeg:number){
 const e=Math.sin((Number(elevationDeg)||0)*Math.PI/180);
 const up=smoothstep(-0.05,0.45,e);
 // The pass sees linear colour, before ACES. Night used to fall to 0.4, and in orbit the
 // sun's world-Y is often low, so the land, the haze and every star crossed it and the
 // frame washed out. Stay above that scene and under the sun core (~3.6) and the eyes (1.5).
 return {
  strength:(0.55+(0.32-0.55)*up),
  threshold:(1.15+(1.45-1.15)*up),
  enabled:plan.bloom,
 };
}

type Chain={
 render:(sunWorld:unknown,elevDeg:number,dt:number,tier:string)=>boolean;
 setSize:(w:number,h:number)=>void;
 state:()=>{tier:string;exposure:number;bloom:boolean;fxaa:boolean;label:string;passes:string[]};
 dispose:()=>void;
};

export async function createGenesisPost(THREE:any,renderer:any,scene:any,camera:any,tierOf:()=>string):Promise<Chain>{
 const [{EffectComposer},{RenderPass},{ShaderPass},{UnrealBloomPass},{OutputPass},{FXAAShader}]=await Promise.all([
  import('three/examples/jsm/postprocessing/EffectComposer.js'),
  import('three/examples/jsm/postprocessing/RenderPass.js'),
  import('three/examples/jsm/postprocessing/ShaderPass.js'),
  import('three/examples/jsm/postprocessing/UnrealBloomPass.js'),
  import('three/examples/jsm/postprocessing/OutputPass.js'),
  import('three/examples/jsm/shaders/FXAAShader.js'),
 ]);
 let cur=tierOf()||'MED';
 let exposure=0.85;
 const composer=new EffectComposer(renderer);
 const size=new THREE.Vector2();
 let bloom:any=null,fxaa:any=null;
 const build=()=>{
  const plan=postPlan(cur,false);
  renderer.getSize(size);
  while(composer.passes.length)composer.removePass(composer.passes[0]);
  composer.addPass(new RenderPass(scene,camera));
  bloom=null;fxaa=null;
  if(plan.bloom){
   const k=plan.bloomScale;
   const b=bloomFor(plan,40);
   bloom=new UnrealBloomPass(new THREE.Vector2(Math.max(1,size.x*k),Math.max(1,size.y*k)),b.strength,0.4,b.threshold);
   composer.addPass(bloom);
  }
  if(plan.fxaa&&FXAAShader){
   fxaa=new ShaderPass(FXAAShader);
   const pr=Math.min(globalThis.devicePixelRatio||1,budgetFor(cur).dpr);
   fxaa.material.uniforms.resolution.value.set(1/Math.max(1,size.x*pr),1/Math.max(1,size.y*pr));
   composer.addPass(fxaa);
  }
  composer.addPass(new OutputPass());
  renderer.toneMapping=THREE.ACESFilmicToneMapping;
  const pr=Math.min(globalThis.devicePixelRatio||1,budgetFor(cur).dpr);
  composer.setPixelRatio(pr);
  if(positiveSize(size.x,size.y))composer.setSize(size.x,size.y);
 };
 build();
 return {
  render(sunWorld,elevDeg,dt,tier){
   if(tier&&tier!==cur){cur=tier;build();}
   const plan=postPlan(cur,false);
   exposure=stepExposure(exposure,exposureTarget(elevDeg),dt);
   renderer.toneMapping=THREE.ACESFilmicToneMapping;
   renderer.toneMappingExposure=exposure;
   if(bloom){
    const b=bloomFor(plan,elevDeg);
    bloom.strength=b.strength;
    bloom.threshold=b.threshold;
   }
   if(!plan.heavy)return false;
   void sunWorld;
   composer.render();
   return true;
  },
  setSize(w,h){
   const s=positiveSize(w,h);
   if(!s)return;
   composer.setSize(s.w,s.h);
   const plan=postPlan(cur,false);
   if(bloom)bloom.setSize(Math.max(1,s.w*plan.bloomScale),Math.max(1,s.h*plan.bloomScale));
   if(fxaa){
    const pr=Math.min(globalThis.devicePixelRatio||1,budgetFor(cur).dpr);
    fxaa.material.uniforms.resolution.value.set(1/Math.max(1,s.w*pr),1/Math.max(1,s.h*pr));
   }
  },
  state:()=>({tier:cur,exposure,bloom:!!bloom,fxaa:!!fxaa,label:POST_LABEL,passes:composer.passes.map((p:any)=>p.constructor?.name||'pass')}),
  dispose(){composer.dispose?.();},
 };
}
