// "The user's heaven": warm divine light inside the cage pocket, endless depth, serene flow (Cory, Oct 18).
// Additive only: the cage geometry, palette and fog stay; this layers warmth and depth on top.
type T=typeof import('three');
export const HEAVEN=Object.freeze({flow:.62,orbit:.6,exposure:1.4,sun:0xffe0b0,halo:0xffd7a0});
export function addHeaven(THREE:T,scene:import('three').Scene,{low}:{low:boolean}){
  const root=new THREE.Group();root.name='heaven';scene.add(root);
  // 1) warm divine light from above (gold-white key + soft warm fill)
  const sun=new THREE.DirectionalLight(HEAVEN.sun,1.7);sun.position.set(1.5,12,2);root.add(sun);root.add(sun.target);
  const fill=new THREE.HemisphereLight(0xffe6c4,0x2a1a30,.7);root.add(fill);
  const radial=(inner:string,outer:string)=>{const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d')!;const g=x.createRadialGradient(64,64,0,64,64,64);g.addColorStop(0,inner);g.addColorStop(.35,outer);g.addColorStop(1,'rgba(0,0,0,0)');x.fillStyle=g;x.fillRect(0,0,128,128);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;};
  const halo=new THREE.Sprite(new THREE.SpriteMaterial({map:radial('rgba(255,245,225,1)','rgba(255,205,150,.35)'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,opacity:.85}));halo.scale.set(7,7,1);halo.position.set(0,5.2,-1.5);// in view at the default camera (theta .7, phi 1.28, zoom 10.6)
  const core=new THREE.Sprite(new THREE.SpriteMaterial({map:radial('rgba(255,252,240,1)','rgba(255,230,190,.5)'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,opacity:.9}));core.scale.set(2.2,2.2,1);core.position.copy(halo.position);root.add(core);root.add(halo);
  // soft light shaft from the halo down onto the pocket (very faint additive cone, fades at the floor)
  const shaftG=new THREE.CylinderGeometry(.5,4.6,5.4,low?16:32,1,true);shaftG.translate(0,2.7,0);
  const shaft=new THREE.Mesh(shaftG,new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,fog:false,uniforms:{uT:{value:0}},
   vertexShader:'varying vec2 vU;void main(){vU=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
   fragmentShader:'varying vec2 vU;uniform float uT;void main(){float a=smoothstep(0.,.35,vU.y)*(1.-smoothstep(.8,1.,vU.y));float r=.6+.4*sin(vU.x*37.+uT*.25)*sin(vU.x*13.-uT*.17);gl_FragColor=vec4(vec3(1.,.86,.62)*a*r*.17,1.);}'}));
  shaft.position.set(0,-.1,-1.5);root.add(shaft);
  // 2) endless depth: slow warm motes drifting upward through the light, layered far behind the cage
  const N=low?260:700,P=new Float32Array(N*3),S=new Float32Array(N);for(let i=0;i<N;i++){const a=Math.random()*6.283,r=Math.pow(Math.random(),.6)*(i%3===0?60:14);P.set([Math.cos(a)*r,Math.random()*16,Math.sin(a)*r],i*3);S[i]=Math.random();}
  const mg=new THREE.BufferGeometry();mg.setAttribute('position',new THREE.BufferAttribute(P,3));mg.setAttribute('aS',new THREE.BufferAttribute(S,1));
  const motes=new THREE.Points(mg,new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,uniforms:{uT:{value:0}},
   vertexShader:'attribute float aS;uniform float uT;varying float vA;void main(){vec3 p=position;p.y=mod(p.y+uT*(.08+.12*aS),16.)-.2;p.x+=sin(uT*.1+aS*20.)*.4;vec4 mv=modelViewMatrix*vec4(p,1.);vA=smoothstep(0.,2.,p.y)*(1.-smoothstep(12.,16.,p.y))*(.4+.6*aS);gl_PointSize=min(40.,(3.+5.*aS)*30./-mv.z)*smoothstep(.35,1.1,-mv.z);gl_Position=projectionMatrix*mv;}',
   fragmentShader:'varying float vA;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;gl_FragColor=vec4(vec3(1.,.88,.66)*smoothstep(.5,0.,d)*vA*1.35,1.);}'}));motes.frustumCulled=false;root.add(motes);
  return {root,
    update(t:number){(shaft.material as any).uniforms.uT.value=t;(motes.material as any).uniforms.uT.value=t;const b=.85+.1*Math.sin(t*.21);(halo.material as any).opacity=b;(core.material as any).opacity=.8+.15*Math.sin(t*.21+.6);sun.intensity=1.6+.15*Math.sin(t*.13);},
    dispose(){scene.remove(root);root.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.map?.dispose?.();o.material?.dispose?.();});}};
}
