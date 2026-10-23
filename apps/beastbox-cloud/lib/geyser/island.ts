// Geyser Jelly island (three side, PR 1/4): volcanic island terrain, columnar basalt cliffs, sea stacks,
// a translucent jelly sea block that tips and springs back, and a shallow-water sim with caustics + foam.
import {GJ,STACKS,islandHeight,springStep,waterStep,waterDrop,rng} from './geyser-math.mjs';
type T=typeof import('three');
export function buildIsland(THREE:T,scene:import('three').Scene,{low,open=false}:{low:boolean;open?:boolean}){
  const root=new THREE.Group();root.name='geyser-jelly';root.position.set(GJ.cx,0,GJ.cz);scene.add(root);
  const U={uT:{value:0},uSea:{value:GJ.sea}};const r=rng('geyser-jelly');const S=GJ.half*2;
  // ---- island terrain (vertex colours: black sand, moss, scoria, basalt) + caustics on the seabed
  const seg=low?72:128;const g=new THREE.PlaneGeometry(S,S,seg,seg);g.rotateX(-Math.PI/2);const P=g.attributes.position as any;const col=new Float32Array(P.count*3);
  const sand=new THREE.Color(0x1a1820),moss=new THREE.Color(0x2c4630),scoria=new THREE.Color(0x4a2219),rock=new THREE.Color(0x2a2a33),bed=new THREE.Color(0x2b4a5a),c=new THREE.Color();
  for(let i=0;i<P.count;i++){const x=P.getX(i),z=P.getZ(i),h=islandHeight(x,z);P.setY(i,h);const dv=Math.hypot(x-GJ.volcano.x,z-GJ.volcano.z);
    if(h<.02)c.copy(bed).lerp(sand,Math.max(0,Math.min(1,(h-GJ.bed)/(.02-GJ.bed))));else if(dv<GJ.volcano.r)c.copy(moss).lerp(scoria,Math.min(1,(1-dv/GJ.volcano.r)*1.6));else if(h<.36)c.copy(sand).lerp(moss,Math.min(1,(h-.02)/.3));else c.copy(moss).lerp(rock,Math.min(1,(h-.5)*1.2));
    col.set([c.r,c.g,c.b],i*3);}
  g.setAttribute('color',new THREE.BufferAttribute(col,3));g.computeVertexNormals();
  const landM=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.92,flatShading:true});
  landM.onBeforeCompile=(sh:any)=>{sh.uniforms.uT=U.uT;sh.uniforms.uSea=U.uSea;sh.vertexShader='varying vec3 vGJ;\n'+sh.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nvGJ=(modelMatrix*vec4(transformed,1.)).xyz;');
    sh.fragmentShader='varying vec3 vGJ;uniform float uT,uSea;\nfloat gjC(vec2 p){p*=2.3;float t=uT*.6;vec2 q=p+vec2(sin(p.y*1.7+t),cos(p.x*1.3-t*.8));return pow(abs(sin(q.x*3.1)*sin(q.y*2.7)+sin((q.x+q.y)*2.2+t)*.5),3.);}\n'+sh.fragmentShader.replace('#include <dithering_fragment>','#include <dithering_fragment>\nif(vGJ.y<uSea){float dep=clamp((uSea-vGJ.y)/.7,0.,1.);gl_FragColor.rgb=mix(gl_FragColor.rgb,vec3(.1,.45,.55),.35*dep)+vec3(.55,.9,1.)*gjC(vGJ.xz)*(1.-dep*.6)*.35;}');};
  landM.customProgramCacheKey=()=>'gj-land';
  const land=new THREE.Mesh(g,landM);land.name='gj-land';root.add(land);
  // neon wireframe light layer over the island
  const wireG=new THREE.WireframeGeometry(new THREE.PlaneGeometry(S,S,low?20:36,low?20:36).rotateX(-Math.PI/2).applyMatrix4(new THREE.Matrix4()));
  {const wp=wireG.attributes.position as any;for(let i=0;i<wp.count;i++)wp.setY(i,islandHeight(wp.getX(i),wp.getZ(i))+.03);}
  const wire=new THREE.LineSegments(wireG,new THREE.LineBasicMaterial({color:0x7af0ff,transparent:true,opacity:.11,blending:THREE.AdditiveBlending,depthWrite:false}));root.add(wire);
  // ---- columnar basalt cliffs (instanced hex prisms) along the NW shore + sea stacks
  const colG=new THREE.CylinderGeometry(.075,.075,1,6);colG.translate(0,.5,0);const basalt=new THREE.MeshStandardMaterial({color:0x26262e,roughness:.85,flatShading:true,emissive:0x0a0a14});
  const nC=low?90:220;const cols=new THREE.InstancedMesh(colG,basalt,nC+STACKS.length*(low?6:12));const m4=new THREE.Matrix4(),q=new THREE.Quaternion(),v=new THREE.Vector3(),s=new THREE.Vector3();let k=0;
  for(let i=0;i<nC;i++){const a=1.3+r()*2.6;const shore=GJ.R*(1+.12*Math.sin(a*3+.7)+.07*Math.sin(a*7-1.1));const rr=shore-.05-r()*.35;const x=Math.cos(a)*rr,z=Math.sin(a)*rr;const base=Math.min(islandHeight(x,z),.1);
    const top=Math.max(islandHeight(x,z),.3)+r()*.25;m4.compose(v.set(x,base-.3,z),q.identity(),s.set(1,top-base+.3,1));cols.setMatrixAt(k++,m4);}
  for(const st of STACKS)for(let i=0;i<(low?6:12);i++){const a=i/(low?6:12)*6.283,rr=st.r*(.3+.7*((i*7)%3)/2);m4.compose(v.set(st.x+Math.cos(a)*rr,GJ.bed,st.z+Math.sin(a)*rr),q.identity(),s.set(1.4,st.h*(.75+.25*Math.cos(i*1.7))-GJ.bed,1.4));cols.setMatrixAt(k++,m4);}
  cols.count=k;cols.instanceMatrix.needsUpdate=true;cols.computeBoundingSphere();root.add(cols);
  // ---- jelly sea block + shallow-water surface (tips and springs back; land stays put so creatures stay grounded)
  const jelly=new THREE.Group();jelly.name='gj-jelly';root.add(jelly);
  const top=.95,bot=GJ.bed-.08,H=top-bot;
  const blockM=new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,uniforms:{uT:U.uT,uW:{value:0}},
    vertexShader:'uniform float uT,uW;varying vec3 vN;varying vec3 vV;void main(){vec3 p=position;p.xz*=1.+uW*.04*sin(p.y*3.+uT*9.);vN=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(p,1.);vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}',
    fragmentShader:'varying vec3 vN;varying vec3 vV;void main(){float f=pow(1.-abs(dot(vN,vV)),2.2);gl_FragColor=vec4(mix(vec3(.25,.85,.8),vec3(.75,1.,.95),f),.06+.42*f);}'});
  const block=new THREE.Mesh(new THREE.BoxGeometry(S,H,S),blockM);block.position.y=bot+H/2;block.renderOrder=3;jelly.add(block);
  const edges=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(S,H,S)),new THREE.LineBasicMaterial({color:0x9ff4ff,transparent:true,opacity:.45,blending:THREE.AdditiveBlending,depthWrite:false}));edges.position.copy(block.position);jelly.add(edges);
  // open sea (Cory, Oct 22): no floating glass tile; the island rises out of a real ocean with a shelf, shoreline foam and deep water
  if(open){block.visible=false;edges.visible=false;
   const oc=new THREE.Mesh(new THREE.RingGeometry(GJ.R*.9,GJ.half*1.6,low?96:192,low?8:16),new THREE.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{uT:U.uT,uR:{value:GJ.R},uH:{value:GJ.half}},
    vertexShader:'varying vec2 vP;void main(){vP=position.xy;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:'uniform float uT,uR,uH;varying vec2 vP;void main(){float a=atan(vP.y,vP.x);float shore=uR*(1.+.12*sin(-a*3.+.7)+.07*sin(-a*7.-1.1));float r=length(vP);float d=r-shore;if(d<.15)discard;'+
     'float shelf=smoothstep(.15,2.2,d),deep=smoothstep(2.,uH*.9,d);vec3 c=mix(vec3(.18,.62,.66),vec3(.05,.2,.38),shelf);c=mix(c,vec3(.02,.05,.16),deep);'+
     'float sw=sin(vP.x*1.7+uT*.6)*sin(vP.y*1.3-uT*.45)+.5*sin((vP.x+vP.y)*3.1+uT);c+=vec3(.25,.45,.55)*max(0.,sw)*.06*(1.-deep*.6);'+
     'float foam=smoothstep(.9,.15,d)*(.55+.45*sin(r*14.-uT*1.8));c=mix(c,vec3(.92,.98,1.),clamp(foam,0.,1.)*.7);'+
     'float fade=1.-smoothstep(uH*1.25,uH*1.6,r);gl_FragColor=vec4(c,(.82+.15*shelf)*fade);}'}));
   oc.rotation.x=-Math.PI/2;oc.position.y=GJ.sea-.012;oc.renderOrder=1;oc.name='gj-ocean';root.add(oc);
   // seabed skirt: the land plane's square edge slopes down into the deep instead of ending in the air
   const sk=new THREE.Mesh(new THREE.RingGeometry(GJ.half*.98,GJ.half*1.6,low?48:96,2),new THREE.MeshStandardMaterial({color:0x0a1626,roughness:1}));sk.rotation.x=-Math.PI/2;sk.position.y=GJ.bed-.05;root.add(sk);}
  const n=low?GJ.simLow:GJ.simHigh;const h=new Float32Array(n*n),pv=new Float32Array(n*n),mask=new Uint8Array(n*n),dep=new Float32Array(n*n);
  const wg=new THREE.PlaneGeometry(S,S,n-1,n-1);wg.rotateX(-Math.PI/2);const WP=wg.attributes.position as any;
  for(let j=0;j<n;j++)for(let i=0;i<n;i++){const q2=j*n+i;const x=WP.getX(q2),z=WP.getZ(q2);const d=GJ.sea-islandHeight(x,z);dep[q2]=d;mask[q2]=d>.01&&i>0&&j>0&&i<n-1&&j<n-1?1:0;}
  wg.setAttribute('aDep',new THREE.BufferAttribute(dep,1));
  const waterM=new THREE.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{uT:U.uT},
    vertexShader:'attribute float aDep;uniform float uT;varying float vD;varying vec3 vN;varying vec3 vV;varying vec3 vW;void main(){vD=aDep;vN=normalize(normalMatrix*normal);vec4 w=modelMatrix*vec4(position,1.);vW=w.xyz;vec4 mv=viewMatrix*w;vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}',
    fragmentShader:'uniform float uT;varying float vD;varying vec3 vN;varying vec3 vV;varying vec3 vW;void main(){if(vD<.0)discard;float f=pow(1.-max(0.,dot(vN,vV)),3.);vec3 sh=vec3(.35,.95,.9),dp=vec3(.03,.2,.38);float d=clamp(vD/.7,0.,1.);vec3 c=mix(sh,dp,d);\n'+
     '// refraction-style shimmer: normal-driven offset of a moving ripple pattern\nvec2 o=vN.xz*.6;float rip=sin((vW.x+o.x)*9.+uT*1.7)*sin((vW.z+o.y)*8.-uT*1.3);c+=vec3(.4,.7,.8)*max(0.,rip)*.08*(1.-d);\n'+
     'float foam=smoothstep(.12,.0,vD)+smoothstep(.35,.9,length(vN.xz)*6.);foam*=.6+.4*sin(vW.x*23.+uT*2.)*sin(vW.z*19.-uT*1.6);c=mix(c,vec3(.95,1.,1.),clamp(foam,0.,1.)*.8);c+=vec3(.8,.95,1.)*f*.35;gl_FragColor=vec4(c,.55+.3*d+.1*f);}'});
  const water=new THREE.Mesh(wg,waterM);water.name='gj-water';water.position.y=GJ.sea;water.renderOrder=2;jelly.add(water);
  let wob={a:0,v:0},wob2={a:0,v:0};let acc=0;
  function tip(amp=.6,dir=r()*6.283){wob.v+=amp*6*Math.cos(dir);wob2.v+=amp*6*Math.sin(dir);}
  function splash(lx:number,lz:number,amp=.25){waterDrop(h,n,(lx+GJ.half)/S,(lz+GJ.half)/S,amp,low?1:2);}
  return {root,U,tip,splash,land,water,jelly,
    update(dt:number,t:number){const d=Math.min(.05,Math.max(0,dt||0));U.uT.value=t;
      wob=springStep(wob,d);wob2=springStep(wob2,d);jelly.rotation.x=wob.a*.07;jelly.rotation.z=wob2.a*.07;(blockM.uniforms.uW as any).value=Math.min(1,Math.abs(wob.v)+Math.abs(wob2.v))*.5;
      // ambient swell + a gentle push from the tilt (water sloshes against the walls)
      if(r()<d*1.2)splash((r()-.5)*S*.9,(r()-.5)*S*.9,.05+r()*.06);
      acc+=d;const step=1/30;let guard=0;while(acc>=step&&guard++<3){waterStep(h,pv,mask,n,step);acc-=step;}if(acc>step)acc=0;
      const tiltX=wob2.a*.35,tiltZ=wob.a*.35;
      for(let j=0;j<n;j++)for(let i=0;i<n;i++){const q2=j*n+i;const hv=mask[q2]?h[q2]*.12+(i/(n-1)-.5)*tiltX*.2-(j/(n-1)-.5)*tiltZ*.2:-.002;WP.setY(q2,Number.isFinite(hv)?hv:0);}
      WP.needsUpdate=true;wg.computeVertexNormals();},
    dispose(){scene.remove(root);root.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});}};
}
