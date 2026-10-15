/**
 * Pocket "god view": multi-scale cosmos around the habitat (creature close-up → habitat on a small
 * planet → planet orbiting its suns → star system → galaxy). Visual only.
 *
 * Shaders and system structure adapted from Cory's Genesis Engine ("The Definitive Core":
 * generateUniverse/createPlanet/createAtmosphere/createStarCorona/createNebula), recoloured to the
 * Beast Box palette. Everything is derived from the recorded seed; the only "quantum" input is the
 * Beast's own labelled simulator counts when a receipt exists (never invented, never hardware).
 */
type T=typeof import('three');
export const ZOOM_MIN=3.2,ZOOM_MAX=12000;
export const PLANET_R=14;
/** Smooth 0..1 ramp in log-zoom space. */
export function scaleMix(zoom:number,from:number,to:number){const t=(Math.log(zoom)-Math.log(from))/(Math.log(to)-Math.log(from));const c=Math.max(0,Math.min(1,t));return c*c*(3-2*c);}
/** Distribution weights from the labelled simulator counts (empty when there is no receipt). */
export function countWeights(counts:Record<string,number>|null|undefined){
 if(!counts)return [];const e=Object.entries(counts).filter(([,v])=>Number.isFinite(v)&&v>0).sort(([a],[b])=>a<b?-1:1);
 const tot=e.reduce((s,[,v])=>s+v,0);return tot>0?e.map(([k,v])=>({key:k,w:v/tot})):[];
}
const PAL=[0x8f5bff,0x5fd4ff,0xff7fd6,0x7ef0c8,0xffd27a];
export function addGodView(THREE:T,scene:import('three').Scene,o:{rand:()=>number;low:boolean;counts:Record<string,number>|null;stage:number}){
 const {rand,low}=o;const weights=countWeights(o.counts);
 // ---- Planet under the habitat (habitat sits on its north pole) ----
 const planetMat=new THREE.ShaderMaterial({uniforms:{time:{value:0},a:{value:new THREE.Color(0x3a2c6e)},b:{value:new THREE.Color(0x7b55c8)},c:{value:new THREE.Color(0x4fe0f0)},bloom:{value:0}},
  vertexShader:'varying vec3 vP;varying vec3 vN;void main(){vP=position;vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
  fragmentShader:'uniform float time;uniform vec3 a;uniform vec3 b;uniform vec3 c;uniform float bloom;varying vec3 vP;varying vec3 vN;'+
   'float h(vec3 p){p=fract(p*.3183099+.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}'+
   'float n(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);return mix(mix(mix(h(i),h(i+vec3(1,0,0)),f.x),mix(h(i+vec3(0,1,0)),h(i+vec3(1,1,0)),f.x),f.y),mix(mix(h(i+vec3(0,0,1)),h(i+vec3(1,0,1)),f.x),mix(h(i+vec3(0,1,1)),h(i+vec3(1,1,1)),f.x),f.y),f.z);}'+
   'float fbm(vec3 p){float v=0.0,s=.5;for(int i=0;i<5;i++){v+=s*n(p);p*=2.03;s*=.5;}return v;}'+
   'void main(){vec3 q=normalize(vP);float f=fbm(q*3.2);float g=fbm(q*9.0+f);vec3 col=mix(a,b,smoothstep(.35,.7,f));'+
   'float glowv=smoothstep(.62,.8,g)*(.25+bloom);col+=c*glowv;float l=max(dot(vN,normalize(vec3(.6,.7,.4))),0.0)*.75+.45;gl_FragColor=vec4(col*l,1.0);}'});
 const planet=new THREE.Mesh(new THREE.SphereGeometry(PLANET_R,low?32:72,low?20:48),planetMat);planet.position.set(0,-PLANET_R-.3,0);scene.add(planet);
 // Atmosphere (Genesis createAtmosphere: fresnel rim, additive, BackSide).
 const atm=new THREE.Mesh(new THREE.SphereGeometry(PLANET_R*1.08,48,32),new THREE.ShaderMaterial({transparent:true,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,
  uniforms:{color:{value:new THREE.Color(0x8f6bff)}},vertexShader:'varying vec3 vN;varying vec3 vV;void main(){vN=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(position,1.0);vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}',
  fragmentShader:'uniform vec3 color;varying vec3 vN;varying vec3 vV;void main(){float i=pow(.75-dot(vN,vV),3.0);gl_FragColor=vec4(color,1.0)*max(i,0.0)*1.6;}'}));
 atm.position.copy(planet.position);scene.add(atm);
 // Growth on the planet: crystal groves around the habitat, count from the native stage; each grove's
 // colour band comes from one labelled simulator outcome (weights only when a receipt exists).
 const groves=new THREE.Group();scene.add(groves);
 const grovesN=Math.min(low?40:90,12+Math.round((o.stage||1)*14));
 for(let i=0;i<grovesN;i++){const lat=.5+rand()*1.0,lon=rand()*Math.PI*2;const w=weights.length?weights[i%weights.length]:null;
  const col=new THREE.Color(PAL[w?Math.abs([...w.key].reduce((s,ch)=>s*31+ch.charCodeAt(0),7))%PAL.length:i%2]);
  const m=new THREE.Mesh(new THREE.OctahedronGeometry(.14+(w?w.w*.9:0.08)+rand()*.14,0),new THREE.MeshBasicMaterial({color:col,fog:false}));
  const dir=new THREE.Vector3(Math.sin(lat)*Math.cos(lon),Math.cos(lat),Math.sin(lat)*Math.sin(lon));
  m.position.copy(planet.position).addScaledVector(dir,PLANET_R+.2);m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),dir);m.scale.y=2.4;groves.add(m);}
 // ---- Star system: planet orbits 1–2 suns (binary from the seed) ----
 const sys=new THREE.Group();scene.add(sys);
 const orbitR=260+rand()*120,binary=rand()>.55,orbitSpeed=.012;
 const sunCols=[0xffc96b,0x9fd8ff,0xff8fd8];const suns:import('three').Mesh[]=[];
 const corona=(color:number,size:number)=>new THREE.Mesh(new THREE.SphereGeometry(size*1.9,32,24),new THREE.ShaderMaterial({transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,side:THREE.BackSide,
  uniforms:{c:{value:new THREE.Color(color)}},vertexShader:'varying vec3 vN;varying vec3 vV;void main(){vN=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(position,1.0);vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}',
  fragmentShader:'uniform vec3 c;varying vec3 vN;varying vec3 vV;void main(){float i=pow(max(0.0,-dot(vN,vV)),2.2);gl_FragColor=vec4(c*i*1.4,i);}'}));
 for(let s=0;s<(binary?2:1);s++){const size=18+rand()*14;const sun=new THREE.Mesh(new THREE.SphereGeometry(size,32,24),new THREE.MeshBasicMaterial({color:sunCols[s],fog:false}));sun.add(corona(sunCols[s],size));sun.userData.size=size;sys.add(sun);suns.push(sun);}
 const sunLight=new THREE.PointLight(0xffe0b0,0,0,0);sys.add(sunLight);
 // Sibling planets on their own orbits (Genesis createPlanet, simplified), with orbit rings.
 const others:{m:import('three').Mesh;r:number;sp:number;ph:number}[]=[];
 const ringMat=new THREE.LineBasicMaterial({color:0x6f5bd8,transparent:true,opacity:.35,fog:false});
 const ring=(r:number)=>{const pts:number[]=[];for(let i=0;i<=128;i++){const a=i/128*Math.PI*2;pts.push(Math.cos(a)*r,0,Math.sin(a)*r);}const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));return new THREE.Line(g,ringMat);};
 sys.add(ring(orbitR));
 const nOthers=3+Math.floor(rand()*(low?2:4));
 for(let i=0;i<nOthers;i++){const r=orbitR*(.45+i*.42+rand()*.15);if(Math.abs(r-orbitR)<40)continue;const size=4+rand()*12;
  const m=new THREE.Mesh(new THREE.SphereGeometry(size,24,16),new THREE.MeshStandardMaterial({color:PAL[i%PAL.length],roughness:.8,emissive:PAL[i%PAL.length],emissiveIntensity:.12,fog:false}));
  sys.add(m);sys.add(ring(r));others.push({m,r,sp:orbitSpeed*Math.pow(orbitR/r,1.5),ph:rand()*Math.PI*2});}
 // ---- Galaxy: capped spiral of stars far out, around the system ----
 const gN=low?900:2400,gp=new Float32Array(gN*3),gc=new Float32Array(gN*3);const arms=2+Math.floor(rand()*3);const tmp=new THREE.Color();
 for(let i=0;i<gN;i++){const r=Math.pow(rand(),.6)*9000+600;const arm=(i%arms)/arms*Math.PI*2;const a=arm+r*.00055+(rand()-.5)*.5;
  gp[i*3]=Math.cos(a)*r;gp[i*3+1]=(rand()-.5)*260*(1-r/9600);gp[i*3+2]=Math.sin(a)*r;tmp.setHex(PAL[i%PAL.length]).lerp(new THREE.Color(0xffffff),.5);gc[i*3]=tmp.r;gc[i*3+1]=tmp.g;gc[i*3+2]=tmp.b;}
 const gg=new THREE.BufferGeometry();gg.setAttribute('position',new THREE.BufferAttribute(gp,3));gg.setAttribute('color',new THREE.BufferAttribute(gc,3));
 const galaxyMat=new THREE.PointsMaterial({size:40,vertexColors:true,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false,fog:false,sizeAttenuation:true});
 const galaxy=new THREE.Points(gg,galaxyMat);sys.add(galaxy);
 const barycenter=new THREE.Vector3();
 return {
  planet,
  /** Per frame: orbit the planet (i.e. place the system around it), fade tiers by zoom. Returns camera focus. */
  update(elapsed:number,zoom:number,habitatFocus:import('three').Vector3,out:import('three').Vector3){
   planetMat.uniforms.time.value=elapsed;planetMat.uniforms.bloom.value=Math.min(.6,(o.stage||1)*.12);
   const a=elapsed*orbitSpeed+.9;
   // Planet sits at the scene origin; the system's barycentre is placed so the planet is on its orbit.
   barycenter.set(-Math.cos(a)*orbitR,-PLANET_R-.3,-Math.sin(a)*orbitR);sys.position.copy(barycenter);
   suns.forEach((s,i)=>{const b=binary?(i?1:-1)*(s.userData.size*1.6):0;s.position.set(Math.cos(elapsed*.05)*b,0,Math.sin(elapsed*.05)*b);});
   for(const p of others){const t=elapsed*p.sp+p.ph;p.m.position.set(Math.cos(t)*p.r,0,Math.sin(t)*p.r);}
   const sysMix=scaleMix(zoom,60,700),galMix=scaleMix(zoom,900,6000);
   galaxyMat.opacity=.85*galMix;galaxy.visible=galMix>0.01;
   // LOD: the star system only exists for the GPU once you zoom out past the planet.
   sys.visible=zoom>34;atm.visible=zoom>8;
   ringMat.opacity=.4*scaleMix(zoom,40,260);
   const lod=zoom>120;groves.visible=zoom<900;
   void lod;
   out.copy(habitatFocus).lerp(barycenter,sysMix*.92);return out;
  },
 };
}
