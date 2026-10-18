// Sector-physics plasma planets (Cory's "quantum tunneling" reference): crackling plasma-web core with a
// soft bloom halo, a dark metallic ring band, instanced radiating emission lines (coloured one side, white
// the other) that flutter with the planet's frequency/audio and lean toward nearby creatures, elliptical
// orbit-node chains inside the ring, and a tunneling event (flash + inversion, gravitational-lens stretch,
// lens ring warp, nebula swirl) with a tiny sector label.
type T=typeof import('three');type V3={x:number;y:number;z:number};
export const PLASMA_LIMITS=Object.freeze({linesLow:48,linesHigh:96,chainNodesLow:6,chainNodesHigh:10,chains:3});
/** Gravitational-lens stretch envelope: (sx, sy) from 1.5×0.8 easing back to 1×1 over `dur` seconds. */
export function lensStretch(t:number,dur=1.4){if(t<0||t>=dur)return [1,1];const k=1-t/dur,e=k*k*(3-2*k);return [1+.5*e,1-.2*e];}
/** Flash/inversion envelope: 1 at the event, gone after ~0.25 s. */
export const flashEnv=(t:number)=>t<0?0:Math.max(0,1-t/.25);
/** Sector label for a world (stable). */
export const sectorLabel=(i:number,id:string)=>`sector ${11+i*3+(id.length%3)} · one path, one order`;
const CORE_FS=`varying vec3 vP;varying vec3 vN;varying vec3 vV;uniform float uTime,uPulse;uniform vec3 uCol;
 float h(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
 float n3(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(mix(h(i),h(i+vec3(1,0,0)),f.x),mix(h(i+vec3(0,1,0)),h(i+vec3(1,1,0)),f.x),f.y),mix(mix(h(i+vec3(0,0,1)),h(i+vec3(1,0,1)),f.x),mix(h(i+vec3(0,1,1)),h(i+vec3(1,1,1)),f.x),f.y),f.z);}
 void main(){vec3 p=vP*2.2;float w=0.,a=.55;for(int i=0;i<OCT;i++){float r=1.-abs(n3(p+uTime*.35)*2.-1.);w+=pow(r,6.)*a;p=p*2.03+vec3(1.7,9.2,3.1);a*=.55;}
  float fr=pow(1.-abs(dot(normalize(vN),normalize(vV))),2.);vec3 c=mix(uCol*.25,uCol,w)+vec3(1.)*pow(w,3.)*1.6+uCol*fr*.8;c*=1.+uPulse*1.2;
  gl_FragColor=vec4(c,1.);}`;
const CORE_VS=`varying vec3 vP;varying vec3 vN;varying vec3 vV;void main(){vP=position;vN=normalMatrix*normal;vec4 mv=modelViewMatrix*vec4(position,1.);vV=-mv.xyz;gl_Position=projectionMatrix*mv;}`;
export function buildPlasmaPlanet(THREE:T,parent:import('three').Object3D,{radius,color,atmo,low,seed=1}:{radius:number;color:number;atmo:number;low:boolean;seed?:number}){
  const g=new THREE.Group();g.name='plasma-planet';parent.add(g);
  const U={uTime:{value:0},uPulse:{value:0},uCol:{value:new THREE.Color(atmo)}};
  const core=new THREE.Mesh(new THREE.IcosahedronGeometry(radius*.62,low?3:4),new THREE.ShaderMaterial({uniforms:U,vertexShader:CORE_VS,fragmentShader:'#define OCT '+(low?2:4)+'\n'+CORE_FS,fog:false}));g.add(core);
  // bloom halo (billboard, additive)
  const halo=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,uniforms:{uCol:U.uCol,uPulse:U.uPulse},
   vertexShader:'varying vec2 vU;void main(){vU=uv-.5;vec4 mv=modelViewMatrix*vec4(0.,0.,0.,1.);mv.xy+=position.xy*'+(radius*3.2).toFixed(2)+';gl_Position=projectionMatrix*mv;}',
   fragmentShader:'varying vec2 vU;uniform vec3 uCol;uniform float uPulse;void main(){float r=length(vU)*2.;float a=exp(-r*r*5.)*(.55+uPulse*.6);gl_FragColor=vec4(mix(uCol,vec3(1.),.35)*a,a);}'}));
  halo.frustumCulled=false;halo.renderOrder=3;g.add(halo);
  // dark metallic ring band
  const tilt=new THREE.Group();tilt.rotation.set(.35+seed*.07,0,.2-seed*.05);g.add(tilt);
  const ring=new THREE.Mesh(new THREE.TorusGeometry(radius*1.05,radius*.09,low?6:10,low?48:96),new THREE.MeshStandardMaterial({color:0x14101e,metalness:.9,roughness:.35,emissive:color,emissiveIntensity:.08,fog:false}));
  ring.rotation.x=Math.PI/2;tilt.add(ring);
  // radiating emission lines (instanced thin quads; radial flutter + lean in the vertex shader)
  const NL=low?PLASMA_LIMITS.linesLow:PLASMA_LIMITS.linesHigh;
  const lg=new THREE.InstancedBufferGeometry();const base=new THREE.PlaneGeometry(1,1);base.translate(0,.5,0);lg.index=base.index;lg.attributes.position=base.attributes.position;lg.attributes.uv=base.attributes.uv;
  const aDir=new Float32Array(NL*3),aSeed=new Float32Array(NL);for(let i=0;i<NL;i++){const a=i/NL*Math.PI*2;aDir[i*3]=Math.cos(a);aDir[i*3+1]=(Math.sin(i*2.39)*.12);aDir[i*3+2]=Math.sin(a);aSeed[i]=Math.sin(i*12.9898)*.5+.5;}
  lg.setAttribute('aDir',new THREE.InstancedBufferAttribute(aDir,3));lg.setAttribute('aSeed',new THREE.InstancedBufferAttribute(aSeed,1));lg.instanceCount=NL;
  const LU={uTime:U.uTime,uLevel:{value:.3},uFreq:{value:1.3+seed*.4},uLean:{value:new THREE.Vector3()},uLeanAmt:{value:0},uCol:U.uCol,uR:{value:radius},uPulse:U.uPulse};
  const lines=new THREE.Mesh(lg,new THREE.ShaderMaterial({uniforms:LU,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,fog:false,
   vertexShader:`attribute vec3 aDir;attribute float aSeed;uniform float uTime,uLevel,uFreq,uLeanAmt,uR,uPulse;uniform vec3 uLean;varying float vS;varying float vA;
    void main(){vec3 d=normalize(aDir);float fl=.55+.45*sin(uTime*uFreq*6.283*.5+aSeed*31.)*(.4+uLevel)+uPulse*.6;float len=uR*(.5+aSeed*.9)*fl;
     vec3 dir=normalize(d+uLean*uLeanAmt*max(0.,dot(d,uLean)+.3));vec3 start=d*uR*1.18;vec3 side=normalize(cross(dir,vec3(0.,1.,0.))+1e-4);
     vec3 p=start+dir*position.y*len+side*position.x*uR*.012;vS=d.x;vA=1.-position.y;gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);}`,
   fragmentShader:`uniform vec3 uCol;varying float vS;varying float vA;void main(){vec3 c=vS>0.?uCol*1.4:vec3(1.);gl_FragColor=vec4(c*vA,vA*.8);}`}));
  lines.frustumCulled=false;tilt.add(lines);
  // orbit-node chains on ellipses inside the ring
  const NN=low?PLASMA_LIMITS.chainNodesLow:PLASMA_LIMITS.chainNodesHigh,NC=PLASMA_LIMITS.chains;
  const nodes=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(radius*.05,0),new THREE.MeshBasicMaterial({color:0xffffff,fog:false}),NN*NC);tilt.add(nodes);
  const chainGeo=new THREE.BufferGeometry();chainGeo.setAttribute('position',new THREE.BufferAttribute(new Float32Array(NN*NC*2*3),3));
  const chainLines=new THREE.LineSegments(chainGeo,new THREE.LineBasicMaterial({color:atmo,transparent:true,opacity:.6,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));chainLines.frustumCulled=false;tilt.add(chainLines);
  const m4=new THREE.Matrix4(),pv=new THREE.Vector3();
  // tunneling event
  const lensRing=new THREE.Mesh(new THREE.RingGeometry(radius*1.6,radius*2.4,low?32:64),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,side:THREE.DoubleSide,uniforms:{uK:{value:0},uCol:U.uCol},
   vertexShader:'varying vec2 vU;void main(){vU=uv;vec4 mv=modelViewMatrix*vec4(0.,0.,0.,1.);mv.xy+=position.xy;gl_Position=projectionMatrix*mv;}',
   fragmentShader:'varying vec2 vU;uniform float uK;uniform vec3 uCol;void main(){float r=length(vU-.5)*2.;float band=sin(r*40.-uK*20.)*.5+.5;float a=uK*band*smoothstep(1.,.6,r)*smoothstep(.2,.5,r);gl_FragColor=vec4(mix(vec3(1.),uCol,r)*a,a);}'}));
  lensRing.frustumCulled=false;lensRing.renderOrder=4;g.add(lensRing);
  let ev=-99,pulse=0;
  return {group:g,U,
   tunnel(t:number){ev=t;},pulse(a=1){pulse=Math.min(1.5,pulse+a);},
   flash(t:number){return flashEnv(t-ev);},
   update(t:number,dt:number,{level=.3,near=null}:{level?:number;near?:V3|null}={}){
    U.uTime.value=t;pulse=Math.max(0,pulse-dt*1.5);U.uPulse.value=pulse;LU.uLevel.value=level;
    if(near){g.updateMatrixWorld();pv.set(near.x,near.y,near.z);tilt.worldToLocal(pv);const d=pv.length();pv.normalize();LU.uLean.value.copy(pv);LU.uLeanAmt.value=Math.max(0,1-d/(radius*8))*.8;}else LU.uLeanAmt.value*=.95;
    const P=chainGeo.attributes.position as any;let k=0;
    for(let c=0;c<NC;c++){const a=radius*(.78+c*.08),b=a*(.55+c*.12),sp=.25+c*.11;for(let i=0;i<NN;i++){const th=t*sp*(c%2?-1:1)+i/NN*Math.PI*2;const x=Math.cos(th)*a,z=Math.sin(th)*b,y=Math.sin(th*2+c)*radius*.04;
     m4.makeTranslation(x,y,z);nodes.setMatrixAt(c*NN+i,m4);const th2=th+Math.PI*2/NN;P.setXYZ(k++,x,y,z);P.setXYZ(k++,Math.cos(th2)*a,Math.sin(th2*2+c)*radius*.04,Math.sin(th2)*b);}}
    nodes.instanceMatrix.needsUpdate=true;P.needsUpdate=true;
    const st=t-ev;const [sx,sy]=lensStretch(st);g.scale.set(sx,sy,sx);(lensRing.material as any).uniforms.uK.value=Math.max(0,1-st/1.6)*(st>=0?1:0);}};
}
/** Small in-scene sector label sprite (fades in on arrival, never part of the DOM UI). */
export function sectorSprite(THREE:T,text:string){const c=document.createElement('canvas');c.width=512;c.height=64;const x=c.getContext('2d')!;x.font='28px ui-monospace,monospace';x.fillStyle='rgba(220,235,255,1)';x.textAlign='center';x.fillText(text,256,42);
  const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),transparent:true,opacity:0,depthWrite:false,fog:false}));s.scale.set(4,.5,1);return s;}
