import * as THREE from 'three';
import {PALETTE,PALETTE_OKLAB,L_WEIGHT} from './palette.js';
import {SEEDS,loadSeed} from './seed.js';
const $=id=>document.getElementById(id);
const LABEL='Seeded from recorded IBM Quantum outcomes. Recorded, not live. The physics is classical math; the quantum is the seed.';
let COPY={};try{COPY=await (await fetch('./copy.json')).json();}catch{}
const FONT=await (await fetch('./font.json')).json();
const T=(k,f)=>k.split('.').reduce((o,x)=>o&&o[x],COPY)??f;
const fmt=(s,o)=>s.replace(/\{(\w+)\}/g,(_,k)=>o[k]??'');

// ───────── synapse: every system is a node, every interaction a signal on one clock ─────────
const nodes={};const sigLog=[];let simTime=0;
function on(name,fn){(nodes[name]??=[]).push(fn);}
function signal(name,data){sigLog.unshift(simTime.toFixed(1)+'s  '+name);sigLog.length=Math.min(sigLog.length,8);(nodes[name]||[]).forEach(f=>f(data));}

// ───────── seeds ─────────
let SEED=null;const loaded=await Promise.all(SEEDS.map(loadSeed));
const R={next:()=>SEED.stream.next(),range:(a,b)=>SEED.stream.range(a,b),chance:p=>SEED.stream.chance(p),angle:()=>SEED.stream.angle()};

// ───────── renderer / targets ─────────
const canvas=$('c'),stage=$('stage');
const renderer=new THREE.WebGLRenderer({canvas,antialias:false,alpha:false});
renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.LinearSRGBColorSpace;
let ART_W=480,ART_H=300,PIX=3;
function mkRT(){const rt=new THREE.WebGLRenderTarget(ART_W,ART_H,{type:THREE.HalfFloatType,minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter,depthBuffer:true});rt.depthTexture=new THREE.DepthTexture(ART_W,ART_H);rt.depthTexture.type=THREE.FloatType;return rt;}
let rtMain=mkRT(),rtRefl=mkRT();
const scene=new THREE.Scene();
const world=new THREE.Group();scene.add(world);
const camera=new THREE.OrthographicCamera(-10,10,6,-6,-200,200);
const hemi=new THREE.HemisphereLight(0xcfe8ff,0xd8b880,0.9);scene.add(hemi);
const sun=new THREE.DirectionalLight(0xfff2d8,1.6);sun.position.set(-20,30,10);scene.add(sun);
const flood=[new THREE.PointLight(0xfff4d0,0,40,1.2),new THREE.PointLight(0xfff4d0,0,40,1.2)];flood[0].position.set(-10,7,-7);flood[1].position.set(10,7,-7);flood.forEach(l=>scene.add(l));
const lam=(c,e)=>new THREE.MeshLambertMaterial({color:c,emissive:e||0});
const vcm=()=>new THREE.MeshLambertMaterial({vertexColors:true});
const BOX=new THREE.BoxGeometry(1,1,1);
function box(w,h,d,c,x,y,z,parent=world){const m=new THREE.Mesh(BOX,typeof c==='object'?c:lam(c));m.scale.set(w,h,d);m.position.set(x,y,z);parent.add(m);return m;}
const reflHide=[];

// ───────── terrain: heights pressed into the island outline ─────────
const ISX=26,ISZ=17,inIsland=(x,z)=>Math.pow(Math.abs(x/ISX),4)+Math.pow(Math.abs(z/ISZ),4)<1;
const shoreZ=x=>7.6+1.3*Math.sin(x*0.12+0.5);
function sandH(x,z){let h;
 if(z<-8.5){const t=Math.min(1,(-8.5-z)/6);h=0.6+t*t*(2.2+0.6*Math.sin(x*0.45)+0.4*Math.sin(x*1.1+1));}
 else if(z<5)h=0.6;else{const s=shoreZ(x),k=0.6/(s-5);h=0.6-(z-5)*k;if(z>s)h=-(z-s)*0.32;}
 return Math.max(h,-2.6);}
function sandN(x,z){const e=0.05,dx=(sandH(x+e,z)-sandH(x-e,z))/(2*e),dz=(sandH(x,z+e)-sandH(x,z-e))/(2*e);return new THREE.Vector3(-dx,1,-dz).normalize();}
let sandMesh,seaMesh,seaGeo,seaBase,waveComps=[],speckle=[];
const SEA_Y=0;
function buildTerrain(){
 if(sandMesh){world.remove(sandMesh);world.remove(seaMesh);world.remove(seaWall);world.remove(cutWall);}
 const step=0.5,pos=[],nor=[],col=[],cut=[],cutC=[],wwall=[],wwallC=[];
 const sandC=[new THREE.Color(0xf6e3b4),new THREE.Color(0xecd29a),new THREE.Color(0xdcbd82)],wet=new THREE.Color(0xb08a58);
 const push=(x,z)=>{const h=sandH(x,z),n=sandN(x,z);pos.push(x,h,z);nor.push(n.x,n.y,n.z);
  const sp=R.next();let c=sandC[sp<0.7?0:sp<0.93?1:2].clone();const wb=Math.abs(h-0.0);if(h<0.25)c.lerp(wet,Math.min(1,(0.25-h)/0.35));if(h>1.2)c.lerp(new THREE.Color(0xc9a46c),0.25);col.push(c.r,c.g,c.b);};
 for(let x=-ISX;x<ISX;x+=step)for(let z=-ISZ;z<ISZ;z+=step){
  const cx=x+step/2,cz=z+step/2;if(!inIsland(cx,cz))continue;
  push(x,z);push(x,z+step);push(x+step,z);push(x+step,z);push(x,z+step);push(x+step,z+step);
  // cut side: edges whose neighbour is outside
  for(const [dx,dz,ax,az,bx,bz] of [[step,0,x+step,z,x+step,z+step],[-step,0,x,z+step,x,z],[0,step,x+step,z+step,x,z+step],[0,-step,x,z,x+step,z]]){
   if(inIsland(cx+dx,cz+dz))continue;const ha=sandH(ax,az),hb=sandH(bx,bz);const bands=[[0.3,0xe8cf98],[0.9,0xc9a46c],[1.8,0x8f6f48],[3.2,0x6e5640],[9,0x4a4038]];
   let top=[ha,hb];for(const [d,cc] of bands){const bot=[Math.max(-6,ha-d),Math.max(-6,hb-d)];const c=new THREE.Color(cc);
    cut.push(ax,top[0],az,bx,top[1],bz,ax,bot[0],az, bx,top[1],bz,bx,bot[1],bz,ax,bot[0],az);for(let i=0;i<6;i++)cutC.push(c.r,c.g,c.b);top=bot;if(bot[0]<=-6)break;}
   if(ha<SEA_Y||hb<SEA_Y){const layers=[[0.4,0x52d8d0],[1.0,0x26b8c0],[1.8,0x1674a0],[3,0x125484]];let t=SEA_Y;for(const [d,cc] of layers){const b=-d,c=new THREE.Color(cc);const fa=Math.max(ha,b),fb=Math.max(hb,b);if(t<=Math.min(fa,fb))break;
     wwall.push(ax+dx*0.002,t,az+dz*0.002,bx+dx*0.002,t,bz+dz*0.002,ax+dx*0.002,fa,az+dz*0.002, bx+dx*0.002,t,bz+dz*0.002,bx+dx*0.002,fb,bz+dz*0.002,ax+dx*0.002,fa,az+dz*0.002);for(let i=0;i<6;i++)wwallC.push(c.r,c.g,c.b);t=b;}}
  }}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
 sandMesh=new THREE.Mesh(g,vcm());world.add(sandMesh);reflHide.push(sandMesh);
 const cg=new THREE.BufferGeometry();cg.setAttribute('position',new THREE.Float32BufferAttribute(cut,3));cg.setAttribute('color',new THREE.Float32BufferAttribute(cutC,3));cg.computeVertexNormals();
 cutWall=new THREE.Mesh(cg,new THREE.MeshLambertMaterial({vertexColors:true,side:THREE.DoubleSide}));world.add(cutWall);reflHide.push(cutWall);
 const wg=new THREE.BufferGeometry();wg.setAttribute('position',new THREE.Float32BufferAttribute(wwall,3));wg.setAttribute('color',new THREE.Float32BufferAttribute(wwallC,3));wg.computeVertexNormals();
 seaWall=new THREE.Mesh(wg,new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide,transparent:true,opacity:0.92}));world.add(seaWall);reflHide.push(seaWall);
 // sea grid over the shore half of the island
 const sx=[],sidx=[];const res=0.6;const cols=Math.ceil(2*ISX/res)+1;let rows=0;const zs=[];for(let z=2;z<=ISZ+0.01;z+=res)zs.push(z);rows=zs.length;
 for(const z of zs)for(let i=0;i<cols;i++){const x=-ISX+i*res;sx.push(x,0,z);}
 for(let r=0;r<rows-1;r++)for(let i=0;i<cols-1;i++){const a=r*cols+i,b=a+1,c=a+cols,d=c+1;const mx=-ISX+(i+.5)*res,mz=zs[r]+res/2;if(!inIsland(mx,mz))continue;if(sandH(mx,mz)>0.5)continue;sidx.push(a,c,b,b,c,d);}
 seaGeo=new THREE.BufferGeometry();seaGeo.setAttribute('position',new THREE.Float32BufferAttribute(sx,3));seaGeo.setAttribute('color',new THREE.Float32BufferAttribute(new Float32Array(sx.length),3));seaGeo.setAttribute('normal',new THREE.Float32BufferAttribute(new Float32Array(sx.length),3));seaGeo.setIndex(sidx);
 seaBase=Float32Array.from(sx);seaMesh=new THREE.Mesh(seaGeo,seaMat);world.add(seaMesh);reflHide.push(seaMesh);
 // Gerstner components (phase offsets from the seed stream)
 waveComps=[[0.16,0.9,0.12,1.0],[0.10,1.6,-0.35,1.4],[0.06,2.6,0.6,2.1],[0.035,4.2,-0.9,2.9],[0.02,6.3,1.3,3.7]].map(([A,k,dir,w])=>({A,k,dx:Math.sin(dir),dz:Math.cos(dir),w,ph:R.angle()}));
}
let seaWall,cutWall;
const seaMat=new THREE.ShaderMaterial({vertexColors:true,transparent:true,uniforms:{refl:{value:null},res:{value:new THREE.Vector2(480,300)},t:{value:0},sunDir:{value:new THREE.Vector3(0,1,0)},sunCol:{value:new THREE.Color(1,1,1)},amb:{value:new THREE.Color(1,1,1)},glint:{value:1}},
 vertexShader:`varying vec3 vC;varying vec3 vN;varying vec3 vW;void main(){vC=color;vN=normal;vec4 w=modelMatrix*vec4(position,1.);vW=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}`,
 fragmentShader:`uniform sampler2D refl;uniform vec2 res;uniform float t;uniform vec3 sunDir;uniform vec3 sunCol;uniform vec3 amb;uniform float glint;varying vec3 vC;varying vec3 vN;varying vec3 vW;
 void main(){vec3 n=normalize(vN);vec2 uv=gl_FragCoord.xy/res+vec2(n.x,n.z)*0.02+vec2(sin(vW.z*3.+t*2.)*0.004,0.);vec4 r=texture2D(refl,uv);
 vec3 base=vC*(amb*0.75+sunCol*0.35*max(dot(n,sunDir),0.));float fres=0.35;vec3 c=mix(base,r.rgb,r.a*fres);
 vec3 v=normalize(vec3(1.,1.2,1.));float s=pow(max(dot(reflect(-sunDir,n),v),0.),60.)*glint;c+=sunCol*s*1.5;
 gl_FragColor=vec4(c,0.94);}`});
const deepC=new THREE.Color(0x125484),midC=new THREE.Color(0x1696b0),shallowC=new THREE.Color(0x52d8d0),foamC=new THREE.Color(0xeef4f6);
function seaHeight(x,z,t){let y=0;for(const c of waveComps){const d=Math.max(0.25,-sandH(x,z));const sh=Math.min(2.2,1/Math.sqrt(d/1.6));y+=c.A*sh*windWaveScale*Math.sin(c.k*(c.dx*x+c.dz*z)-c.w*t+c.ph);}return y;}
function updateSea(t){const p=seaGeo.attributes.position,col=seaGeo.attributes.color,nor=seaGeo.attributes.normal;const tmp=new THREE.Color();
 for(let i=0;i<p.count;i++){const x=seaBase[3*i],z=seaBase[3*i+2];const g=sandH(x,z),d=Math.max(0.25,-g),sh=Math.min(2.2,1/Math.sqrt(d/1.6));
  let y=0,ox=0,oz=0,nx=0,nz=0,amp=0;for(const c of waveComps){const A=c.A*sh*windWaveScale,ph=c.k*(c.dx*x+c.dz*z)-c.w*t+c.ph,s=Math.sin(ph),co=Math.cos(ph);y+=A*s;amp+=A;ox+=-c.dx*A*0.6*co;oz+=-c.dz*A*0.6*co;nx-=c.k*c.dx*A*co;nz-=c.k*c.dz*A*co;}
  p.setXYZ(i,x+ox,y,z+oz);const l=Math.hypot(nx,1,nz);nor.setXYZ(i,nx/l,1/l,nz/l);
  const depth=-g;tmp.copy(depth>2.2?deepC:depth>0.9?midC:shallowC);if(depth>0.9&&depth<=2.2)tmp.lerp(deepC,(depth-0.9)/1.3);else if(depth<=0.9)tmp.lerp(midC,Math.max(0,depth)/0.9);
  const crest=amp>0?y/amp:0;if((crest>0.55&&depth<1.6)||Math.abs(g-y)<0.07)tmp.lerp(foamC,0.85);col.setXYZ(i,tmp.r,tmp.g,tmp.b);}
 p.needsUpdate=col.needsUpdate=nor.needsUpdate=true;}
let windWaveScale=1;

// ───────── props ─────────
const props={palms:[],flags:[],lights:[],buoys:[],hatch:null,stringBulbs:[]};
const COURT={L:16,W:8,netH:2.43};
function buildProps(){
 const sandY=0.6;
 // court straps
 for(const [w,d,x,z] of [[16,0.06,0,4],[16,0.06,0,-4],[0.06,8,8,0],[0.06,8,-8,0],[0.06,8,0,0]])box(w,0.02,d,0x2e6cb8,x,sandY+0.01,z);
 // net
 const tex=new THREE.CanvasTexture((()=>{const c=document.createElement('canvas');c.width=64;c.height=16;const g=c.getContext('2d');g.strokeStyle='#d6e2e8';g.lineWidth=1;for(let i=0;i<=64;i+=8){g.beginPath();g.moveTo(i+.5,0);g.lineTo(i+.5,16);g.stroke();}for(let j=0;j<=16;j+=8){g.beginPath();g.moveTo(0,j+.5);g.lineTo(64,j+.5);g.stroke();}return c;})());
 tex.magFilter=THREE.NearestFilter;tex.wrapS=tex.wrapT=THREE.RepeatWrapping;tex.repeat.set(4,1);
 const net=new THREE.Mesh(new THREE.PlaneGeometry(8.5,1),new THREE.MeshBasicMaterial({map:tex,transparent:true,alphaTest:0.4,side:THREE.DoubleSide}));net.rotation.y=Math.PI/2;net.position.set(0,sandY+COURT.netH-0.5,0);world.add(net);props.net=net;
 box(0.05,0.07,8.6,0xffffff,0,sandY+COURT.netH,0);box(0.04,0.05,8.6,0xffffff,0,sandY+COURT.netH-1,0);
 for(const z of [-4,4]){for(let i=0;i<8;i++)box(0.03,0.11,0.03,i%2?0xffffff:0xe23c3c,0,sandY+COURT.netH-0.3+i*0.11,z);}
 for(const z of [-4.9,4.9]){box(0.12,2.6,0.12,0xd6e2e8,0,sandY+1.3,z);box(0.26,1.4,0.26,0x1c4cb0,0,sandY+0.7,z);
  const rope=new THREE.Mesh(BOX,lam(0xeef4f6));const a=new THREE.Vector3(0,sandY+2.5,z),b=new THREE.Vector3(0,sandY,z+Math.sign(z)*1.6);bone(rope,a,b,0.02);world.add(rope);}
 // palms
 const palmAt=[[-18,-11],[-13,-13.5],[15,-12],[20,-9],[-21,-4],[22,1]];
 for(const [x,z] of palmAt){const g=new THREE.Group();g.position.set(x,sandH(x,z),z);world.add(g);const lean=R.range(-0.25,0.25),segs=9;let p=new THREE.Vector3();const pts=[];
  for(let i=0;i<segs;i++){const q=new THREE.Vector3(Math.sin(i*0.12)*1.4*lean*i*0.4,i*0.75,lean*i*0.15);pts.push(q);const s=new THREE.Mesh(BOX,lam(i%2?0x8c5a3c:0x5c3a28));bone(s,p.clone(),q.clone(),0.28-i*0.012);g.add(s);p=q;}
  const crown=new THREE.Group();crown.position.copy(p);g.add(crown);const fronds=[];
  for(let i=0;i<8;i++){const f=new THREE.Group();f.rotation.y=i/8*Math.PI*2+R.range(-.2,.2);crown.add(f);const fr=[];let q=new THREE.Vector3();
   for(let j=0;j<5;j++){const n=new THREE.Vector3(0.55*(j+1),0.25-0.09*j*j,0);const m=new THREE.Mesh(BOX,lam(j<2?0x4c9838:0x2e7034));bone(m,q.clone(),n.clone(),0.12,0.55-0.06*j);f.add(m);fr.push(m);q=n;}fronds.push(f);}
  props.palms.push({g,crown,fronds,ph:R.angle()});}
 // dune grass
 for(let i=0;i<70;i++){const x=R.range(-24,24),z=R.range(-16,-9);if(!inIsland(x,z))continue;const b=box(0.05,R.range(0.3,0.7),0.05,0x7cbc48,x,0,z);b.position.y=sandH(x,z)+b.scale.y/2;b.userData.grass=R.angle();(props.grass??=[]).push(b);}
 // boardwalk
 for(let i=0;i<14;i++)box(1.6,0.08,0.45,i%2?0xc89060:0xb87e50,-14+i*0.0,sandY+0.06,-6-i*0.5+3.5);
 for(let i=0;i<10;i++)box(0.45,0.08,1.6,0xc89060,-12+i*0.5,sandY+0.06,-9.2);
 // kiosk
 const k=new THREE.Group();k.position.set(12,sandY,-9.5);world.add(k);box(4,2.4,2.4,0xf4d8bc,0,1.2,0,k);for(let i=0;i<8;i++)box(0.55,0.08,1.6,i%2?0xffffff:0xe86e6a,-1.9+i*0.55,2.5,1.6,k).rotation.x=0.35;
 props.hatch=box(2.2,0.9,0.05,lam(0x2c1a12),0,1.5,1.21,k);box(2.4,0.5,0.1,0x3a7cf0,0,2.95,0,k);box(0.2,1.9,0.5,0x26b8c0,2.3,0.95,0.6,k).rotation.z=-0.15;box(0.2,1.7,0.5,0xff7a5c,2.6,0.85,0.2,k).rotation.z=-0.2;
 box(0.8,0.5,0.5,0x3a7cf0,-2.6,0.25,1,k);box(0.8,0.06,0.5,0xffffff,-2.6,0.52,1,k);for(const x of [-0.8,0,0.8]){box(0.08,0.6,0.08,0x5c3a28,x,0.3,1.9,k);box(0.4,0.06,0.4,0xe86e6a,x,0.62,1.9,k);}
 // benches, shower, lifeguard tower
 for(const x of [-4,4]){box(2,0.08,0.45,0xb87e50,x,sandY+0.45,-6.6);box(0.1,0.45,0.4,0x5c3a28,x-0.9,sandY+0.22,-6.6);box(0.1,0.45,0.4,0x5c3a28,x+0.9,sandY+0.22,-6.6);}
 box(0.1,2.4,0.1,0xb4c2cc,-9.5,sandY+1.2,-7.8);box(0.6,0.06,0.15,0xb4c2cc,-9.3,sandY+2.4,-7.8);box(0.8,0.04,0.8,0x8a98a4,-9.5,sandY+0.02,-7.8);
 const tw=new THREE.Group();tw.position.set(-17,sandY,3);world.add(tw);for(const [x,z] of [[-.8,-.8],[.8,-.8],[-.8,.8],[.8,.8]])box(0.14,2.6,0.14,0xffffff,x,1.3,z,tw);box(2,0.15,2,0xd84c3c,0,2.6,0,tw);box(2,1,0.1,0xd84c3c,0,3.1,-1,tw);box(2.2,0.1,2.2,0xffffff,0,3.9,0,tw);box(0.06,1.8,0.06,0xd6e2e8,0.9,4.6,0.9,tw);
 const flag=new THREE.Group();flag.position.set(0.9,5.3,0.9);tw.add(flag);box(0.7,0.4,0.02,0xff7a5c,0.35,0,0,flag);props.flags.push(flag);
 // umbrellas, towels, chair, sandcastle, rowboat, fire pit
 for(const [x,z,c] of [[-6,-7.5,0xe86e6a],[6,-7.8,0x26b8c0],[-15,6,0xffe04a]]){box(0.06,2.2,0.06,0xffffff,x,sandY+1.1,z);for(let i=0;i<8;i++){const s=box(1.2,0.06,0.35,i%2?0xffffff:c,x,sandY+2.1,z);s.rotation.y=i/8*Math.PI*2;s.translateX(0.55);s.rotation.z=-0.25;}}
 box(1.8,0.02,0.8,0x3a7cf0,-6,sandY+0.01,-6.4);box(1.8,0.02,0.8,0xff9c2c,-15,sandY+0.01,5);
 const ch=new THREE.Group();ch.position.set(6.6,sandY,-6.8);world.add(ch);box(0.6,0.06,1.2,0xffffff,0,0.35,0,ch);const bk=box(0.6,0.9,0.06,0x26b8c0,0,0.75,-0.65,ch);bk.rotation.x=-0.4;
 props.castle=new THREE.Group();props.castle.position.set(-11,sandY,5.6);world.add(props.castle);box(1,0.4,1,0xdcbd82,0,0.2,0,props.castle);for(const [x,z] of [[-.4,-.4],[.4,-.4],[-.4,.4],[.4,.4]])box(0.25,0.6,0.25,0xecd29a,x,0.3,z,props.castle);box(0.3,0.5,0.3,0xecd29a,0,0.55,0,props.castle);
 const rb=new THREE.Group();rb.position.set(18,sandH(18,6.5),6.5);rb.rotation.y=0.5;world.add(rb);box(3,0.4,1.1,0xe8cf98,0,0.25,0,rb);box(2.6,0.1,0.9,0x8c5a3c,0,0.42,0,rb);box(0.3,0.06,1.1,0x5c3a28,0,0.5,0,rb);
 const fp=new THREE.Group();fp.position.set(-8,sandY,-11.5);world.add(fp);for(let i=0;i<8;i++){const s=box(0.3,0.2,0.3,0x8a98a4,Math.cos(i/8*6.28)*0.7,0.1,Math.sin(i/8*6.28)*0.7,fp);}
 box(1.2,0.15,0.15,0x5c3a28,0,0.18,0,fp).rotation.y=0.6;box(1.2,0.15,0.15,0x5c3a28,0,0.25,0,fp).rotation.y=-0.6;props.fire=[box(0.3,0.4,0.3,lam(0xff9c2c,0xff9c2c),0,0.4,0,fp),box(0.18,0.6,0.18,lam(0xffd868,0xffd868),0.05,0.45,0,fp)];
 // string lights on posts + floodlights
 const posts=[[-9,-7],[-3,-7.4],[3,-7.4],[9,-7]];for(const [x,z] of posts)box(0.1,3,0.1,0x5c3a28,x,sandY+1.5,z);
 for(let s=0;s<3;s++){const [x0,z0]=posts[s],[x1,z1]=posts[s+1];for(let i=1;i<8;i++){const t=i/8;const b=box(0.12,0.12,0.12,lam(0xfff6c0,0x000000),x0+(x1-x0)*t,sandY+2.9-Math.sin(t*Math.PI)*0.5,z0+(z1-z0)*t);props.stringBulbs.push(b);}}
 for(const x of [-10,10]){box(0.18,7,0.18,0x8a98a4,x,sandY+3.5,-7);const h=box(1,0.5,0.3,lam(0xd6e2e8),x,sandY+7,-6.8);props.lights.push(h);}
 // buoys on a rope
 for(let i=0;i<9;i++){const x=-12+i*3,z=14.2;if(!inIsland(x,z))continue;const b=box(0.35,0.35,0.35,i%2?0xff7a5c:0xffffff,x,0,z);props.buoys.push(b);}
}
function bone(m,a,b,t,w){const d=b.clone().sub(a),L=d.length();m.position.copy(a).add(b).multiplyScalar(0.5);m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());m.scale.set(w??t,Math.max(L,0.001),t);}

// ───────── people: box rigs with two-bone IK (law of cosines) ─────────
function ik2(root,target,l1,l2,pole){const d=target.clone().sub(root);let L=d.length();L=Math.min(Math.max(L,Math.abs(l1-l2)+1e-3),l1+l2-1e-3);d.normalize();
 const a=Math.acos(THREE.MathUtils.clamp((l1*l1+L*L-l2*l2)/(2*l1*L),-1,1));const side=pole.clone().sub(d.clone().multiplyScalar(pole.dot(d))).normalize();
 const mid=root.clone().add(d.clone().multiplyScalar(Math.cos(a)*l1)).add(side.multiplyScalar(Math.sin(a)*l1));const end=root.clone().add(d.multiplyScalar(L));return [mid,end];}
class Rig{constructor(shirt,shorts,skin,opts={}){this.g=new THREE.Group();world.add(this.g);const m=c=>new THREE.Mesh(BOX,lam(c));
  this.p={torso:m(shirt),pelvis:m(shorts),head:m(skin),uaL:m(skin),faL:m(skin),uaR:m(skin),faR:m(skin),thL:m(shorts),shL:m(skin),thR:m(shorts),shR:m(skin),ftL:m(0xffffff),ftR:m(0xffffff),neck:m(skin)};
  for(const k in this.p)this.g.add(this.p[k]);
  if(opts.cap){this.cap=m(opts.cap);this.brim=m(opts.cap);this.g.add(this.cap,this.brim);}if(opts.bun){this.bun=m(0x5c3a28);this.g.add(this.bun);}if(opts.glasses){this.gl=m(0x0e1834);this.g.add(this.gl);}
  this.pos=new THREE.Vector3();this.yaw=0;this.hipH=0.95;this.lean=0;this.handL=null;this.handR=null;this.footL=null;this.footR=null;this.phase=0;}
 pose(){const up=new THREE.Vector3(0,1,0),fw=new THREE.Vector3(Math.sin(this.yaw),0,Math.cos(this.yaw)),rt=new THREE.Vector3(fw.z,0,-fw.x);
  const hip=this.pos.clone().add(new THREE.Vector3(0,this.hipH,0));const tdir=up.clone().multiplyScalar(Math.cos(this.lean)).add(fw.clone().multiplyScalar(Math.sin(this.lean)));
  const chest=hip.clone().add(tdir.clone().multiplyScalar(0.55));bone(this.p.pelvis,hip.clone().sub(tdir.clone().multiplyScalar(0.08)),hip.clone().add(tdir.clone().multiplyScalar(0.12)),0.34,0.3);this.p.pelvis.scale.set(0.34,0.2,0.22);
  bone(this.p.torso,hip.clone().add(tdir.clone().multiplyScalar(0.1)),chest,0.22);this.p.torso.scale.x=0.36;this.p.torso.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(up,0));
  const torsoQ=new THREE.Quaternion().setFromUnitVectors(up,tdir).multiply(new THREE.Quaternion().setFromAxisAngle(up,this.yaw));this.p.torso.quaternion.copy(torsoQ);this.p.pelvis.quaternion.copy(torsoQ);
  const neckTop=chest.clone().add(tdir.clone().multiplyScalar(0.1));bone(this.p.neck,chest,neckTop,0.1);const head=neckTop.clone().add(tdir.clone().multiplyScalar(0.13));
  this.p.head.position.copy(head);this.p.head.quaternion.copy(torsoQ);this.p.head.scale.set(0.24,0.26,0.24);
  if(this.cap){this.cap.position.copy(head).add(tdir.clone().multiplyScalar(0.13));this.cap.quaternion.copy(torsoQ);this.cap.scale.set(0.26,0.07,0.26);this.brim.position.copy(this.cap.position).add(fw.clone().multiplyScalar(0.17));this.brim.quaternion.copy(torsoQ);this.brim.scale.set(0.24,0.03,0.14);}
  if(this.bun){this.bun.position.copy(head).add(tdir.clone().multiplyScalar(0.12)).sub(fw.clone().multiplyScalar(0.13));this.bun.scale.set(0.12,0.12,0.12);}
  if(this.gl){this.gl.position.copy(head).add(fw.clone().multiplyScalar(0.125)).add(tdir.clone().multiplyScalar(0.03));this.gl.quaternion.copy(torsoQ);this.gl.scale.set(0.22,0.05,0.02);}
  const sh=s=>chest.clone().add(rt.clone().multiplyScalar(0.21*s)).sub(tdir.clone().multiplyScalar(0.04));
  const def=s=>sh(s).add(new THREE.Vector3(0,-0.55,0)).add(rt.clone().multiplyScalar(0.05*s));
  for(const [s,ua,fa,tgt] of [[1,'uaL','faL',this.handL],[-1,'uaR','faR',this.handR]]){const S=sh(s);const [e,h]=ik2(S,tgt||def(s),0.3,0.3,fw.clone().multiplyScalar(-1).add(new THREE.Vector3(0,-0.5,0)));bone(this.p[ua],S,e,0.09);bone(this.p[fa],e,h,0.08);}
  const hp=s=>hip.clone().add(rt.clone().multiplyScalar(0.11*s));
  for(const [s,th,shn,ft,tgt] of [[1,'thL','shL','ftL',this.footL],[-1,'thR','shR','ftR',this.footR]]){const H=hp(s);const tg=tgt||H.clone().setY(this.pos.y+0.06);const [k,a]=ik2(H,tg,0.46,0.46,fw.clone().add(new THREE.Vector3(0,0.2,0)));
   bone(this.p[th],H,k,0.14);bone(this.p[shn],k,a,0.11);this.p[ft].position.copy(a).add(fw.clone().multiplyScalar(0.07)).setY(a.y-0.03);this.p[ft].quaternion.setFromAxisAngle(up,this.yaw);this.p[ft].scale.set(0.12,0.06,0.26);}}}

const players=[];const TEAMS=['CORAL','TEAL'];
function buildPeople(){
 const names=[T('teams.CORAL',[{name:'Juno'},{name:'Pip'}]),T('teams.TEAL',[{name:'Rook'},{name:'Sunny'}])];
 const look=[[0xff8a6c,0xc4486e,0xe0a880,{cap:0xffe04a}],[0xff8a6c,0xc4486e,0xc08060,{bun:true}],[0x26b8c0,0x0e5c5c,0x8c5a3c,{glasses:true}],[0x26b8c0,0x0e5c5c,0xf4d8bc,{cap:0xffffff,glasses:true}]];
 for(let t=0;t<2;t++)for(let i=0;i<2;i++){const L=look[t*2+i];const r=new Rig(L[0],L[1],L[2],L[3]);r.team=t;r.idx=i;r.name=names[t][i]?.name||'P';r.side=t===0?-1:1;
  r.home=new THREE.Vector3(r.side*4.5,0.6,i?2:-2);r.pos.copy(r.home);r.vel=new THREE.Vector3();r.target=r.home.clone();r.state='ready';r.st=0;r.y0=0;r.vy=0;r.air=false;players.push(r);}
 // beachgoers
 const bg=[];const mk=(c,s,k,o)=>{const r=new Rig(c,s,k,o);bg.push(r);return r;};
 const sun1=mk(0xffd868,0x3a7cf0,0xe0a880);sun1.pos.set(-6,0.6,-6.4);sun1.g.rotation.z=0;sun1.lying=true;
 const chair=mk(0xffffff,0x5c3a28,0xf4d8bc,{cap:0x26b8c0});chair.pos.set(6.6,0.6,-6.8);chair.seated=true;
 const c1=mk(0xff7a5c,0x1c4cb0,0x8c5a3c,{bun:true});c1.pos.set(-2,0.6,-6.2);c1.cheer=true;const c2=mk(0xffe04a,0x2e7034,0xe0a880);c2.pos.set(-0.8,0.6,-6.4);c2.cheer=true;
 const kid=mk(0x3cd0b0,0xff9c2c,0xc08060,{cap:0xe23c3c});kid.pos.set(-11.8,0.6,5.6);kid.kid=true;kid.g.scale.setScalar(0.6);
 const f1=mk(0x965c78,0x143a66,0xe0a880);f1.pos.set(-9.2,0.6,-11.5);f1.seated=true;const f2=mk(0x4c9838,0x5c3a28,0x5c3a28,{glasses:true});f2.pos.set(-6.8,0.6,-11.5);f2.seated=true;
 props.bg=bg;props.cheerers=[c1,c2];props.kid=kid;
 for(const r of bg){r.yaw=Math.atan2(-r.pos.x,-r.pos.z);if(r.kid)r.yaw=Math.atan2(props.castle.position.x-r.pos.x,props.castle.position.z-r.pos.z);r.cheerT=-1;}
 // gulls
 props.gulls=[];for(let i=0;i<4;i++){const g=new THREE.Group();world.add(g);const body=box(0.15,0.12,0.4,0xffffff,0,0,0,g);const wl=box(0.6,0.03,0.18,0xd6e2e8,-0.32,0,0,g),wr=box(0.6,0.03,0.18,0xd6e2e8,0.32,0,0,g);
  const sh=new THREE.Mesh(new THREE.PlaneGeometry(0.8,0.4),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:0.25,depthWrite:false}));sh.rotation.x=-Math.PI/2;world.add(sh);reflHide.push(sh);
  props.gulls.push({g,wl,wr,sh,cx:R.range(-12,12),cz:R.range(-4,10),r:R.range(5,10),h:R.range(7,11),a:R.angle(),sp:R.range(0.25,0.45),flap:true,mode:0,ph:0});}
}
function poseBeachgoers(t){for(const r of props.bg){r.handL=r.handR=r.footL=r.footR=null;r.lean=0;r.hipH=0.95*(r.kid?1:1);
 const fw=new THREE.Vector3(Math.sin(r.yaw),0,Math.cos(r.yaw)),rt=new THREE.Vector3(fw.z,0,-fw.x),b=r.pos;
 if(r.lying){r.hipH=0.12;r.lean=Math.PI/2;r.footL=b.clone().sub(fw.clone().multiplyScalar(0.9)).add(rt.clone().multiplyScalar(0.12)).setY(0.66);r.footR=b.clone().sub(fw.clone().multiplyScalar(0.9)).sub(rt.clone().multiplyScalar(0.12)).setY(0.66);r.handL=b.clone().add(fw.clone().multiplyScalar(0.8)).add(rt.clone().multiplyScalar(0.3)).setY(0.68);r.handR=b.clone().add(fw.clone().multiplyScalar(0.8)).sub(rt.clone().multiplyScalar(0.3)).setY(0.68);}
 else if(r.seated){r.hipH=0.42;r.lean=-0.15;r.footL=b.clone().add(fw.clone().multiplyScalar(0.55)).add(rt.clone().multiplyScalar(0.15)).setY(0.66);r.footR=b.clone().add(fw.clone().multiplyScalar(0.55)).sub(rt.clone().multiplyScalar(0.15)).setY(0.66);}
 else if(r.kid){r.hipH=0.5;r.lean=0.4;const pat=Math.max(0,Math.sin(t*(r.patT>t?9:2)))*0.15;r.handL=b.clone().add(fw.clone().multiplyScalar(0.45)).setY(0.95+pat);r.handR=r.handL.clone().add(rt.clone().multiplyScalar(-0.15));}
 else if(r.cheer){if(r.cheerT>t-2.2&&r.cheerT<t){const k=t-r.cheerT,clap=Math.abs(Math.sin(k*12))*0.12;const top=b.clone().setY(2.4+0.05*Math.sin(k*10));r.handL=top.clone().add(rt.clone().multiplyScalar(0.06+clap));r.handR=top.clone().sub(rt.clone().multiplyScalar(0.06+clap));r.pos.y=0.6+Math.max(0,Math.sin(k*7))*0.12;}else r.pos.y=0.6;}
 r.pose();}}

// ───────── wind: base + gust fronts (stream-seeded) ─────────
const WIND={mode:1,base:[0.4,3.5,6.5],dir:0.6,gust:0,gustT:0,next:3,speed:0,vec:new THREE.Vector3()};
function updateWind(dt){WIND.next-=dt;if(WIND.next<=0){WIND.gustT=0;WIND.gustAmp=WIND.base[WIND.mode]*R.range(0.3,0.9);WIND.dirJ=R.range(-0.35,0.35);WIND.next=R.range(4,12)/(WIND.mode+1)*2;signal('gust front',WIND.gustAmp);}
 WIND.gustT+=dt;const env=WIND.gustAmp?Math.min(1,WIND.gustT/1.2)*Math.exp(-Math.max(0,WIND.gustT-1.2)/2.5):0;
 WIND.speed=WIND.base[WIND.mode]+(WIND.gustAmp||0)*env;const d=WIND.dir+(WIND.dirJ||0)*env;WIND.vec.set(Math.sin(d),0,Math.cos(d)).multiplyScalar(WIND.speed);windWaveScale=0.6+WIND.speed/8;}

// ───────── ball: ballistic ODE in substeps (gravity, quadratic drag, wind, float wobble) ─────────
const G=9.81,KD=0.012,BALL_R=0.105;
const ballMesh=new THREE.Mesh(new THREE.IcosahedronGeometry(BALL_R,1),new THREE.MeshLambertMaterial({color:0xffe04a}));world.add(ballMesh);
const ballStripe=box(0.03,0.22,0.22,0x3a7cf0,0,0,0,ballMesh);ballStripe.scale.set(0.3,2.1,2.1);
const ball={p:new THREE.Vector3(0,3,0),v:new THREE.Vector3(),wob:0,wobPh:0,state:'held',holder:null,inSea:false,rest:false};
function accel(p,v,wind,wob,wobPh,t,out){const rel=v.clone().sub(wind);const s=rel.length();out.copy(rel).multiplyScalar(-KD*s/0.27);out.y-=G;
 if(wob>0){const lat=new THREE.Vector3(-v.z,0,v.x).normalize();out.add(lat.multiplyScalar(wob*Math.sin(t*9+wobPh)));}return out;}
function stepBall(b,dt,wind,t){const n=4,h=dt/n,a=new THREE.Vector3();for(let i=0;i<n;i++){accel(b.p,b.v,wind,b.wob,b.wobPh,t+i*h,a);b.v.addScaledVector(a,h);b.p.addScaledVector(b.v,h);}}
function predict(p,v,windScale=1,wob=0,maxT=4){const pts=[];const b={p:p.clone(),v:v.clone(),wob:0,wobPh:0};const w=WIND.vec.clone().multiplyScalar(windScale);let t=0;const dt=1/60;
 while(t<maxT){stepBall(b,dt,w,t);t+=dt;pts.push({t,p:b.p.clone(),v:b.v.clone()});if(b.p.y<groundAt(b.p.x,b.p.z)+BALL_R)break;}return pts;}
function groundAt(x,z){return inIsland(x,z)?Math.max(sandH(x,z),SEA_Y):SEA_Y-5;}
// shot solver: lob to apex by iteration; drive by bisection on launch angle with drift correction; wind at 70%
function solveLob(from,target,apex){let v=new THREE.Vector3();const vy=Math.sqrt(2*G*Math.max(0.3,apex-from.y));let dir=target.clone().sub(from).setY(0);const T0=(vy+Math.sqrt(vy*vy+2*G*Math.max(0,from.y-target.y)))/G;v.copy(dir).multiplyScalar(1/T0).setY(vy);
 for(let it=0;it<7;it++){const pts=predict(from,v,0.7);const end=pts[pts.length-1];if(!end)break;const miss=target.clone().sub(end.p).setY(0);v.addScaledVector(miss,1/end.t);}return v;}
function solveDrive(from,target,speed){const dir=target.clone().sub(from).setY(0);const dist=dir.length();dir.normalize();let aim=target.clone();let v=new THREE.Vector3();
 for(let it=0;it<3;it++){const d2=aim.clone().sub(from).setY(0);const dl=d2.length();const dn=d2.normalize();let lo=-0.9,hi=0.5;
  for(let k=0;k<16;k++){const a=(lo+hi)/2;v.copy(dn).multiplyScalar(Math.cos(a)*speed).setY(Math.sin(a)*speed);const pts=predict(from,v,0.7);const e=pts[pts.length-1].p.clone().sub(from).setY(0).dot(dn);if(e>dl)hi=a;else lo=a;}
  const pts=predict(from,v,0.7);const miss=target.clone().sub(pts[pts.length-1].p).setY(0);aim.add(miss);}
 return v;}

// ───────── game ─────────
const game={score:[0,0],sets:[0,0],set:1,server:{team:0,idx:0},phase:'prep',touches:0,lastTeam:-1,lastToucher:null,status:'',statusT:0,attackStyle:0,call:null,wait:1.5,serving:null,plan:null,fetcher:null,over:false};
const callMarker=new THREE.Group();world.add(callMarker);box(0.9,0.04,0.12,0xe23c3c,0,0,0,callMarker).rotation.y=0.785;box(0.9,0.04,0.12,0xe23c3c,0,0,0,callMarker).rotation.y=-0.785;callMarker.visible=false;
function setStatus(k,o={}){game.status=fmt(T('status.'+k,k),o);game.statusT=simTime;}
function teamSide(t){return t===0?-1:1;}
function sideOf(x){return x<0?0:1;}
function inCourt(p,m=0){return Math.abs(p.x)<=8+m&&Math.abs(p.z)<=4+m;}
function newMatch(){game.score=[0,0];game.sets=[0,0];game.set=1;game.server={team:0,idx:0};game.over=false;newRally();}
function newRally(){game.touches=0;game.lastTeam=-1;game.lastToucher=null;game.phase='prep';game.plan=null;game.wait=1.4;ball.wob=0;ball.inSea=false;ball.rest=false;
 for(const p of players){p.state='walk';p.target=p.home.clone();}const s=server();s.target=new THREE.Vector3(s.side*8.8,0.6,s.idx?1.5:-1.5);
 ball.state='held';ball.holder=s;setStatus('serve',{team:TEAMS[game.server.team]});}
const server=()=>players[game.server.team*2+game.server.idx];
function pointTo(team,why){if(game.phase==='dead')return;game.phase='dead';game.score[team]++;setStatus(why||'point',{team:TEAMS[team]});signal('point scored',team);
 if(game.server.team!==team){game.server={team,idx:1-((game.lastServerIdx?.[team])??1)};}(game.lastServerIdx??=[1,1])[team]=game.server.idx;
 const [a,b]=game.score,tgt=game.set===3?15:15;const won=(a>=tgt||b>=tgt)&&Math.abs(a-b)>=2;
 if(won){const w=a>b?0:1;game.sets[w]++;setTimeout0(()=>{setStatus(game.sets[w]>=2?'match_won':'set_won',{team:TEAMS[w]});if(game.sets[w]>=2)game.over=true;game.score=[0,0];game.set++;},1.2);}
 else if(Math.max(a,b)>=tgt-1&&a!==b){const lead=a>b?0:1;setTimeout0(()=>setStatus(game.sets[lead]===1?'match_point':'set_point'),1.2);}
 for(const p of players)if(p.team===team){p.state='celebrate';p.st=0;}
 game.wait=3.2;game.afterDead='fetch';}
const timers=[];function setTimeout0(f,d){timers.push({t:simTime+d,f});}
on('point scored',team=>{for(const c of props.cheerers)c.cheerT=simTime+R.range(0.1,0.9);props.kid.patT=simTime+R.range(0.5,1.5);});
on('gust front',a=>{for(const p of props.palms)p.kick=(p.kick||0)+a*0.04;});
on('ball in sea',()=>{ball.inSea=true;});

function pickReceiver(team,pts,h,exclude){let best=null;const contact=pts.findIndex((q,i)=>i>2&&q.v.y<0&&q.p.y<=h+0.6+(h<1.2?0:0)&&sideOf(q.p.x)===team);if(contact<0)return null;const c=pts[contact];
 for(const p of players){if(p.team!==team||p===exclude)continue;const d=p.pos.clone().setY(0).distanceTo(c.p.clone().setY(0));const tt=d/5.2+0.22;const late=tt-c.t;
  const zone=(c.p.z<0)===(p.idx===0)?0:0.15;const score=late+zone;if(!best||score<best.score)best={p,score,late,c};}return best;}
function planTouch(){ // ball is flying toward side S
 const S=sideOf(ball.p.x+ball.v.x*0.3);const pts=predict(ball.p,ball.v,1,ball.wob);if(!pts.length)return;const land=pts[pts.length-1].p;
 const team=game.lastTeam===-1?1-game.server.team:(sideOf(land.x));
 const touch=game.lastTeam===team?game.touches:0;const H=[0.95,2.3,2.9][touch];
 if(touch===0&&!inCourt(land,-0.15)&&!inCourt(land,0.25)===true){game.plan={team,leave:true};for(const p of players)if(p.team===team){p.target=land.clone().multiplyScalar(0).add(p.pos);}return;}
 if(touch===0&&!inCourt(land,0.3)){game.plan={team,leave:true};return;}
 if(game.lastTeam===-1&&R.chance(0.035)){game.plan={team,leave:true,seam:true};setStatus('seam');signal('seam',team);return;}
 const pick=pickReceiver(team,pts,H,game.lastTeam===team?game.lastToucher:null);if(!pick){game.plan={team,leave:true};return;}
 const c=pick.c;const off=new THREE.Vector3(teamSide(team)*0.25,0,0);game.plan={team,p:pick.p,touch,H,c,dive:pick.late>0&&pick.late<0.5,late:Math.max(0,pick.late)};
 pick.p.target=c.p.clone().add(off).setY(0.6);pick.p.state=touch===2?'approach':'run';
 for(const q of players)if(q.team===team&&q!==pick.p){q.state='run';q.target=touch===0?new THREE.Vector3(teamSide(team)*1.6,0.6,-c.p.z*0.3):touch===1?new THREE.Vector3(teamSide(team)*5.5,0.6,-Math.sign(c.p.z||1)*1.5):new THREE.Vector3(teamSide(team)*2.5,0.6,c.p.z*0.5);}
 const other=1-team;const opp=players.filter(q=>q.team===other);
 if(touch===2){const bl=opp.reduce((a,b)=>Math.abs(a.pos.x)<Math.abs(b.pos.x)?a:b);bl.state='block';bl.target=new THREE.Vector3(teamSide(other)*0.5,0.6,THREE.MathUtils.clamp(c.p.z,-3.6,3.6));const dd=opp.find(q=>q!==bl);dd.state='run';dd.target=new THREE.Vector3(teamSide(other)*6,0.6,-Math.sign(c.p.z||1)*1.8);game.blocker=bl;}
 else{for(const q of opp){q.state='run';q.target=new THREE.Vector3(teamSide(other)*4.5,0.6,q.idx?2:-2);}game.blocker=null;}}
function contact(p,plan){const team=p.team,side=teamSide(team),opp=-side;const inSpeed=ball.v.length();game.lastTeam=team;game.lastToucher=p;game.touches=plan.touch+1;signal('contact',p.name);ball.wob=0;
 const from=ball.p.clone();let v;
 if(plan.touch===0||plan.touch===1&&false){ // pass / dig
  const err=0.25+0.05*inSpeed+0.08*WIND.speed+1.6*plan.late;const a=R.angle(),m=err*R.next();let tgt=new THREE.Vector3(side*1.6+Math.cos(a)*m,1,Math.sin(a)*m);
  if(inSpeed>13&&R.chance(0.14)){tgt=new THREE.Vector3(side*R.range(2,12),0,R.range(-9,9));signal('shank',p.name);}
  v=solveLob(from,tgt,R.range(3.6,4.8));p.state=plan.dive?'dive':'bump';
 }else if(plan.touch===1){const att=players.find(q=>q.team===team&&q!==p);const z=THREE.MathUtils.clamp(att.pos.z,-3,3);const tgt=new THREE.Vector3(side*1.2,2.6,z);v=solveLob(from,tgt.clone().setY(1.0),R.range(4.6,5.6));p.state=ball.p.y<1.6?'bump':'set';
 }else{ // attack
  const style=game.attackStyle,b=game.blocker;const cands=[];
  for(const [x,z,kind] of [[opp*7.4,3.4,'line'],[opp*7.4,-3.4,'line'],[opp*7,0,'deep'],[opp*3,3.5,'cut'],[opp*3,-3.5,'cut'],[opp*2,0,'poke'],[opp*6.5,1.8,'cross'],[opp*6.5,-1.8,'cross']]){
   const t=new THREE.Vector3(x,0.6,z*(Math.sign(from.z||1)*(kind==='line'?1:-1)));let s=0;for(const q of players)if(q.team!==team)s+=Math.min(4,q.pos.distanceTo(t));if(b)s+=Math.abs(b.pos.z-t.z)*0.8;if(game.call&&sideOf(game.call.x)!==team){s-=game.call.distanceTo(t)*3;}cands.push({t,s,kind});}
  cands.sort((a,b)=>b.s-a.s);const pick=game.call&&sideOf(game.call.x)!==team?{t:game.call.clone().setY(0.6),kind:'called'}:cands[0];if(game.call&&sideOf(game.call.x)!==team){game.call=null;callMarker.visible=false;}
  const spike=style===1||(style===0&&(from.y>2.6&&R.chance(0.7)));
  let tgt=pick.t.clone();if(R.chance(0.05))tgt.x+=opp*R.range(1.5,3);
  v=spike&&pick.kind!=='poke'?solveDrive(from,tgt,R.range(15,19)):solveLob(from,tgt,R.range(3.4,4.2));
  if(R.chance(0.04))v.y-=2.5; // stream-seeded net error
  p.state='spikehit';p.st=0;signal('attack',spike?'spike':'shot');
  // block
  if(b&&b.air){const pts=predict(from,v,1);const cross=pts.find(q=>Math.abs(q.p.x)<0.35);if(cross&&Math.abs(cross.p.z-b.pos.z)<0.7&&cross.p.y<b.pos.y+2.75+0.6){const r=R.next();
    if(r<0.35){v.set(-v.x*0.45,-2,v.z*0.3);setStatus('stuff');signal('stuff',b.name);}else if(r<0.7){v.multiplyScalar(0.35);v.y=3.2;game.blockTouch=b.team;signal('soft block',b.name);}else{v.x*=0.8;v.z+=R.range(-5,5);v.y=4;signal('off the fingers',b.name);}}}
 }
 ball.v.copy(v);ball.state='flying';game.phase='rally';if(game.blockTouch!==undefined&&game.blockTouch!==null){game.lastTeam=game.blockTouch;game.touches=1;game.lastToucher=null;game.blockTouch=null;}
 game.plan=null;game.replan=0.05;}
function serveBall(){const s=server();const side=teamSide(s.team),opp=-side;const flat=R.chance(0.4);ball.state='flying';ball.holder=null;ball.p.copy(s.pos).add(new THREE.Vector3(0,2.9,0));
 let tgt=new THREE.Vector3(opp*R.range(3.5,7.6),0.6,R.range(-3.6,3.6));if(R.chance(0.04))tgt.x=opp*R.range(8.4,10);
 let v=flat?solveDrive(ball.p,tgt,R.range(16,19)):solveLob(ball.p,tgt,R.range(4.2,5.4));if(R.chance(0.035))v.y-=1.8;
 ball.v.copy(v);ball.wob=flat?0:R.range(0.6,1.6);ball.wobPh=R.angle();game.phase='rally';game.touches=0;game.lastTeam=-1;game.serveTeam=s.team;s.state='servehit';s.st=0;game.replan=0.05;signal('serve',flat?'flat':'float');setStatus('rally');}
function crossingNet(prev){if(Math.sign(prev.x)===Math.sign(ball.p.x)||prev.x===0)return;const y=ball.p.y-0.6,z=Math.abs(ball.p.z);
 if(z>4&&z<4.3&&y<COURT.netH+0.6){setStatus('antenna');pointTo(1-sideOf(prev.x),'antenna');return;}
 if(z<=4.25&&y<COURT.netH+BALL_R){signal('net',y);if(y>COURT.netH-0.12){ball.v.x*=0.25;ball.v.y=Math.abs(ball.v.y)*0.3+0.6;ball.v.x+= (R.chance(0.5)?1:-1)*0.4;}else{ball.p.x=prev.x;ball.v.x*=-0.15;ball.v.z*=0.4;}}}
function ballLanded(){const g=sandH(ball.p.x,ball.p.z);signal('ball landed',ball.p.clone());
 if(!inIsland(ball.p.x,ball.p.z)||g<SEA_Y-0.05){signal('ball in sea');}else{puff(ball.p);mark(ball.p,0.22);}
 if(game.phase!=='rally')return;const S=sideOf(ball.p.x);const inside=inCourt(ball.p,BALL_R);
 if(inside){pointTo(1-S,game.lastTeam===-1?'ace':'point');}else{const loser=game.lastTeam===-1?game.serveTeam:game.lastTeam;setStatus('out');pointTo(1-loser,'out');}}

// ───────── particles: puffs, footprints & ball marks (instanced dents that fade) ─────────
const MARKS=400;const markMesh=new THREE.InstancedMesh(new THREE.CylinderGeometry(0.5,0.5,0.02,6),new THREE.MeshLambertMaterial({color:0xc9a46c}),MARKS);markMesh.count=MARKS;world.add(markMesh);reflHide.push(markMesh);
const marks=[];let markI=0;const _m=new THREE.Matrix4();for(let i=0;i<MARKS;i++){marks.push({life:0,p:new THREE.Vector3(),s:0});markMesh.setMatrixAt(i,_m.makeScale(0,0,0));}
function mark(p,s){const m=marks[markI];markI=(markI+1)%MARKS;m.life=1;m.p.set(p.x,sandH(p.x,p.z)+0.005,p.z);m.s=s;}
const puffs=[];const puffGeo=new THREE.BoxGeometry(0.12,0.12,0.12),puffMat=lam(0xf6e3b4);
function puff(p){for(let i=0;i<8;i++){const m=new THREE.Mesh(puffGeo,puffMat);m.position.set(p.x,sandH(p.x,p.z)+0.1,p.z);world.add(m);reflHide.push(m);const a=R.angle();puffs.push({m,v:new THREE.Vector3(Math.cos(a)*1.2,R.range(1,2.2),Math.sin(a)*1.2),life:0.7});}}

// ───────── player update ─────────
function movePlayer(p,dt){const to=p.target.clone().sub(p.pos).setY(0);const d=to.length();const max=p.state==='walk'?2.2:p.state==='fetch'?4:5.2;
 if(d>0.05){to.normalize();p.vel.lerp(to.multiplyScalar(Math.min(max,d*4)),Math.min(1,dt*8));}else p.vel.multiplyScalar(Math.max(0,1-dt*10));
 p.pos.addScaledVector(p.vel,dt);const gy=Math.max(sandH(p.pos.x,p.pos.z),-0.3);if(p.air){p.vy-=G*dt;p.y0+=p.vy*dt;if(p.y0<=0){p.y0=0;p.air=false;mark(p.pos,0.1);}}p.pos.y=gy+p.y0;
 const sp=p.vel.length();if(sp>0.3){p.phase+=dt*sp*2.6;p.yaw=lerpAngle(p.yaw,Math.atan2(p.vel.x,p.vel.z),dt*10);if(Math.floor(p.phase/Math.PI)!==p.lastStep){p.lastStep=Math.floor(p.phase/Math.PI);if(gy>0.05)mark(p.pos.clone().add(new THREE.Vector3(Math.cos(p.yaw)*0.1*(p.lastStep%2?1:-1),0,0)),0.08);}}
 else{const look=ball.p.clone().sub(p.pos);p.yaw=lerpAngle(p.yaw,Math.atan2(look.x,look.z),dt*6);}}
function lerpAngle(a,b,t){let d=((b-a+Math.PI)%(Math.PI*2)+Math.PI*2)%(Math.PI*2)-Math.PI;return a+d*Math.min(1,t);}
function posePlayer(p,t){p.st+=1/120;const fw=new THREE.Vector3(Math.sin(p.yaw),0,Math.cos(p.yaw)),rt=new THREE.Vector3(fw.z,0,-fw.x),b=p.pos.clone();const sp=p.vel.length();
 p.handL=p.handR=p.footL=p.footR=null;p.lean=0.1;p.hipH=0.95;
 const feet=(w,stride)=>{const s=Math.sin(p.phase)*stride;p.footL=b.clone().add(rt.clone().multiplyScalar(w)).add(fw.clone().multiplyScalar(s)).setY(b.y-p.y0+0.06+Math.max(0,Math.cos(p.phase))*stride*0.4);p.footR=b.clone().sub(rt.clone().multiplyScalar(w)).sub(fw.clone().multiplyScalar(s)).setY(b.y-p.y0+0.06+Math.max(0,-Math.cos(p.phase))*stride*0.4);};
 const H=(f,u,r)=>b.clone().add(fw.clone().multiplyScalar(f)).add(rt.clone().multiplyScalar(r)).setY(b.y+u);
 const st=p.state;
 if(p.air){p.footL=H(-0.1,0.15-0.3,0.12);p.footR=H(0.1,-0.1,-0.12);p.footL.y=b.y+0.1;p.footR.y=b.y+0.05;}
 else if(sp>0.6){feet(0.11,Math.min(0.4,sp*0.08));p.lean=0.25;p.hipH=0.92-Math.abs(Math.sin(p.phase))*0.04;}else{feet(0.2,0);p.hipH=0.82;}
 if(st==='bump'&&p.st<0.6){p.handL=H(0.42,0.75,0.03);p.handR=H(0.42,0.75,-0.03);p.hipH=0.7;p.lean=0.35;}
 else if(st==='dive'&&p.st<1.1){p.hipH=0.3;p.lean=1.35;p.handL=H(1.2,0.25,0.12);p.handR=H(1.2,0.25,-0.12);p.footL=H(-0.9,0.1,0.15);p.footR=H(-0.9,0.1,-0.15);}
 else if(st==='set'&&p.st<0.6){p.handL=H(0.12,1.95,0.13);p.handR=H(0.12,1.95,-0.13);}
 else if(st==='approach'||st==='spike'){if(p.air){const k=Math.min(1,p.st/0.35);p.handR=H(-0.2+0.1*k,1.9,-0.25);p.handL=H(0.3,1.9,0.2);}else{p.handL=H(-0.3,0.6,0.25);p.handR=H(-0.3,0.6,-0.25);p.lean=0.4;}}
 else if(st==='spikehit'&&p.st<0.6){p.handR=H(0.45,0.9+Math.max(0,0.9-p.st*3),-0.2);p.handL=H(0.2,1.0,0.2);p.lean=0.3;}
 else if(st==='block'&&(p.air||p.st<0.9)){p.handL=H(0.15,2.25,0.15);p.handR=H(0.15,2.25,-0.15);}
 else if(st==='serve'||st==='hold'||(ball.holder===p)){if(game.tossing){p.handL=H(0.3,2.0,0.15);p.handR=H(-0.25,1.8,-0.25);}else{p.handL=H(0.35,1.05,0.1);p.handR=H(0.35,1.05,-0.1);}}
 else if(st==='servehit'&&p.st<0.5){p.handR=H(0.5,1.7-p.st,-0.15);p.handL=H(0.2,0.9,0.2);}
 else if(st==='celebrate'&&p.st<2.5){const k=p.st;p.handL=H(0.1,2.0+0.1*Math.sin(k*9),0.25);p.handR=H(0.1,2.0+0.1*Math.sin(k*9+1),-0.25);if(!p.air&&k<1.2&&Math.sin(k*8)>0.97){p.air=true;p.vy=2.2;}}
 else if(game.phase==='rally'||game.phase==='prep'){p.handL=H(0.3,0.75,0.18);p.handR=H(0.3,0.75,-0.18);}
 p.pose();}
function handPos(p){return p.p.faL.position.clone().add(p.p.faR.position).multiplyScalar(0.5).add(new THREE.Vector3(Math.sin(p.yaw),0,Math.cos(p.yaw)).multiplyScalar(0.15));}

// ───────── simulation step ─────────
let paused=false;
function sim(dt){simTime+=dt;updateWind(dt);for(let i=timers.length-1;i>=0;i--)if(timers[i].t<=simTime){const f=timers[i].f;timers.splice(i,1);f();}
 // gulls: flap or glide (choice drawn from the stream)
 for(const g of props.gulls){g.ph-=dt;if(g.ph<=0){g.flap=R.chance(0.45);g.ph=R.range(1,4);}g.a+=dt*g.sp;g.flapT=(g.flapT||0)+dt;}
 for(const p of players)movePlayer(p,dt);
 if(game.over){if(game.wait>0){game.wait-=dt;}return;}
 if(game.phase==='prep'){const s=server();ball.holder=s;if(s.pos.distanceTo(s.target)<0.15){game.wait-=dt;if(game.wait<0.6&&!game.tossing){game.tossing=true;}if(game.wait<=0){game.tossing=false;serveBall();}}}
 else if(game.phase==='rally'||game.phase==='dead'||game.phase==='loose'){if(ball.state==='flying'){const prev=ball.p.clone();stepBall(ball,dt,WIND.vec,simTime);crossingNet(prev);
   if(Math.abs(ball.p.x)<0.3&&Math.abs(Math.abs(ball.p.z)-4.9)<0.15&&ball.p.y<3.2){ball.v.z*=-0.5;ball.v.x*=-0.3;signal('post');}
   const gy=groundAt(ball.p.x,ball.p.z);if(ball.p.y<=gy+BALL_R&&ball.v.y<0){if(gy<=SEA_Y+0.001){ball.state='sea';ball.p.y=SEA_Y;ballLanded();}else{ball.p.y=gy+BALL_R;const fast=ball.v.length();ball.v.y=-ball.v.y*0.18;ball.v.x*=0.35;ball.v.z*=0.35;if(game.phase==='rally')ballLanded();if(fast<2){ball.state='rolling';}}}
   if(game.phase==='rally'){game.replan-=dt;if(game.replan<=0&&!game.plan){planTouch();game.replan=99;}
    const pl=game.plan;if(pl&&pl.p){const p=pl.p;if(pl.touch===2&&!p.air){const tt=pl.c.t;const pts=predict(ball.p,ball.v,1,0,3);const c=pts.find(q=>q.v.y<0&&q.p.y<=pl.H+0.85);if(c&&c.t<0.42&&c.t>0.2&&p.pos.distanceTo(p.target)<1.4){p.air=true;p.vy=4.1;p.st=0;p.state='spike';}}
     if(game.blocker&&!game.blocker.air&&pl.touch===2&&p.air&&p.st>0.05){game.blocker.air=true;game.blocker.vy=3.6;game.blocker.st=0;}
     const reach=pl.dive?1.6:pl.touch===2?0.9:0.8;const hc=p.pos.clone().add(new THREE.Vector3(0,pl.touch===2?(p.air?2.75:2.2):pl.touch===1?2.0:0.85,0));
     if(ball.v.y<0&&ball.p.y<=hc.y+0.25&&ball.p.clone().setY(0).distanceTo(p.pos.clone().setY(0))<reach&&Math.abs(ball.p.y-hc.y)<0.9)contact(p,pl);
     else if(ball.v.y<0&&ball.p.y<hc.y-0.7&&sideOf(ball.p.x)===pl.team){/* missed: let it fall */}}
    if(!game.plan&&game.replan>50&&ball.state==='flying')game.replan=0.25;}}
  else if(ball.state==='rolling'){ball.v.multiplyScalar(Math.max(0,1-dt*3));ball.p.addScaledVector(ball.v,dt);ball.p.y=sandH(ball.p.x,ball.p.z)+BALL_R;if(sandH(ball.p.x,ball.p.z)<SEA_Y){ball.state='sea';signal('ball in sea');}}
  else if(ball.state==='sea'){ // buoyancy + drift
   const sh=seaHeight(ball.p.x,ball.p.z,simTime);ball.p.y+=(sh+0.03-ball.p.y)*Math.min(1,dt*6);ball.p.x+=WIND.vec.x*0.04*dt;ball.p.z+=(WIND.vec.z*0.04-0.05)*dt;
   const back=Math.max(Math.abs(ball.p.x)-ISX+2,0);if(!inIsland(ball.p.x,ball.p.z-1)){ball.p.z-=dt*0.5;}}
  if(game.phase==='dead'){game.wait-=dt;if(game.wait<=0&&!game.fetcher){if(game.over){return;}
    const s=server();const cand=players.filter(q=>q!==s);const f=cand.reduce((a,b)=>a.pos.distanceTo(ball.p)<b.pos.distanceTo(ball.p)?a:b);game.fetcher=f;f.state='fetch';f.target=ball.p.clone();
    if(ball.inSea)setStatus('fetch');for(const p of players)if(p!==f){p.state='walk';p.target=p===s?new THREE.Vector3(s.side*8.8,0.6,s.idx?1.5:-1.5):p.home.clone();}}
   if(game.fetcher){const f=game.fetcher;if(ball.holder!==f){f.target.copy(ball.p).setY(0.6);if(f.pos.clone().setY(0).distanceTo(ball.p.clone().setY(0))<0.5){ball.holder=f;ball.state='held';game.throwIn=0.6;}}
    else{f.target.copy(f.pos);game.throwIn-=dt;if(game.throwIn<=0){const s=server();ball.holder=null;ball.state='lob';ball.p.copy(handPos(f));ball.v.copy(solveLob(ball.p,s.pos.clone().add(new THREE.Vector3(0,1.1,0)),Math.max(ball.p.y,1.6)+2.2));game.fetcher=null;game.phase='loose';}}}}
  if(game.phase==='loose'){if(ball.state==='lob'){stepBall(ball,dt,WIND.vec.clone().multiplyScalar(0.7),simTime);const s=server();if(ball.p.distanceTo(s.pos.clone().add(new THREE.Vector3(0,1.1,0)))<0.7||ball.p.y<sandH(ball.p.x,ball.p.z)+BALL_R){ball.state='held';newRally();}}}
 }
 if(ball.state==='held'&&ball.holder){const h=ball.holder;if(game.tossing&&h===server()){const k=Math.max(0,0.6-game.wait)/0.6;ball.p.copy(h.pos).add(new THREE.Vector3(Math.sin(h.yaw)*0.3,1.2+Math.sin(k*Math.PI)*1.9+k*0.1,Math.cos(h.yaw)*0.3));}else ball.p.copy(handPos(h));}
 if(game.phase==='dead'&&game.wait<0&&!game.fetcher&&ball.state==='held'&&ball.holder===server()){newRally();}
 for(const p of players){if(p.air&&p.state==='block')p.st+=0;posePlayer(p,simTime);}
 // marks fade
 for(let i=0;i<MARKS;i++){const m=marks[i];if(m.life>0){m.life-=dt/14;markMesh.setMatrixAt(i,_m.compose(m.p,new THREE.Quaternion(),new THREE.Vector3(m.s*Math.max(0,m.life),1,m.s*Math.max(0,m.life))));}}markMesh.instanceMatrix.needsUpdate=true;
 for(let i=puffs.length-1;i>=0;i--){const q=puffs[i];q.life-=dt;q.v.y-=G*0.4*dt;q.m.position.addScaledVector(q.v,dt);q.m.scale.setScalar(Math.max(0.01,q.life/0.7));if(q.life<=0){world.remove(q.m);reflHide.splice(reflHide.indexOf(q.m),1);puffs.splice(i,1);}}
}

// ───────── visual (non-random) animation per frame ─────────
function animate(t){updateSea(t);ballMesh.position.copy(ball.p);ballMesh.rotation.x+=ball.v.length()*0.01;
 for(const p of props.palms){p.kick=(p.kick||0)*0.985;const sw=(WIND.speed*0.02+p.kick)*Math.sin(t*1.7+p.ph)+WIND.speed*0.012;p.crown.rotation.z=sw*0.6;p.crown.rotation.x=sw*0.4;p.fronds.forEach((f,i)=>{f.rotation.z=-0.05-WIND.speed*0.015-0.08*Math.sin(t*3+i+p.ph)*(0.3+WIND.speed/6);});}
 for(const g of props.grass||[])g.rotation.z=Math.sin(t*2.4+g.userData.grass)*0.05*(1+WIND.speed/3)+WIND.speed*0.02;
 for(const f of props.flags){f.rotation.y=-WIND.dir+Math.PI/2+Math.sin(t*6)*0.05*WIND.speed;f.scale.x=0.4+Math.min(1,WIND.speed/6)*0.6;}
 if(props.net)props.net.position.x=Math.sin(t*2)*0.01*WIND.speed;
 for(const b of props.buoys)b.position.y=seaHeight(b.position.x,b.position.z,t)+0.1;
 for(const g of props.gulls){const x=g.cx+Math.cos(g.a)*g.r,z=g.cz+Math.sin(g.a)*g.r;g.g.position.set(x,g.h+(g.flap?Math.sin(t*3)*0.2:0),z);g.g.rotation.y=-g.a;const f=g.flap?Math.sin(t*14)*0.6:0.08;g.wl.rotation.z=f;g.wr.rotation.z=-f;g.sh.position.set(x,groundAt(x,z)+0.02,z);}
 const fl=0.8+0.2*Math.sin(t*13)*Math.sin(t*7.3);if(props.fire)props.fire.forEach((m,i)=>m.scale.y=(0.4+0.2*i)*fl*(night?1.3:0.8));
 poseBeachgoers(t);callMarker.position.y=game.call?sandH(game.call.x,game.call.z)+0.05:0;}

// ───────── time of day ─────────
let tod=0,night=false;const SKY=[[0x4c94dc,0xd4ecff],[0x643070,0xffae84],[0x080c1c,0x1e4482]];
function applyTime(){night=tod===2;const sets=[[0xfff2d8,1.7,0xcfe8ff,0.95,[-20,30,10]],[0xffa070,1.1,0xb090c0,0.7,[-30,8,6]],[0x8fa8e0,0.35,0x22305a,0.45,[15,25,-10]]][tod];
 sun.color.set(sets[0]);sun.intensity=sets[1];hemi.color.set(sets[2]);hemi.intensity=sets[3];sun.position.set(...sets[4]);flood.forEach(l=>l.intensity=night?60:0);
 for(const b of props.stringBulbs)b.material.emissive.set(tod>0?0xffd868:0x000000);for(const l of props.lights)l.material.emissive.set(night?0xfff6c0:0x000000);
 props.hatch.material.emissive.set(tod>0?0xffd868:0x000000);seaMat.uniforms.glint.value=tod===2?0.6:1;
 post.uniforms.skyTop.value.set(SKY[tod][0]);post.uniforms.skyBot.value.set(SKY[tod][1]);}

// ───────── post: whole-pixel upscale, depth outlines, OKLab palette (L x1.35), dithered sky ─────────
const palL=PALETTE_OKLAB.map(c=>new THREE.Vector3(...c)),palR=PALETTE.map(c=>new THREE.Vector3(c[0]/255,c[1]/255,c[2]/255));
const post=new THREE.RawShaderMaterial({glslVersion:THREE.GLSL3,uniforms:{tCol:{value:null},tDep:{value:null},art:{value:new THREE.Vector2(480,300)},pix:{value:3},palL:{value:palL},palR:{value:palR},lw:{value:L_WEIGHT},near:{value:-200},far:{value:200},raw:{value:0},skyTop:{value:new THREE.Color()},skyBot:{value:new THREE.Color()},off:{value:new THREE.Vector2()}},
 vertexShader:`in vec3 position;void main(){gl_Position=vec4(position.xy,0.,1.);}`,
 fragmentShader:`precision highp float;uniform sampler2D tCol;uniform sampler2D tDep;uniform vec2 art;uniform float pix;uniform vec3 palL[${PALETTE.length}];uniform vec3 palR[${PALETTE.length}];uniform float lw;uniform float near;uniform float far;uniform float raw;uniform vec3 skyTop;uniform vec3 skyBot;uniform vec2 off;out vec4 o;
 vec3 toLab(vec3 c){float l=0.4122214708*c.r+0.5363325363*c.g+0.0514459929*c.b,m=0.2119034982*c.r+0.6806995451*c.g+0.1073969566*c.b,s=0.0883024619*c.r+0.2817188376*c.g+0.6299787005*c.b;l=pow(max(l,0.),1./3.);m=pow(max(m,0.),1./3.);s=pow(max(s,0.),1./3.);
  return vec3(0.2104542553*l+0.7936177850*m-0.0040720468*s,1.9779984951*l-2.4285922050*m+0.4505937099*s,0.0259040371*l+0.7827717662*m-0.8086757660*s);}
 float lin(ivec2 p){p=clamp(p,ivec2(0),ivec2(art)-1);float d=texelFetch(tDep,p,0).r;return near+d*(far-near);}
 float bayer(ivec2 p){int x=p.x&3,y=p.y&3;int m[16]=int[16](0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5);return (float(m[y*4+x])+0.5)/16.;}
 vec3 toLin(vec3 c){return pow(c,vec3(2.2));}
 void main(){ivec2 p=ivec2(floor((gl_FragCoord.xy-off)/pix));p=clamp(p,ivec2(0),ivec2(art)-1);vec3 c=texelFetch(tCol,p,0).rgb;float d=texelFetch(tDep,p,0).r;
  bool sky=d>=0.99999;if(sky){float t=float(p.y)/art.y;float q=floor(t*7.+bayer(p))/7.;c=toLin(mix(skyBot,skyTop,q));}
  if(raw>0.5){o=vec4(pow(c,vec3(1./2.2)),1.);return;}
  if(!sky){float z=lin(p);float dmax=0.;dmax=max(dmax,lin(p+ivec2(1,0))-z);dmax=max(dmax,lin(p-ivec2(1,0))-z);dmax=max(dmax,lin(p+ivec2(0,1))-z);dmax=max(dmax,lin(p-ivec2(0,1))-z);if(dmax>0.5)c*=0.45;}
  vec3 L=toLab(c);float best=1e9;vec3 outc=vec3(0);for(int i=0;i<${PALETTE.length};i++){vec3 e=L-palL[i];e.x*=lw;float dd=dot(e,e);if(dd<best){best=dd;outc=palR[i];}}
  o=vec4(outc,1.);}`});
const postScene=new THREE.Scene();postScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),post));const postCam=new THREE.Camera();

// ───────── camera: isometric ortho, 90° steps, zoom 0.7–2.8, fit island + palms, pixel-snapped ─────────
const view={az:Math.PI/4,azT:Math.PI/4,zoom:innerWidth<760?1.25:1,el:31*Math.PI/180};
function fitAndSnap(){const dir=new THREE.Vector3(Math.cos(view.el)*Math.sin(view.az),Math.sin(view.el),Math.cos(view.el)*Math.cos(view.az));const target=new THREE.Vector3(0,0.5,0);
 camera.position.copy(target).addScaledVector(dir,60);camera.up.set(0,1,0);camera.lookAt(target);camera.updateMatrixWorld();
 const right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0),up=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,1);
 let mx=0,my=0,cx0=1e9,cx1=-1e9,cy0=1e9,cy1=-1e9;const pts=[];for(let i=0;i<32;i++){const a=i/32*Math.PI*2;const c=Math.cos(a),s=Math.sin(a);const x=ISX*Math.sign(c)*Math.pow(Math.abs(c),0.5),z=ISZ*Math.sign(s)*Math.pow(Math.abs(s),0.5);pts.push(new THREE.Vector3(x,1,z),new THREE.Vector3(x,-5,z));}
 for(const p of props.palms)pts.push(p.g.position.clone().add(new THREE.Vector3(0,8,0)));
 for(const q of pts){const v=q.clone().sub(target);const x=v.dot(right),y=v.dot(up);cx0=Math.min(cx0,x);cx1=Math.max(cx1,x);cy0=Math.min(cy0,y);cy1=Math.max(cy1,y);}
 const aspect=ART_W/ART_H;let w=(cx1-cx0)*1.04,h=(cy1-cy0)*1.04;if(w/h>aspect)h=w/aspect;else w=h*aspect;w/=view.zoom;h/=view.zoom;
 const ccx=(cx0+cx1)/2,ccy=(cy0+cy1)/2;const pw=w/ART_W;
 // snap: world origin onto a whole art pixel
 const ox=-ccx,oy=-ccy;const sx=Math.round(ox/pw)*pw-ox,sy=Math.round(oy/pw)*pw-oy;
 camera.left=ccx-w/2-sx;camera.right=ccx+w/2-sx;camera.top=ccy+h/2-sy;camera.bottom=ccy-h/2-sy;camera.updateProjectionMatrix();}

function resize(){const r=stage.getBoundingClientRect();const W=Math.max(1,Math.floor(r.width)),H=Math.max(1,Math.floor(r.height));PIX=W>900?3:2;ART_W=Math.max(120,Math.min(480,Math.floor(W/PIX)));ART_H=Math.max(90,Math.min(300,Math.floor(H/PIX)));
 const cw=ART_W*PIX,ch=ART_H*PIX;renderer.setSize(W,H,false);canvas.width=W;canvas.height=H;rtMain.dispose();rtRefl.dispose();rtMain=mkRT();rtRefl=mkRT();
 post.uniforms.art.value.set(ART_W,ART_H);post.uniforms.pix.value=PIX;post.uniforms.off.value.set(Math.floor((W-cw)/2),Math.floor((H-ch)/2));seaMat.uniforms.res.value.set(ART_W,ART_H);}
new ResizeObserver(resize).observe(stage);

function render(){fitAndSnap();
 // mirrored reflection pass (scene.scale.y = -1 about the water plane), hide sand, water, particles
 const hidden=reflHide.map(m=>m.visible);reflHide.forEach(m=>m.visible=false);ballMesh.visible=true;world.scale.y=-1;scene.background=null;
 renderer.setRenderTarget(rtRefl);renderer.setClearColor(0x000000,0);renderer.clear();renderer.render(scene,camera);world.scale.y=1;reflHide.forEach((m,i)=>m.visible=hidden[i]);
 seaMat.uniforms.refl.value=rtRefl.texture;seaMat.uniforms.sunDir.value.copy(sun.position).normalize();seaMat.uniforms.sunCol.value.copy(sun.color).multiplyScalar(sun.intensity/1.6);seaMat.uniforms.amb.value.copy(hemi.color).multiplyScalar(hemi.intensity);
 renderer.setRenderTarget(rtMain);renderer.setClearColor(0x000000,1);renderer.clear();renderer.render(scene,camera);
 renderer.setRenderTarget(null);post.uniforms.tCol.value=rtMain.texture;post.uniforms.tDep.value=rtMain.depthTexture;post.uniforms.near.value=camera.near;post.uniforms.far.value=camera.far;renderer.render(postScene,postCam);}

// ───────── scoreboard: lit pixel font ─────────
const sb=$('score'),sg=sb.getContext('2d');
function drawText(x,y,s,col,sc){s=s.toUpperCase();for(const ch of s){const g=FONT.glyphs[ch];if(g){for(let r=0;r<7;r++)for(let c=0;c<5;c++)if(g[r][c]==='1'){sg.fillStyle=col;sg.fillRect(x+c*sc,y+r*sc,sc,sc);}}x+=6*sc;}return x;}
const tw=(s,sc)=>s.length*6*sc;
function drawScore(){const sc=window.innerWidth<500?1:2;const st=(game.status||'').toUpperCase().replace(/[^A-Z0-9\-:\/. ]/g,'');const l1=`CORAL ${String(game.score[0]).padStart(2,'0')} - ${String(game.score[1]).padStart(2,'0')} TEAL`;const l2=`SET ${Math.min(game.set,3)}  SETS ${game.sets[0]}-${game.sets[1]}`;
 const W=Math.max(tw(l1,sc),tw(st,sc),tw(l2,sc))+16*sc,H=(7*3+18)*sc+6*sc;if(sb.width!==W||sb.height!==H){sb.width=W;sb.height=H;}
 sb.style.width=W*1.0+'px';sg.fillStyle='#0b1122';sg.fillRect(0,0,W,H);sg.strokeStyle='#2e6cb8';sg.lineWidth=sc;sg.strokeRect(sc/2,sc/2,W-sc,H-sc);
 sg.shadowColor='#ffd868';sg.shadowBlur=4*sc;let x=(W-tw(l1,sc))/2;x=drawText(x,4*sc,'CORAL ',PALETTE[31]&&'#ff8a6c',sc);x=drawText(x,4*sc,`${String(game.score[0]).padStart(2,'0')} - ${String(game.score[1]).padStart(2,'0')} `,'#ffe04a',sc);drawText(x,4*sc,'TEAL','#52d8d0',sc);
 sg.shadowBlur=2*sc;drawText((W-tw(l2,sc))/2,14*sc,l2,'#d6e2e8',sc);drawText((W-tw(st,sc))/2,24*sc,st,'#fff6c0',sc);sg.shadowBlur=0;
 // serve dots
 const s=game.server;sg.fillStyle=s.team===0?'#ff8a6c':'#52d8d0';const dx=s.team===0?6*sc:W-9*sc;sg.fillRect(dx,5*sc,3*sc,3*sc);if(s.idx)sg.fillRect(dx,10*sc,3*sc,3*sc);}

// ───────── UI wiring ─────────
const ui=T('ui',{});const seg=(id,labels,get,set)=>{const el=$(id);el.innerHTML='';labels.forEach((l,i)=>{const b=document.createElement('button');b.textContent=l;b.onclick=()=>{set(i);refresh();};el.appendChild(b);});const refresh=()=>[...el.children].forEach((b,i)=>b.setAttribute('aria-pressed',String(get()===i)));refresh();};
seg('time',ui.time||['Day','Sunset','Night'],()=>tod,i=>{tod=i;applyTime();});
seg('wind',ui.wind||['Calm','Breeze','Gusty'],()=>WIND.mode,i=>{WIND.mode=i;});
seg('attack',ui.attack||['Auto','Spike','Shots'],()=>game.attackStyle,i=>{game.attackStyle=i;});
$('newm').textContent=ui.new_match||'New match';$('pause').textContent=ui.pause||'Pause';$('raw').textContent=ui.raw||'Raw 3D';$('viewl').textContent=ui.view||'View';
$('newm').onclick=()=>reseed(SEED);$('pause').onclick=e=>{paused=!paused;e.target.setAttribute('aria-pressed',paused);};
$('raw').onclick=e=>{post.uniforms.raw.value=1-post.uniforms.raw.value;e.target.setAttribute('aria-pressed',String(!!post.uniforms.raw.value));};
$('theme').onclick=()=>document.body.classList.toggle('light');
$('rotl').onclick=()=>view.azT-=Math.PI/2;$('rotr').onclick=()=>view.azT+=Math.PI/2;$('zin').onclick=()=>view.zoom=Math.min(2.8,view.zoom*1.2);$('zout').onclick=()=>view.zoom=Math.max(0.7,view.zoom/1.2);
$('hint').textContent=ui.call_shot||'Tap the sand to call the next attack';
$('howl').innerHTML=(T('how_its_drawn',[])).map(s=>`<li>${s.replace(/</g,'&lt;')}</li>`).join('');
const sp=T('synapse_panel',{});$('seedlabel').textContent=LABEL;$('f_inj').textContent=sp.fields?.injection||'Injection';$('f_job').textContent=sp.fields?.job||'Job ID';$('f_rounds').textContent=sp.fields?.rounds||'Rounds';$('f_win').textContent=sp.fields?.win_rate||'Win rate';$('f_stream').textContent=sp.fields?.stream||'Stream used';$('switchl').textContent=sp.switcher||'Reseed from';
const injEl=$('inj');
function drawSwitcher(){injEl.innerHTML='';for(const s of loaded){const b=document.createElement('button');b.className='inj';b.disabled=!s.ok;b.setAttribute('aria-pressed',String(SEED===s));
 b.innerHTML=s.ok?`${s.name}<small>${s.job_id} · ${s.rounds.toLocaleString('en-US')} rounds · ${(s.win_rate*100).toFixed(2)}%${s.win_rate<0.75?' · '+(sp.failed_run_note||'No violation; still a seed.'):''}</small>`:`${s.file}<small>${s.job} · ${sp.unavailable||'Outcomes not found.'}</small>`;
 b.onclick=()=>reseed(s);injEl.appendChild(b);}}
// drag to rotate in 90° steps, wheel / pinch zoom, tap the sand to call the attack
const ptrs=new Map();let drag=null,pinch0=0;
stage.addEventListener('pointerdown',e=>{stage.setPointerCapture(e.pointerId);ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});if(ptrs.size===1)drag={x:e.clientX,y:e.clientY,moved:false};if(ptrs.size===2){const [a,b]=[...ptrs.values()];pinch0=Math.hypot(a.x-b.x,a.y-b.y)/view.zoom;}});
stage.addEventListener('pointermove',e=>{if(!ptrs.has(e.pointerId))return;ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY});if(ptrs.size===2){const [a,b]=[...ptrs.values()];view.zoom=THREE.MathUtils.clamp(Math.hypot(a.x-b.x,a.y-b.y)/pinch0,0.7,2.8);drag=null;return;}
 if(drag){const dx=e.clientX-drag.x;if(Math.abs(dx)>8)drag.moved=true;if(Math.abs(dx)>70){view.azT+=dx>0?-Math.PI/2:Math.PI/2;drag.x=e.clientX;}}});
stage.addEventListener('pointerup',e=>{ptrs.delete(e.pointerId);if(drag&&!drag.moved)callShot(e);drag=null;});
stage.addEventListener('wheel',e=>{e.preventDefault();view.zoom=THREE.MathUtils.clamp(view.zoom*(e.deltaY<0?1.1:1/1.1),0.7,2.8);},{passive:false});
const ray=new THREE.Raycaster();
function callShot(e){const r=canvas.getBoundingClientRect();const off=post.uniforms.off.value;const px=(e.clientX-r.left-off.x)/(ART_W*PIX),py=(r.height-(e.clientY-r.top)-off.y)/(ART_H*PIX);
 ray.setFromCamera(new THREE.Vector2(px*2-1,py*2-1),camera);const hit=ray.intersectObject(sandMesh)[0];if(!hit)return;const p=hit.point;if(!inCourt(p,0.5))return;game.call=new THREE.Vector3(p.x,0.6,p.z);callMarker.position.set(p.x,0.62,p.z);callMarker.visible=true;signal('shot called',p.x.toFixed(1));}

// ───────── boot / reseed: same injection + same stream position = same world ─────────
function clearWorld(){for(let i=world.children.length-1;i>=0;i--){const c=world.children[i];if(c!==ballMesh&&c!==callMarker&&c!==markMesh)world.remove(c);}reflHide.length=0;reflHide.push(markMesh);players.length=0;props.palms=[];props.flags=[];props.lights=[];props.buoys=[];props.stringBulbs=[];props.grass=[];puffs.length=0;timers.length=0;marks.forEach(m=>m.life=0);sandMesh=null;}
function reseed(s){if(!s||!s.ok)return;SEED=s;s.stream.reset();clearWorld();simTime=0;WIND.next=3;WIND.gustAmp=0;sigLog.length=0;game.call=null;callMarker.visible=false;
 buildTerrain();buildProps();buildPeople();applyTime();newMatch();drawSwitcher();signal('reseed',s.name);
 $('v_inj').textContent=s.name;$('v_job').textContent=s.job_id+' · '+s.backend;$('v_rounds').textContent=s.rounds.toLocaleString('en-US');$('v_win').textContent=(s.win_rate*100).toFixed(2)+'%';$('v_sha').textContent=s.outcomes_sha256;}
const first=loaded.find(s=>s.ok);
if(!first){$('err').textContent=sp.unavailable||'Outcomes not found.';drawSwitcher();}
else{resize();reseed(first);let last=performance.now(),acc=0;const DT=1/120;
 function frame(now){requestAnimationFrame(frame);let d=Math.min(0.1,(now-last)/1000);last=now;if(!paused){acc+=d;while(acc>=DT){sim(DT);acc-=DT;}}
  view.az+=(view.azT-view.az)*Math.min(1,d*7);animate(simTime);render();drawScore();
  $('v_stream').textContent=SEED.stream.drawn.toLocaleString('en-US')+' draws · block '+SEED.stream.counter;$('wms').textContent=`· ${WIND.speed.toFixed(1)} m/s`;$('signals').textContent=sigLog.join('\n');}
 requestAnimationFrame(frame);}
window.__beachTwo={game,ball,get seed(){return SEED&&{name:SEED.name,drawn:SEED.stream.drawn}},loaded:()=>loaded.map(s=>({file:s.file||s.name,ok:s.ok}))};
