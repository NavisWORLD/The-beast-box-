// P1 post chain for the living world: render -> god rays -> bloom -> optics -> output (ACES, exposure 0.85 from the pack).
// All values come from Cosmo's p1post pack per tier. The sun is the ONE engine sun the view already uses; this file never moves it.
// Label: SEEDED look, a designed screen effect.
import {tierSettings,bloomThresholdPreExposure} from './post-tiers.mjs';
import {GOD_RAYS_FRAG,OPTICS_FRAG,PASS_VERT} from './post-shaders.mjs';
import {sunVisible,grainSeed} from './graphics-state.mjs';
export type PostChain={render:(sunWorld:any,sunElevDeg:number)=>void;setSize:(w:number,h:number)=>void;setTier:(t:string)=>void;tier:()=>string;state:()=>any;dispose:()=>void};
export async function createPostChain(THREE:any,renderer:any,scene:any,camera:any,tier:string):Promise<PostChain>{
  const [{EffectComposer},{RenderPass},{ShaderPass},{UnrealBloomPass},{OutputPass}]=await Promise.all([
    import('three/examples/jsm/postprocessing/EffectComposer.js'),import('three/examples/jsm/postprocessing/RenderPass.js'),
    import('three/examples/jsm/postprocessing/ShaderPass.js'),import('three/examples/jsm/postprocessing/UnrealBloomPass.js'),
    import('three/examples/jsm/postprocessing/OutputPass.js')]);
  let cur=tier,frame=0,last:any={};
  const composer=new EffectComposer(renderer);const size=new THREE.Vector2();
  let rays:any=null,bloom:any=null,optics:any=null;
  const build=()=>{
    const s=tierSettings(cur);renderer.getSize(size);
    while(composer.passes.length)composer.removePass(composer.passes[0]);
    composer.addPass(new RenderPass(scene,camera));
    rays=null;bloom=null;optics=null;
    if(s.god_rays.enabled&&s.god_rays.samples>0){rays=new ShaderPass({uniforms:{tDiffuse:{value:null},uSunPos:{value:new THREE.Vector2(.5,.5)},uDensity:{value:s.god_rays.density},uDecay:{value:s.god_rays.decay},uWeight:{value:s.god_rays.weight},uExposure:{value:s.god_rays.exposure},uSunVisible:{value:0},uGate:{value:new THREE.Vector2(s.god_rays.bright_gate[0],s.god_rays.bright_gate[1])}},vertexShader:PASS_VERT,fragmentShader:GOD_RAYS_FRAG(s.god_rays.samples)});composer.addPass(rays);}
    if(s.bloom.enabled){const k=s.bloom.resolution==='full'?1:.5;bloom=new UnrealBloomPass(new THREE.Vector2(size.x*k,size.y*k),s.bloom.strength,s.bloom.radius,bloomThresholdPreExposure(cur));composer.addPass(bloom);}
    const o=s.optics;if(o.grain>0||o.chromatic_aberration>0||o.vignette>0||o.edge_blur>0){optics=new ShaderPass({uniforms:{tDiffuse:{value:null},uAberration:{value:o.chromatic_aberration},uGrain:{value:o.grain},uVignette:{value:o.vignette},uEdgeBlur:{value:o.edge_blur},uGamma:{value:o.gamma},uGrainSeed:{value:0}},vertexShader:PASS_VERT,fragmentShader:OPTICS_FRAG});composer.addPass(optics);}
    composer.addPass(new OutputPass());
    renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=o.exposure;
    const dpr=Math.min(globalThis.devicePixelRatio||1,s.budget.max_dpr)*s.budget.render_scale;composer.setPixelRatio(dpr);composer.setSize(size.x,size.y);
  };
  build();
  const v=new THREE.Vector3();
  return {
    render(sunWorld,sunElevDeg){frame++;
      if(rays&&sunWorld){v.copy(sunWorld).project(camera);const behind=v.z>1;const vis=behind?0:sunVisible(sunElevDeg,[v.x,v.y],0);rays.uniforms.uSunVisible.value=vis;rays.uniforms.uSunPos.value.set((v.x+1)/2,(v.y+1)/2);last.sunVisible=+vis.toFixed(3);}
      if(optics)optics.uniforms.uGrainSeed.value=grainSeed(frame);
      composer.render();},
    setSize(w,h){composer.setSize(w,h);if(bloom)bloom.setSize(w,h);},
    setTier(t){if(t!==cur){cur=t;build();}},tier:()=>cur,
    state:()=>({tier:cur,frame,passes:composer.passes.map((p:any)=>p.constructor?.name||'pass'),rays:!!rays,bloom:!!bloom,optics:!!optics,...last}),
    dispose(){composer.dispose?.();},
  };
}
