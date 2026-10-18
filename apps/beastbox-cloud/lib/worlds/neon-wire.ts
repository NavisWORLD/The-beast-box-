// Neon wireframe overlay (Cory's depth reference): thin self-lit cyan/white lines layered on top of the
// existing fur/palette. Edges = silhouette fresnel; contours = object-space iso-lines (screen-space AA via
// fwidth so they stay 1–2 px crisp at any depth); density + brightness rise at features (high curvature).
// Distance legibility: uNeonDist brightens the network as the creature gets farther away.
type T=typeof import('three');
export const NEON=Object.freeze({color:[.55,.95,1.],white:[1,1,1],farBoost:.9,near:4,far:40});
export const neonDistGain=(d:number)=>1+NEON.farBoost*Math.min(1,Math.max(0,(d-NEON.near)/(NEON.far-NEON.near)));
export type NeonU={uNeon:{value:number};uNeonDist:{value:number}};
export const neonUniforms=():NeonU=>({uNeon:{value:1},uNeonDist:{value:1}});
/** mode 'body': edges+contours+features; 'lat': planet latitude lines; 'rim': outline only (works with replaced project_vertex). */
export function neonPatch(m:any,U:NeonU,{mode='body',freq=9,amt=1}:{mode?:'body'|'lat'|'rim';freq?:number;amt?:number}={}){
  if(!m||m.__neon)return;m.__neon=mode;const prev=m.onBeforeCompile;const prevKey=m.customProgramCacheKey?.bind(m);
  m.onBeforeCompile=(sh:any,r:any)=>{prev?.call(m,sh,r);sh.uniforms.uNeon=U.uNeon;sh.uniforms.uNeonDist=U.uNeonDist;
   const pos=mode!=='rim'&&sh.vertexShader.includes('#include <project_vertex>');
   if(pos)sh.vertexShader='varying vec3 vNW;\n'+sh.vertexShader.replace('#include <project_vertex>','vNW=transformed;\n#include <project_vertex>');
   const C=`vec3(${NEON.color.join(',')})`;
   sh.fragmentShader=(pos?'varying vec3 vNW;\n':'')+'uniform float uNeon,uNeonDist;\n'+sh.fragmentShader.replace('#include <dithering_fragment>',`#include <dithering_fragment>
    {vec3 nN=normalize(normal);vec3 vV=normalize(vViewPosition);float fr=1.-abs(dot(nN,vV));
     float edge=smoothstep(.72,.97,fr);float lines=0.,feat=0.;
     ${pos?(mode==='lat'?`float la=asin(clamp(normalize(vNW).y,-1.,1.))*${freq.toFixed(1)}/1.5708;float ga=abs(fract(la)-.5)/max(fwidth(la),1e-4);lines=1.-clamp(ga-.5,0.,1.);`
     :`feat=clamp(length(fwidth(nN))*6.,0.,1.);float F=${freq.toFixed(1)}*(1.+feat*1.5);
      float y=vNW.y*F;float gy=abs(fract(y)-.5)/max(fwidth(y),1e-4);float a=atan(vNW.x,vNW.z)*F*.5;float ga2=abs(fract(a)-.5)/max(fwidth(a),1e-4);
      lines=max(1.-clamp(gy-.5,0.,1.),(1.-clamp(ga2-.5,0.,1.))*.6);`):''}
     vec3 nc=mix(${C},vec3(1.),feat*.6+edge*.3);
     gl_FragColor.rgb+=nc*(edge*.55+lines*(.28+feat*.5))*${amt.toFixed(2)}*uNeon*uNeonDist;}`);};
  m.customProgramCacheKey=()=>(prevKey?prevKey():'')+':neon-'+mode;m.needsUpdate=true;
}
/** Jellyfish filaments: a few light strands trailing a moving anchor (verlet-lagged history). */
export function makeFilaments(THREE:T,parent:import('three').Object3D,{count=3,len=14,color=0x9ff4ff}:{count?:number;len?:number;color?:number}={}){
  const strands=[...Array(count)].map((_,k)=>{const g=new THREE.BufferGeometry();const a=new Float32Array(len*3);g.setAttribute('position',new THREE.BufferAttribute(a,3));
   const ln=new THREE.Line(g,new THREE.LineBasicMaterial({color,transparent:true,opacity:.55,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));ln.frustumCulled=false;parent.add(ln);
   return {ln,a,pts:[...Array(len)].map(()=>new THREE.Vector3()),k,init:false};});
  return {strands,
   step(anchor:import('three').Vector3,t:number,air:number,on:boolean,dt:number){for(const s of strands){s.ln.visible=on;if(!on)continue;
    if(!s.init){s.pts.forEach(p=>p.copy(anchor));s.init=true;}
    s.pts[0].copy(anchor);const follow=Math.min(1,dt*(9-air*5));
    for(let i=1;i<s.pts.length;i++){const p=s.pts[i],q=s.pts[i-1];const w=Math.sin(t*2.2+i*.55+s.k*2.1)*.035*(1+air*1.5);
     p.x+=(q.x-p.x)*follow+w;p.y+=(q.y-.045*(1-air)-p.y)*follow;p.z+=(q.z-p.z)*follow+Math.cos(t*1.7+i*.5+s.k)*.03*(1+air);
     s.a[i*3]=p.x;s.a[i*3+1]=p.y;s.a[i*3+2]=p.z;}s.a[0]=anchor.x;s.a[1]=anchor.y;s.a[2]=anchor.z;
    (s.ln.geometry.attributes.position as any).needsUpdate=true;(s.ln.material as any).opacity=.35+.35*air;}}};
}
