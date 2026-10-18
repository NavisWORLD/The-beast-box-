// Universe of worlds (three side): home trees + clouds + sky dome + parallax haze, distant worlds with
// atmospheres, moons and gravity wells, and gravity-tunneling trips. Everything instanced and count-capped.
import {LIMITS,WORLDS,cstTree,treeTips,worldAnchor,moonPeriod,tunnelPath,travelPose} from './worlds-math.mjs';
import {seededRng} from '../physics/cst-integrator.mjs';
import {groundRay,planetWalk} from './grounding.mjs';
import {buildPlasmaPlanet,sectorSprite,sectorLabel,flashEnv} from './plasma';
import {neonPatch,neonUniforms,type NeonU} from './neon-wire';
type T=typeof import('three');type V3={x:number;y:number;z:number};

const SWAY_VS=`
 vec4 wpS=modelMatrix*instanceMatrix*vec4(transformed,1.);float hS=max(0.,wpS.y+.05);
 vec2 swS=uFlow*hS*hS*.012*(sin(uTime*.9+wpS.x*.21+wpS.z*.17)+.45*sin(uTime*1.7+wpS.z*.4));
 wpS.xz+=swS;vec4 mvPosition=viewMatrix*wpS;gl_Position=projectionMatrix*mvPosition;
 vec3 nS=normalize(mat3(viewMatrix)*mat3(modelMatrix)*mat3(instanceMatrix)*objectNormal);vRimS=1.-abs(dot(nS,normalize(-mvPosition.xyz)));
 vHS=wpS.y;vNearS=smoothstep(NEAR_A,NEAR_B,-mvPosition.z);`;
/** Near-lens rules for foliage: fully faded inside NEAR_A, full from NEAR_B (world units in view depth). */
export const CANOPY_NEAR=Object.freeze({a:2.5,b:7});
function swayMat(THREE:T,U:any,opts:any,{rim=0,shade=0,fade=false,key='bark'}:{rim?:number;shade?:number;fade?:boolean;key?:string}={}){const m=new THREE.MeshStandardMaterial(opts);
  m.onBeforeCompile=(sh:any)=>{sh.uniforms.uTime=U.uTime;sh.uniforms.uFlow=U.uFlow;
   const vs=SWAY_VS.replace('NEAR_A',CANOPY_NEAR.a.toFixed(2)).replace('NEAR_B',CANOPY_NEAR.b.toFixed(2));
   sh.vertexShader='uniform float uTime;uniform vec2 uFlow;varying float vRimS,vHS,vNearS;\n'+sh.vertexShader.replace('#include <project_vertex>',vs);
   sh.fragmentShader='varying float vRimS,vHS,vNearS;\n'+sh.fragmentShader.replace('#include <dithering_fragment>',
    `#include <dithering_fragment>
     gl_FragColor.rgb*=mix(1.,mix(.45,1.18,clamp(vHS/7.,0.,1.)),${shade.toFixed(2)});// depth shading: darker low/inner, lit crown
     gl_FragColor.rgb+=vec3(.55,.75,1.)*pow(vRimS,2.4)*${rim.toFixed(2)};// cool rim light from the cage glow
     ${fade?'gl_FragColor.a*=vNearS;if(gl_FragColor.a<.02)discard;':''}`);};
  m.customProgramCacheKey=()=>'bbsway-'+key;return m;}

export function buildWorlds(THREE:T,scene:import('three').Scene,{low,universe=30,neon=neonUniforms()}:{low:boolean;universe?:number;neon?:NeonU}){
  const U={uTime:{value:0},uFlow:{value:new THREE.Vector2(.8,.35)}};const rnd=seededRng('worlds');
  const root=new THREE.Group();root.name='universe-of-worlds';scene.add(root);
  const m4=new THREE.Matrix4(),q=new THREE.Quaternion(),up=new THREE.Vector3(0,1,0),va=new THREE.Vector3(),vb=new THREE.Vector3(),vs=new THREE.Vector3();
  // ---- sky dome + horizon haze (palette: cage purples into deep space)
  const sky=new THREE.Mesh(new THREE.SphereGeometry(1800,low?24:40,low?12:20),new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,fog:false,
   uniforms:{uTime:U.uTime},vertexShader:'varying vec3 vD;void main(){vD=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
   fragmentShader:`varying vec3 vD;uniform float uTime;void main(){float y=vD.y;
    vec3 zen=vec3(.02,.016,.06),mid=vec3(.09,.05,.2),hor=vec3(.27,.16,.45);
    vec3 c=mix(hor,mid,smoothstep(-.02,.22,y));c=mix(c,zen,smoothstep(.2,.85,y));
    c+=vec3(.35,.2,.55)*exp(-abs(y)*14.)*.5;
    float band=sin(vD.x*3.+vD.z*2.+uTime*.02)*.5+.5;c+=vec3(.05,.12,.18)*band*smoothstep(.05,.4,y)*(1.-smoothstep(.4,.8,y))*.6;
    gl_FragColor=vec4(c,1.);}`}));
  sky.renderOrder=-10;sky.frustumCulled=false;root.add(sky);
  // ---- parallax depth layers: three silhouette rings with soft haze (move at different apparent rates)
  const layers:import('three').Mesh[]=[];
  [[universe*2.1,6,.2,0x3a2a6a],[universe*3.8,13,.15,0x30225e],[universe*6.5,24,.11,0x281c52]].forEach(([R,H,a,col],i)=>{
   const g=new THREE.CylinderGeometry(R,R,H,low?64:128,1,true);g.translate(0,H/2-.2,0);
   const mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,side:THREE.DoubleSide,fog:false,uniforms:{uC:{value:new THREE.Color(col)},uA:{value:a},uS:{value:i*7.1}},
    vertexShader:'varying vec2 vU;void main(){vU=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:`varying vec2 vU;uniform vec3 uC;uniform float uA,uS;
     float n(float x){return sin(x)*.5+sin(x*2.3+uS)*.3+sin(x*5.1+uS*2.)*.15;}
     void main(){float x=vU.x*6.2831*6.;float ridge=.45+.35*n(x+uS);float m=1.-smoothstep(ridge-.28,ridge+.06,vU.y);
      float haze=pow(1.-vU.y,2.)*.5;gl_FragColor=vec4(uC*(1.+vU.y*.6),clamp(m*uA+haze*uA,0.,1.));}`});
   const ring=new THREE.Mesh(g,mat);ring.renderOrder=-9+i*0;ring.frustumCulled=false;root.add(ring);layers.push(ring);});
  // ---- home trees: one instanced mesh for all branches, one for canopy puffs (CST branching, flow sway)
  const nT=low?LIMITS.homeTreesLow:LIMITS.homeTreesHigh,depth=low?LIMITS.treeDepthLow:LIMITS.treeDepthHigh;
  const trees:{x:number;z:number;s:number;segs:any[]}[]=[];
  for(let i=0;i<nT;i++){const a=i*2.39996+rnd()*.4,r=7+rnd()*(universe*.4);trees.push({x:Math.cos(a)*r,z:Math.sin(a)*r,s:5.5+rnd()*3,segs:cstTree('home'+i,{depth,scale:1})});}
  const segTotal=Math.min(LIMITS.maxSegments,trees.reduce((n,t)=>n+t.segs.length,0));
  const tips=trees.map(t=>treeTips(t.segs));const CLUMP=low?2:3;const tipTotal=tips.reduce((n,t)=>n+t.length,0)*CLUMP;
  const branchGeo=new THREE.CylinderGeometry(.7,1,1,low?5:7,1,true);branchGeo.translate(0,.5,0);
  const bark=swayMat(THREE,U,{color:0x6a4a9a,emissive:0x3a2068,emissiveIntensity:.7,roughness:.85,flatShading:true},{rim:.35,shade:.6,key:'bark'});
  const branches=new THREE.InstancedMesh(branchGeo,bark,segTotal);branches.name='cst-trees';
  neonPatch(bark,neon,{mode:'rim',amt:.45});// branch outlines
  const leafGeo=new THREE.IcosahedronGeometry(1,low?0:1);
  const leaf=swayMat(THREE,U,{color:0x6b4fc0,emissive:0x6a3fe0,emissiveIntensity:.5,roughness:.6,flatShading:true,transparent:true,opacity:1},{rim:.55,shade:1,fade:true,key:'leaf'});
  const canopy=new THREE.InstancedMesh(leafGeo,leaf,tipTotal);canopy.name='cst-canopy';
  const tc=new THREE.Color();let si=0,li=0;
  trees.forEach((t,ti)=>{for(const s of t.segs){if(si>=segTotal)break;va.set(t.x+s.a[0]*t.s,-.06+s.a[1]*t.s,t.z+s.a[2]*t.s);vb.set(t.x+s.b[0]*t.s,-.06+s.b[1]*t.s,t.z+s.b[2]*t.s);
    const L=va.distanceTo(vb);q.setFromUnitVectors(up,vb.clone().sub(va).normalize());const th=s.r*t.s*(s.d===1?1.7:1.25);vs.set(th,L,th);m4.compose(va,q,vs);branches.setMatrixAt(si++,m4);}
   const hue=ti%3===0?.47:ti%3===1?.74:.8;
   for(const p of tips[ti])for(let c=0;c<CLUMP;c++){// layered clumps: inner dark big, outer lighter smaller, lifted
    const o=c*.6;va.set(t.x+(p[0]+(rnd()-.5)*.12*o)*t.s,-.06+(p[1]+.04*c)*t.s,t.z+(p[2]+(rnd()-.5)*.12*o)*t.s);q.setFromEuler(new THREE.Euler(rnd()*3,rnd()*3,0));
    vs.set(1,.8,1).multiplyScalar(t.s*(.15-.03*c)*(.85+rnd()*.3));m4.compose(va,q,vs);canopy.setMatrixAt(li,m4);
    tc.setHSL(hue+(rnd()-.5)*.05,.6+.1*c,.42+.12*c+rnd()*.06);canopy.setColorAt(li++,tc);}});
  const walkBranches=trees.flatMap(t=>t.segs.filter((s:any)=>s.d===2||s.d===3).map((s:any)=>({a:{x:t.x+s.a[0]*t.s,y:-.06+s.a[1]*t.s,z:t.z+s.a[2]*t.s},b:{x:t.x+s.b[0]*t.s,y:-.06+s.b[1]*t.s,z:t.z+s.b[2]*t.s},r:s.r*t.s*1.25})));
  const treeBodies=trees.flatMap(t=>[{x:t.x,y:t.s*.35,z:t.z,r:t.s*.12+.5},{x:t.x,y:t.s*.85,z:t.z,r:t.s*.42}]);// trunk + crown push the lens out
  branches.instanceMatrix.needsUpdate=true;canopy.instanceMatrix.needsUpdate=true;root.add(branches,canopy);
  // ---- soft clouds: billboarded instanced quads, radial soft alpha with drift
  const nC=low?LIMITS.cloudsLow:LIMITS.cloudsHigh,nP=nC*LIMITS.puffs;
  const cloudMat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,fog:false,uniforms:{uTime:U.uTime},
   vertexShader:`attribute vec4 aP;varying vec2 vU;varying float vA;uniform float uTime;void main(){vU=uv-.5;
    vec3 c=aP.xyz;c.x=mod(c.x+uTime*.35+200.,400.)-200.;vec4 mv=viewMatrix*vec4(c,1.);
    float d=-mv.z;vA=smoothstep(2.,10.,d)*(1.-smoothstep(150.,260.,d));mv.xy+=position.xy*aP.w;gl_Position=projectionMatrix*mv;}`,
   fragmentShader:`varying vec2 vU;varying float vA;void main(){float r=length(vU)*2.;float a=(1.-smoothstep(.2,1.,r))*.32*vA;
    vec3 c=mix(vec3(.62,.5,.9),vec3(.32,.24,.6),r);gl_FragColor=vec4(c,a);}`});
  const cg=new THREE.InstancedBufferGeometry();const pg=new THREE.PlaneGeometry(1,1);cg.index=pg.index;cg.attributes.position=pg.attributes.position;cg.attributes.uv=pg.attributes.uv;
  const aP=new Float32Array(nP*4);for(let c=0;c<nC;c++){const a=rnd()*6.283,r=14+rnd()*90,cx=Math.cos(a)*r,cz=Math.sin(a)*r,cy=10+rnd()*14,sz=5+rnd()*7;
   for(let p=0;p<LIMITS.puffs;p++){const k=(c*LIMITS.puffs+p)*4;aP[k]=cx+(rnd()-.5)*sz*1.4;aP[k+1]=cy+(rnd()-.5)*sz*.3;aP[k+2]=cz+(rnd()-.5)*sz*.6;aP[k+3]=sz*(.6+rnd()*.6);}}
  cg.setAttribute('aP',new THREE.InstancedBufferAttribute(aP,4));cg.instanceCount=nP;
  const clouds=new THREE.Mesh(cg,cloudMat);clouds.frustumCulled=false;clouds.renderOrder=2;clouds.name='soft-clouds';root.add(clouds);
  // ---- distant worlds: LOD body + atmosphere shell + optional moon; islands carry mini CST trees
  const atmoMat=(col:number)=>new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,side:THREE.BackSide,fog:false,uniforms:{uC:{value:new THREE.Color(col)}},
   vertexShader:'varying vec3 vN,vV;void main(){vN=normalize(normalMatrix*normal);vec4 mv=modelViewMatrix*vec4(position,1.);vV=normalize(-mv.xyz);gl_Position=projectionMatrix*mv;}',
   fragmentShader:'varying vec3 vN,vV;uniform vec3 uC;void main(){float f=pow(1.-abs(dot(vN,vV)),2.2);gl_FragColor=vec4(uC*f*1.4,f);}'});
  const worlds=WORLDS.map((w,wi)=>{const g=new THREE.Group();g.name='world-'+w.id;const lod=new THREE.LOD();
   const mk=(det:number)=>{if(w.kind==='planet')return new THREE.Mesh(new THREE.IcosahedronGeometry(w.radius,det),new THREE.MeshStandardMaterial({color:w.color,emissive:w.color,emissiveIntensity:.45,roughness:.75,flatShading:true,fog:false}));
     const isl=new THREE.Group();const rock=new THREE.Mesh(new THREE.ConeGeometry(w.radius,w.radius*1.8,det?14:7,det?3:1),new THREE.MeshStandardMaterial({color:0x241840,emissive:w.color,emissiveIntensity:.25,flatShading:true,fog:false}));
     rock.rotation.x=Math.PI;rock.position.y=-w.radius*.9;const top=new THREE.Mesh(new THREE.CylinderGeometry(w.radius,w.radius*.96,.3,det?28:12),new THREE.MeshStandardMaterial({color:w.color,emissive:w.color,emissiveIntensity:.5,flatShading:true,fog:false}));
     isl.add(rock,top);if(det){const gr=new THREE.GridHelper(w.radius*1.8,8,0x4983a4,0x284c74);gr.position.y=.17;(gr.material as any).fog=false;isl.add(gr);}return isl;};
   const lvls=[mk(low?2:3),mk(low?1:2),mk(0)];lvls.forEach(l=>l.traverse((m:any)=>{if(m.isMesh&&m.material?.isMeshStandardMaterial)neonPatch(m.material,neon,{mode:'lat',freq:w.kind==='planet'?7:3,amt:.5});if(m.isLineSegments)(m.material as any).color?.setHex?.(0x9ff4ff);}));
   if(w.kind!=='planet'){lod.addLevel(lvls[0],0);lod.addLevel(lvls[1],60);lod.addLevel(lvls[2],130);}/*lod.addLevel(mk(low?1:2),60);*/g.add(lod);
   const atmo=new THREE.Mesh(new THREE.SphereGeometry(w.radius*(w.kind==='planet'?1.32:1.5),low?20:32,low?12:20),atmoMat(w.atmo));g.add(atmo);
   const glow=new THREE.PointLight(w.atmo,low?0:6,w.radius*5);if(!low)g.add(glow);
   let moon:import('three').Mesh|null=null;if(w.moon){moon=new THREE.Mesh(new THREE.IcosahedronGeometry(w.radius*.22,1),new THREE.MeshStandardMaterial({color:0xd9ccff,emissive:w.atmo,emissiveIntensity:.35,flatShading:true,fog:false}));g.add(moon);}
   if(w.kind==='island'){const segs=cstTree('isle'+wi,{depth:low?3:4,scale:1});const im=new THREE.InstancedMesh(branchGeo,bark,segs.length*3);let k=0;
    for(let t=0;t<3;t++){const ox=(t-1)*w.radius*.45,oz=(t%2?.4:-.3)*w.radius,s=1.3+t*.3;for(const sg of segs){va.set(ox+sg.a[0]*s,.15+sg.a[1]*s,oz+sg.a[2]*s);vb.set(ox+sg.b[0]*s,.15+sg.b[1]*s,oz+sg.b[2]*s);
     q.setFromUnitVectors(up,vb.clone().sub(va).normalize());vs.set(sg.r*s,va.distanceTo(vb),sg.r*s);m4.compose(va,q,vs);im.setMatrixAt(k++,m4);}}
    im.instanceMatrix.needsUpdate=true;g.add(im);}
   const plasma=w.kind==='planet'?buildPlasmaPlanet(THREE,g,{radius:w.radius,color:w.color,atmo:w.atmo,low,seed:wi}):null;
   const label=sectorSprite(THREE,sectorLabel(wi,w.id));label.position.set(0,w.radius*2.3,0);g.add(label);
   root.add(g);return {w,g,moon,lod,plasma,label,labelT:-99,anchor:worldAnchor(w,0),mass:w.mass};});
  // ---- gravity-tunneling trail
  const TRAIL_N=64;const trailGeo=new THREE.BufferGeometry();trailGeo.setAttribute('position',new THREE.BufferAttribute(new Float32Array((TRAIL_N+1)*3),3));
  const trail=new THREE.Line(trailGeo,new THREE.LineBasicMaterial({color:0xc79cff,transparent:true,opacity:0,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));trail.frustumCulled=false;root.add(trail);
  let trip:any=null,tripT=0,next=40+rnd()*20,lastWorld=-1;
  const wellsNow=()=>worlds.map(o=>({...o.anchor,mass:o.mass}));
  function startTrip(i:number,from:V3){const o=worlds[i%worlds.length];const top={x:o.anchor.x,y:o.anchor.y+o.w.radius*(o.w.kind==='planet'?1:.12)+.25,z:o.anchor.z};
   const others=wellsNow().filter((_,j)=>j!==i%worlds.length);trip={i:i%worlds.length,out:tunnelPath({x:from.x,y:from.y,z:from.z},top,others,{n:TRAIL_N})};tripT=0;lastWorld=trip.i;trip.ph='go';worlds[trip.i].plasma?.tunnel(U.uTime.value);
   const a=trailGeo.attributes.position as any;trip.out.forEach((p:V3,k:number)=>a.setXYZ(k,p.x,p.y,p.z));a.needsUpdate=true;return trip;}
  return {root,worlds,U,
   bodies:()=>[...worlds.map(o=>({x:o.g.position.x,y:o.g.position.y,z:o.g.position.z,r:o.w.radius*1.1+.6})),...treeBodies],
   startTrip,get trip(){return trip;},neon,
   /** tunneling flash level 0..1 (white flash + inversion window) */
   flash:()=>{let f=0;for(const o of worlds)if(o.plasma)f=Math.max(f,o.plasma.flash(U.uTime.value));return f;},
   /** core pulse of the nearest plasma world (companions feeding) */
   pulseNear(p:V3,a=.6){let best:any=null,bd=1e9;for(const o of worlds){if(!o.plasma)continue;const d=Math.hypot(o.g.position.x-p.x,o.g.position.y-p.y,o.g.position.z-p.z);if(d<bd){bd=d;best=o;}}if(best&&bd<best.w.radius*10)best.plasma.pulse(a);},
   /** downward ray against floor, island tops, planet spheres and walkable tree limbs */
   ground:(p:V3)=>groundRay(p,{worlds:worlds.map(o=>({x:o.g.position.x,y:o.g.position.y,z:o.g.position.z,r:o.w.radius,kind:o.w.kind,top:.15})),branches:walkBranches}),
   /** advance; returns travel pose for the traveller or null when home. */
   update(dt:number,t:number,cam:import('three').Camera,traveller:V3,canAuto:boolean){
    U.uTime.value=t;U.uFlow.value.set(.8+Math.sin(t*.13)*.25,.35+Math.cos(t*.09)*.2);
    sky.position.copy(cam.position);// dome at infinity
    layers.forEach((l,i)=>{l.position.set(cam.position.x*(.25+i*.25),0,cam.position.z*(.25+i*.25));});// parallax: farther layers trail the camera more
    for(const o of worlds){o.anchor=worldAnchor(o.w,t);o.g.position.set(o.anchor.x,o.anchor.y,o.anchor.z);o.g.rotation.y=t*.03*(o.w.kind==='planet'?1:.4);
     if(o.moon){const P=moonPeriod(o.w),a=t*2*Math.PI/P,R=o.w.radius*1.9;o.moon.position.set(Math.cos(a)*R,Math.sin(a*.5)*R*.25,Math.sin(a)*R);}o.lod.update(cam);
     if(o.plasma){const tp=traveller,dn=Math.hypot(tp.x-o.g.position.x,tp.y-o.g.position.y,tp.z-o.g.position.z);o.plasma.update(t,dt,{level:.3+.25*Math.sin(t*.7+o.w.mass),near:dn<o.w.radius*8?tp:null});}
     const lt=t-o.labelT;(o.label.material as any).opacity=lt<0||lt>6?0:Math.min(1,lt/.8)*Math.min(1,(6-lt)/1.2)*.75;}
    const tm=trail.material as any;
    if(!trip){next-=dt;tm.opacity=Math.max(0,tm.opacity-dt*.5);if(canAuto&&next<=0){next=55+rnd()*25;startTrip((lastWorld+1+Math.floor(rnd()*2))%worlds.length,traveller);}else return null;}
    tripT+=dt;const P=travelPose(trip,tripT);tm.opacity=Math.min(.55,tm.opacity+dt*.8)*(P.phase==='stay'?.9:1);
    const o=worlds[trip.i],k=trip.out.length-1,end=trip.out[k];// keep the far end glued to the moving world
    const dx=o.anchor.x-(end.__ax??o.anchor.x),dy=o.anchor.y-(end.__ay??o.anchor.y);end.__ax=o.anchor.x;end.__ay=o.anchor.y;if(dx||dy){end.x+=dx;end.y+=dy;}
    if(P.phase!==trip.ph){if(P.phase==='stay'){o.plasma?.tunnel(t);o.labelT=t;}if(P.phase==='back')o.plasma?.tunnel(t);trip.ph=P.phase;}
    if(P.done){trip=null;return null;}
    let pos=P.pos,n={x:0,y:1,z:0};
    if(P.phase==='stay'){if(o.w.kind==='planet'){const W=planetWalk(o.anchor,o.w.radius,Math.min(.95,(tripT-9)*.14),trip.h??(trip.h=rnd()*6.283));pos=W.pos;n=W.n;}
     else pos={x:o.anchor.x+Math.sin(tripT*.5)*o.w.radius*.4,y:o.anchor.y+.15,z:o.anchor.z+Math.cos(tripT*.4)*o.w.radius*.3};}
    return {phase:P.phase,pos,n,world:o.w.id,s:Math.min(1,tripT/9)};},
   dispose(){scene.remove(root);root.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});}};
}
