/** "Gravity tunneling" depth for the Cage camera (cage look unchanged):
 *  1) mass-weighted follow: Zeref and nearby points of interest act as gravity wells; the focus has inertia and a small overshoot;
 *  2) dolly zoom: when Zeref accelerates or travels far, the camera pushes in while the FOV widens (45°→60°), then eases back;
 *  3) depth layers: near-lens drifting motes + glyphs ride with the camera (parallax against mid creatures and far beacons);
 *  5) desktop-only cheap depth of field focused on Zeref (skipped on phones / software GL);
 *  6) depth ripple: a slight FOV/lens pulse on the creature's frequency layer. */
type T=typeof import('three');
export const FOV_BASE=46,FOV_WIDE=60;
/** Pure helper (tested): keep the subject's apparent size while FOV widens → camera distance shrinks. */
export const dollyDistance=(d:number,fov0:number,fov:number)=>d*Math.tan(fov0*Math.PI/360)/Math.tan(fov*Math.PI/360);
export function createGravityCam(THREE:T,{camera,scene,renderer,low,dof}:{camera:any;scene:any;renderer:any;low:boolean;dof:boolean}){
 const F=new THREE.Vector3(),V=new THREE.Vector3(),tgt=new THREE.Vector3();let init=false,s=0,prev:{x:number;z:number}|null=null,spd=0,t=0;
 // near-lens layer (camera-anchored → strong parallax against the world)
 const N=low?28:64,pos=new Float32Array(N*3),seed=new Float32Array(N);for(let i=0;i<N;i++){seed[i]=Math.random();pos[i*3]=(Math.random()-.5)*1.6;pos[i*3+1]=(Math.random()-.5)*1.1;pos[i*3+2]=-(.55+Math.random()*1.4);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));
 const near=new THREE.Points(g,new THREE.PointsMaterial({size:.012,color:0xb9a2ff,transparent:true,opacity:.32,blending:THREE.AdditiveBlending,depthWrite:false,depthTest:false,fog:false}));
 near.renderOrder=20;near.frustumCulled=false;camera.add(near);
 // a few faint glyph motes (code / CST symbols) share the same drifting positions
 const gc=typeof document!=='undefined'?document.createElement('canvas'):null;let gm:any=null,glyphs:any=null;
 if(gc){gc.width=gc.height=64;const x=gc.getContext('2d')!;x.fillStyle='#fff';x.font='44px monospace';x.textAlign='center';x.textBaseline='middle';x.fillText('φ',32,34);
  const gg=new THREE.BufferGeometry();gg.setAttribute('position',new THREE.BufferAttribute(pos,3));gg.setDrawRange(0,Math.ceil(N/5));
  gm=new THREE.PointsMaterial({size:.05,map:new THREE.CanvasTexture(gc),color:0xc9b6ff,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false,depthTest:false,fog:false});
  glyphs=new THREE.Points(gg,gm);glyphs.renderOrder=21;glyphs.frustumCulled=false;camera.add(glyphs);}if(!camera.parent)scene.add(camera);
 const base=pos.slice();let lastCam=new THREE.Vector3().copy(camera.position);
 // optional desktop DOF
 let comp:any=null,bokeh:any=null;
 if(dof)void Promise.all([import('three/examples/jsm/postprocessing/EffectComposer.js'),import('three/examples/jsm/postprocessing/RenderPass.js'),import('three/examples/jsm/postprocessing/BokehPass.js')]).then(([E,R,B])=>{
  comp=new E.EffectComposer(renderer);comp.addPass(new R.RenderPass(scene,camera));bokeh=new B.BokehPass(scene,camera,{focus:6,aperture:.0018,maxblur:.0045});comp.addPass(bokeh);}).catch(()=>{comp=null;});
 return {
  /** Returns the eased focus point; `pull` 0..1 is how much the wells own the camera. */
  focus(dt:number,home:any,z:{x:number;z:number}|null,wells:{x:number;z:number}[],pull:number){
   if(!init){F.copy(home);init=true;}
   tgt.copy(home);
   if(z&&pull>0){let wx=z.x*3,wz=z.z*3,m=3;for(const w of wells){const d2=(w.x-z.x)**2+(w.z-z.z)**2;const mw=1.2*Math.exp(-d2/18);wx+=w.x*mw;wz+=w.z*mw;m+=mw;}
    tgt.x+=(wx/m-tgt.x)*pull;tgt.z+=(wz/m-tgt.z)*pull;}
   // underdamped spring → inertia + small overshoot (ζ≈0.55)
   const k=3.2,c=2*.55*Math.sqrt(k);V.addScaledVector(tgt.clone().sub(F),k*dt).multiplyScalar(Math.max(0,1-c*dt));F.addScaledVector(V,dt);
   if(z){if(prev){const v=Math.hypot(z.x-prev.x,z.z-prev.z)/Math.max(dt,1e-3);spd+=(v-spd)*Math.min(1,dt*3);}prev={x:z.x,z:z.z};}
   return F;},
  /** Dolly zoom + depth ripple. Returns camera distance and FOV. */
  lens(dt:number,zoom:number,far:number,beat:number){t+=dt;
   const want=Math.min(1,Math.max(0,spd*.9-.15)+Math.max(0,(far-3)/18));s+=(want-s)*Math.min(1,dt*(want>s?1.6:.6));
   const ripple=Math.sin(t*6.2832*1.3)*.35*beat;
   const fov=FOV_BASE+(FOV_WIDE-FOV_BASE)*s+ripple;return {fov,zoom:dollyDistance(zoom,FOV_BASE,fov)*(1-.12*s)};},
  step(dt:number){const d=camera.position.clone().sub(lastCam);lastCam.copy(camera.position);
   const q=camera.quaternion.clone().invert();d.applyQuaternion(q);
   for(let i=0;i<N;i++){const k=i*3;base[k]-=d.x*.25;base[k+1]-=d.y*.25+dt*.01*(seed[i]-.5);
    base[k]=((base[k]+.8)%1.6+1.6)%1.6-.8;base[k+1]=((base[k+1]+.55)%1.1+1.1)%1.1-.55;
    pos[k]=base[k]+Math.sin(t*.4+seed[i]*9)*.03;pos[k+1]=base[k+1]+Math.cos(t*.3+seed[i]*7)*.02;pos[k+2]=base[k+2];}
   g.attributes.position.needsUpdate=true;if(glyphs)glyphs.geometry.attributes.position.needsUpdate=true;},
  render(focusDist:number){if(comp&&bokeh){bokeh.uniforms.focus.value=focusDist;comp.render();}else renderer.render(scene,camera);},
  resize(w:number,h:number){comp?.setSize(w,h);},
  dispose(){camera.remove(near);if(glyphs){camera.remove(glyphs);glyphs.geometry.dispose();gm.map?.dispose();gm.dispose();}g.dispose();(near.material as any).dispose();comp?.dispose?.();}};
}
