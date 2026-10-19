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
  const halo=new THREE.Sprite(new THREE.SpriteMaterial({map:radial('rgba(255,245,225,1)','rgba(255,205,150,.35)'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,opacity:.85}));halo.scale.set(5,5,1);halo.position.set(0,3.4,0);// v3: low over the pocket centre, in frame at the default camera from any orbit angle
  const core=new THREE.Sprite(new THREE.SpriteMaterial({map:radial('rgba(255,252,240,1)','rgba(255,230,190,.5)'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,opacity:.9}));core.scale.set(1.5,1.5,1);core.position.copy(halo.position);root.add(core);root.add(halo);
  // v3 sun orb: a distinct, very bright disc (not tone-mapped) + star rays + wide bloom
  const orb=new THREE.Mesh(new THREE.SphereGeometry(.32,24,16),new THREE.MeshBasicMaterial({color:0xfff6e0,toneMapped:false,fog:false}));orb.position.copy(halo.position);orb.name='heaven-sun';root.add(orb);
  const rays=(()=>{const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d')!;x.translate(128,128);for(let i=0;i<12;i++){x.rotate(Math.PI/6);const g=x.createLinearGradient(0,0,0,128);g.addColorStop(0,'rgba(255,240,210,.9)');g.addColorStop(1,'rgba(255,200,140,0)');x.fillStyle=g;x.beginPath();x.moveTo(-(i%2?3:6),0);x.lineTo(i%2?3:6,0);x.lineTo(0,i%2?90:128);x.fill();}const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;})();
  const star=new THREE.Sprite(new THREE.SpriteMaterial({map:rays,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,opacity:.75}));star.scale.set(3.4,3.4,1);star.position.copy(halo.position);root.add(star);
  const bloom=new THREE.Sprite(new THREE.SpriteMaterial({map:radial('rgba(255,215,160,.55)','rgba(255,180,120,.12)'),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,opacity:.7}));bloom.scale.set(11,11,1);bloom.position.copy(halo.position);root.add(bloom);
  // soft light shaft from the halo down onto the pocket (very faint additive cone, fades at the floor)
  const shaftG=new THREE.CylinderGeometry(.3,2.8,3.5,low?16:32,1,true);shaftG.translate(0,1.75,0);
  const shaft=new THREE.Mesh(shaftG,new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,fog:false,uniforms:{uT:{value:0}},
   vertexShader:'varying vec2 vU;void main(){vU=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
   fragmentShader:'varying vec2 vU;uniform float uT;void main(){float a=smoothstep(0.,.25,vU.y)*(1.-smoothstep(.92,1.,vU.y))*(.55+.45*vU.y);float r=.6+.4*sin(vU.x*37.+uT*.25)*sin(vU.x*13.-uT*.17);gl_FragColor=vec4(vec3(1.,.86,.62)*a*r*.42,1.);}'}));
  shaft.position.set(0,-.1,0);root.add(shaft);
  // 2) endless depth: slow warm motes drifting upward through the light, layered far behind the cage
  const N=low?260:700,P=new Float32Array(N*3),S=new Float32Array(N);for(let i=0;i<N;i++){const a=Math.random()*6.283,r=Math.pow(Math.random(),.6)*(i%3===0?60:14);P.set([Math.cos(a)*r,Math.random()*16,Math.sin(a)*r],i*3);S[i]=Math.random();}
  const mg=new THREE.BufferGeometry();mg.setAttribute('position',new THREE.BufferAttribute(P,3));mg.setAttribute('aS',new THREE.BufferAttribute(S,1));
  const motes=new THREE.Points(mg,new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,uniforms:{uT:{value:0}},
   vertexShader:'attribute float aS;uniform float uT;varying float vA;void main(){vec3 p=position;p.y=mod(p.y+uT*(.08+.12*aS),16.)-.2;p.x+=sin(uT*.1+aS*20.)*.4;vec4 mv=modelViewMatrix*vec4(p,1.);vA=smoothstep(0.,2.,p.y)*(1.-smoothstep(12.,16.,p.y))*(.4+.6*aS);gl_PointSize=min(40.,(3.+5.*aS)*30./-mv.z)*smoothstep(.35,1.1,-mv.z);gl_Position=projectionMatrix*mv;}',
   fragmentShader:'varying float vA;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;gl_FragColor=vec4(vec3(1.,.88,.66)*smoothstep(.5,0.,d)*vA*1.35,1.);}'}));motes.frustumCulled=false;root.add(motes);
  return {root,
    update(t:number){(shaft.material as any).uniforms.uT.value=t;(motes.material as any).uniforms.uT.value=t;const b=.85+.1*Math.sin(t*.21);(halo.material as any).opacity=b;star.material.rotation=t*.03;(star.material as any).opacity=.65+.15*Math.sin(t*.5);(core.material as any).opacity=.8+.15*Math.sin(t*.21+.6);sun.intensity=1.6+.15*Math.sin(t*.13);},
    dispose(){scene.remove(root);root.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.map?.dispose?.();o.material?.dispose?.();});}};
}
