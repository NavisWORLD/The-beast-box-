// Dimensional sensors of life: hidden refracting sensor nodes across the universe, a nervous-system
// network per creature grown from the shared CST seed, and the words → light → vibration signal chain.
import {SENSOR_LIMITS,nerveTree,growthLevel,pulseAt,nearestNodes,loadXP,saveXP,entityRng} from './sensors-math.mjs';
type T=typeof import('three');type V3={x:number;y:number;z:number};
export const NERVE_PALETTES:Record<string,[number,number]>=Object.freeze({default:[0x9ff4ff,0xffffff],warm:[0xffb020,0xff3b1f],zeref:[0xc79cff,0x9ff4ff],
 'art-frostmitt':[0x9fe8ff,0xffffff],'art-shardhowl':[0xff8fd8,0x7fffe0],'art-velvetcoil':[0xd16bff,0xffb8f0],'art-nyxbean':[0x8f7bff,0xffffff],'art-kairo':[0xffc46b,0xfff1c9]}) as any;
export function createSensors(THREE:T,scene:import('three').Scene,{low,points}:{low:boolean;points:V3[]}){
  const xp:Record<string,number>=typeof window!=='undefined'?loadXP(window.localStorage):{};
  // ---- hidden universe nodes (billboards, invisible until stimulated; chromatic refraction ring + bloom core)
  const N=Math.min(points.length,low?SENSOR_LIMITS.nodesLow:SENSOR_LIMITS.nodesHigh);const nodes=points.slice(0,N);
  const g=new THREE.InstancedBufferGeometry();const pg=new THREE.PlaneGeometry(1,1);g.index=pg.index;g.attributes.position=pg.attributes.position;g.attributes.uv=pg.attributes.uv;
  const aP=new Float32Array(N*3),aS=new Float32Array(N);nodes.forEach((p,i)=>{aP[i*3]=p.x;aP[i*3+1]=p.y;aP[i*3+2]=p.z;});
  g.setAttribute('aP',new THREE.InstancedBufferAttribute(aP,3));const stimA=new THREE.InstancedBufferAttribute(aS,1);stimA.setUsage(THREE.DynamicDrawUsage);g.setAttribute('aS',stimA);g.instanceCount=N;
  const mat=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,fog:false,uniforms:{uTime:{value:0}},
   vertexShader:`attribute vec3 aP;attribute float aS;varying vec2 vU;varying float vS;uniform float uTime;void main(){vU=uv-.5;vS=aS;vec4 mv=viewMatrix*vec4(aP,1.);float sz=(.25+aS*.9);mv.xy+=position.xy*sz*step(.01,aS);gl_Position=projectionMatrix*mv;}`,
   fragmentShader:`varying vec2 vU;varying float vS;uniform float uTime;void main(){float r=length(vU)*2.;if(vS<.01)discard;
    float ring(float o){return exp(-pow((r-.62-o)*14.,2.));}vec3 c=vec3(ring(-.04),ring(0.),ring(.04))*.9;// refraction: rgb-split ring
    c+=vec3(.75,.9,1.)*exp(-r*r*9.)*1.3;gl_FragColor=vec4(c*vS,vS*max(c.r,max(c.g,c.b)));}`});
  const mesh=new THREE.Mesh(g,mat);mesh.frustumCulled=false;mesh.renderOrder=5;mesh.name='sensor-nodes';scene.add(mesh);
  // ---- nerve networks per creature
  type Nerve={pal:[number,number];id:string;lines:import('three').LineSegments;nodes:import('three').Points;arcs:import('three').LineSegments;level:number;tips:V3[];heart:V3;flare:number;host:import('three').Object3D;dims:any;seed:import('three').Mesh};
  const nerves=new Map<string,Nerve>();
  function nerveMat(c:number,o:number){return new THREE.LineBasicMaterial({color:c,transparent:true,opacity:o,blending:THREE.AdditiveBlending,depthWrite:false,depthTest:false,fog:false});}
  function rebuild(n:Nerve){const tr=nerveTree(n.id,n.dims,n.level);const P=new Float32Array(tr.segs.length*6),C=new Float32Array(tr.segs.length*6);const pal=(n as any).pal;const ca=new THREE.Color(pal[1]),cb=new THREE.Color(pal[0]);
   tr.segs.forEach((s:any,i:number)=>{P.set([s.a.x,s.a.y,s.a.z,s.b.x,s.b.y,s.b.z],i*6);const c=ca.clone().lerp(cb,Math.min(1,s.d/2));const k=s.d===0?1.3:1;C.set([c.r*k,c.g*k,c.b*k,c.r*k,c.g*k,c.b*k],i*6);});
   n.lines.geometry.dispose();const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(P,3));geo.setAttribute('color',new THREE.BufferAttribute(C,3));n.lines.geometry=geo;n.nodes.geometry=geo;/* junction glints share the buffer */n.tips=tr.tips.slice(0,low?10:24);}
  /** Attach to a creature host (local space). dims from its body box: heart seed, head, tail, limb tips. */
  function attach(id:string,host:import('three').Object3D,dims:{heart:V3;head:V3;tail:V3;limbs:V3[]},palette?:'warm'){
   if(nerves.has(id))return nerves.get(id)!;const pal=palette==='warm'?NERVE_PALETTES.warm:((NERVE_PALETTES as any)[id]||NERVE_PALETTES.default);
   const lines=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity:.2,blending:THREE.AdditiveBlending,depthWrite:false,depthTest:false,fog:false}));lines.renderOrder=6;lines.frustumCulled=false;
   const arcs=new THREE.LineSegments(new THREE.BufferGeometry(),nerveMat(pal[1],.0));arcs.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array((low?10:24)*2*2*3),3));arcs.renderOrder=6;arcs.frustumCulled=false;
   const seed=new THREE.Mesh(new THREE.SphereGeometry(.035,8,6),new THREE.MeshBasicMaterial({color:pal[1],transparent:true,opacity:.6,blending:THREE.AdditiveBlending,depthTest:false,fog:false}));seed.position.set(dims.heart.x,dims.heart.y,dims.heart.z);seed.renderOrder=7;
   const nodes=new THREE.Points(new THREE.BufferGeometry(),new THREE.PointsMaterial({size:.035,vertexColors:true,transparent:true,opacity:.45,blending:THREE.AdditiveBlending,depthWrite:false,depthTest:false,fog:false}));nodes.renderOrder=6;nodes.frustumCulled=false;
   host.add(lines,nodes,arcs,seed);const n:Nerve={pal,id,lines,nodes,arcs,level:growthLevel(xp[id]||0),tips:[],heart:dims.heart,flare:0,host,dims,seed};rebuild(n);nerves.set(id,n);return n;}
  // ---- signal pulses (words → light)
  const PM=SENSOR_LIMITS.pulsesMax;const pp=new Float32Array(PM*3);const pgeo=new THREE.BufferGeometry();pgeo.setAttribute('position',new THREE.BufferAttribute(pp,3));
  const pts=new THREE.Points(pgeo,new THREE.PointsMaterial({color:0xffffff,size:.16,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false,fog:false}));pts.frustumCulled=false;scene.add(pts);
  const pulses:{a:V3;b:V3;t:number;id:string;on?:()=>void}[]=[];const stim=new Float32Array(N);let saveT=0;const wv=new THREE.Vector3();
  return {mesh,nerves,attach,
   xp:(id:string)=>xp[id]||0,
   /** words: light pulses leave the nearest sensor nodes and travel to the creature; onArrive = vibration. */
   signal(id:string,to:V3,strength:number,onArrive:()=>void){for(const i of nearestNodes(nodes,to,3)){stim[i]=1;if(pulses.length<PM)pulses.push({a:{...nodes[i]},b:{...to},t:0,id,on:onArrive});}},
   stimulate(p:V3,r=1.5,a=.6){for(let i=0;i<N;i++){const n=nodes[i];const d=Math.hypot(n.x-p.x,n.y-p.y,n.z-p.z);if(d<r)stim[i]=Math.max(stim[i],a*(1-d/r));}},
   experience(id:string,amt=1){xp[id]=(xp[id]||0)+amt;const n=nerves.get(id);if(n){const L=growthLevel(xp[id]);if(L!==n.level){n.level=L;rebuild(n);}n.flare=Math.min(1,n.flare+.35);}},
   flare(id:string,a=1){const n=nerves.get(id);if(n)n.flare=Math.min(1,Math.max(n.flare,a));},
   update(dt:number,t:number,emotion:Record<string,number>={}){mat.uniforms.uTime.value=t;
    for(let i=0;i<N;i++){stim[i]=Math.max(0,stim[i]-dt*.35);aS[i]=stim[i];}stimA.needsUpdate=true;
    let k=0;for(let i=pulses.length-1;i>=0;i--){const p=pulses[i];p.t+=dt*.9;const q=pulseAt(p,p.t);if(!q){const done=pulses.splice(i,1)[0];done.on?.();this.flare(done.id,1);this.experience(done.id,.34);continue;}
     pp[k*3]=q.x;pp[k*3+1]=q.y;pp[k*3+2]=q.z;k++;}
    for(;k<PM;k++){pp[k*3+1]=-999;}(pgeo.attributes.position as any).needsUpdate=true;
    for(const n of nerves.values()){const e=emotion[n.id]||0;n.flare=Math.max(0,n.flare-dt*.6);const f=Math.max(n.flare,e*.6);
     (n.lines.material as any).opacity=.4+.6*f;(n.nodes.material as any).opacity=.45+.55*f;(n.seed.material as any).opacity=.5+.5*f;n.seed.scale.setScalar(1+f*.35+Math.sin(t*3)*.06);
     // electric arcs at tips (re-jittered every frame, only visible when flaring)
     const A=(n.arcs.geometry.attributes.position as any);const r=entityRng(n.id+':'+Math.floor(t*12));let j=0;
     for(const tp of n.tips){let ax=tp.x,ay=tp.y,az=tp.z;for(let s=0;s<2;s++){const bx=ax+(r()-.5)*.06,by=ay+(r()-.5)*.06,bz=az+(r()-.5)*.06;A.setXYZ(j++,ax,ay,az);A.setXYZ(j++,bx,by,bz);ax=bx;ay=by;az=bz;}}
     A.needsUpdate=true;(n.arcs.material as any).opacity=f*.9;
     n.host.getWorldPosition(wv);if(f>.3)this.stimulate({x:wv.x,y:wv.y,z:wv.z},2.2,f*.7);}
    saveT+=dt;if(saveT>5&&typeof window!=='undefined'){saveT=0;saveXP(window.localStorage,xp);}}};
}
/** Body dims from a living-core: heart seed at the chest, spine head↔tail along the long axis, limb tips = extremal vertices. */
export function bodyDims(LC:any){let src:any=null;(LC?.body?.isMesh?[LC.body]:LC?.body?.children||[]).forEach((o:any)=>{if(o.isMesh&&o.geometry?.attributes?.position&&(!src||o.geometry.attributes.position.count>src.geometry.attributes.position.count))src=o;});
  if(!src)return null;const g=src.geometry;g.computeBoundingBox();const b=g.boundingBox;const c={x:(b.min.x+b.max.x)/2,y:(b.min.y+b.max.y)/2,z:(b.min.z+b.max.z)/2};
  const ex=b.max.x-b.min.x,ez=b.max.z-b.min.z,h=b.max.y-b.min.y;const P=g.attributes.position;const n=Math.min(P.count,g.drawRange?.count||P.count);
  const head={x:c.x,y:b.max.y-h*.18,z:c.z},tail={x:c.x,y:b.min.y+h*.22,z:c.z};
  // limbs: farthest vertices from the heart in 8 directional sectors (excluding the top/head cap)
  const heart={x:c.x,y:c.y+h*.08,z:c.z};const best:any[]=[];
  for(let i=0;i<n;i+=7){const x=P.getX(i),y=P.getY(i),z=P.getZ(i);if(y===0&&x===0&&z===0)continue;const dx=x-heart.x,dy=y-heart.y,dz=z-heart.z;const sec=(Math.atan2(dz,dx)+Math.PI)/(2*Math.PI)*4|0;const k=(dy>0?0:4)+Math.min(3,sec);const d=dx*dx+dy*dy+dz*dz;
   if(!best[k]||d>best[k].d)best[k]={d,p:{x,y,z}};}
  const limbs=best.filter(Boolean).map(o=>o.p);void ex;void ez;return {host:src,dims:{heart,head,tail,limbs}};}
