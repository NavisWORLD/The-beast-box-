// Geyser Jelly events (PR 2/4): Strokkur geyser cycle, hot springs, mud pot, boardwalk; scoria volcano with a
// lava lake and a lava channel steaming into the sea; eruptions and tremors with lava bombs, steam and ash puffs.
import {GJ,geyserCycle,islandHeight,bombAt,rng} from './geyser-math.mjs';
type T=typeof import('three');
type Island={root:import('three').Group;tip:(a?:number,d?:number)=>void;splash:(x:number,z:number,a?:number)=>void};
export function addGeyserEvents(THREE:T,isl:Island,{low}:{low:boolean}){
  const root=new THREE.Group();root.name='gj-events';isl.root.add(root);const r=rng('gj-events');
  const G=GJ.geyser,V=GJ.volcano,gy=islandHeight(G.x,G.z);const U={uT:{value:0},uHeat:{value:0}};
  const listeners:((e:string)=>void)[]=[];const emit=(e:string)=>listeners.forEach(f=>f(e));
  // ---- puffs: pooled steam / ash / spray particles
  const N=low?180:420,pp=new Float32Array(N*3),pv=new Float32Array(N*3),pl=new Float32Array(N),pk=new Float32Array(N),ps=new Float32Array(N);let pi=0;
  const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(pp,3));pg.setAttribute('aL',new THREE.BufferAttribute(pl,1));pg.setAttribute('aK',new THREE.BufferAttribute(pk,1));pg.setAttribute('aS',new THREE.BufferAttribute(ps,1));
  const puffs=new THREE.Points(pg,new THREE.ShaderMaterial({transparent:true,depthWrite:false,uniforms:{},
    vertexShader:'attribute float aL,aK,aS;varying float vL,vK;void main(){vL=aL;vK=aK;vec4 mv=modelViewMatrix*vec4(position,1.);gl_PointSize=aL>0.?min(64.,aS*(1.6-aL)*60./-mv.z)*smoothstep(.35,1.1,-mv.z):0.;gl_Position=projectionMatrix*mv;}',
    fragmentShader:'varying float vL,vK;void main(){if(vL<=0.)discard;float d=length(gl_PointCoord-.5);if(d>.5)discard;vec3 c=vK<.5?vec3(.92,.96,1.):vK<1.5?vec3(.25,.22,.24):vec3(.75,.95,1.);float a=smoothstep(.5,0.,d)*vL*(vK<1.5?.55:.8);gl_FragColor=vec4(c,a);}'}));
  puffs.frustumCulled=false;root.add(puffs);
  function puff(x:number,y:number,z:number,kind:0|1|2,vx=0,vy=.4,vz=0,size=.6){const i=pi++%N;pp.set([x,y,z],i*3);pv.set([vx+(r()-.5)*.2,vy*(0.7+r()*.6),vz+(r()-.5)*.2],i*3);pl[i]=1;pk[i]=kind;ps[i]=size*(.7+r()*.6);}
  // ---- Strokkur: pool, dome, boardwalk, hot springs, mud pot
  const pool=new THREE.Mesh(new THREE.CircleGeometry(.32,24),new THREE.MeshStandardMaterial({color:0x2ad4e0,emissive:0x0b6f7a,emissiveIntensity:.9,roughness:.1,transparent:true,opacity:.92}));pool.rotation.x=-Math.PI/2;pool.position.set(G.x,gy+.015,G.z);pool.name='gj-geyser';root.add(pool);
  const dome=new THREE.Mesh(new THREE.SphereGeometry(.3,20,12,0,Math.PI*2,0,Math.PI/2),new THREE.MeshStandardMaterial({color:0x8ff6ff,emissive:0x2aa6c0,transparent:true,opacity:.8,roughness:.05}));dome.position.copy(pool.position);dome.scale.setScalar(.001);root.add(dome);
  const plank=new THREE.BoxGeometry(.5,.025,.09),wood=new THREE.MeshStandardMaterial({color:0x6b4a32,roughness:.9});const nb=10;const walk=new THREE.InstancedMesh(plank,wood,nb);{const m=new THREE.Matrix4(),q=new THREE.Quaternion(),v=new THREE.Vector3(),s=new THREE.Vector3(1,1,1);for(let i=0;i<nb;i++){const a=-.6+i*.17,R=.75;const x=G.x+Math.cos(a)*R,z=G.z+Math.sin(a)*R;q.setFromAxisAngle(new THREE.Vector3(0,1,0),-a);m.compose(v.set(x,islandHeight(x,z)+.05,z),q,s);walk.setMatrixAt(i,m);}walk.instanceMatrix.needsUpdate=true;}root.add(walk);
  const springs=[[G.x+.55,G.z-.45],[G.x-.5,G.z-.35],[G.x+.2,G.z-.8]].map(([x,z],i)=>{const m=new THREE.Mesh(new THREE.CircleGeometry(.12+i*.02,16),new THREE.MeshStandardMaterial({color:i===2?0x6b5a48:0x37c9d6,emissive:i===2?0x1a1208:0x0a5a66,roughness:i===2?.95:.15}));m.rotation.x=-Math.PI/2;m.position.set(x,islandHeight(x,z)+.012,z);root.add(m);return m;});
  const mud=springs[2];
  // ---- volcano: lava lake in the crater + lava channel to the sea
  const lavaM=new THREE.ShaderMaterial({uniforms:U,toneMapped:false,vertexShader:'varying vec2 vU;void main(){vU=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:'uniform float uT,uHeat;varying vec2 vU;void main(){vec2 p=vU*vec2(8.,3.);float n=sin(p.x*2.1+uT*.9)*sin(p.y*3.3-uT*.7)+sin((p.x+p.y)*1.7+uT*1.3)*.5;float cr=smoothstep(.2,.9,n*.5+.5);vec3 c=mix(vec3(1.,.85,.3),vec3(.35,.05,.02),cr);c*=1.+uHeat*1.5;gl_FragColor=vec4(c,1.);}'});
  const lake=new THREE.Mesh(new THREE.CircleGeometry(GJ.volcano.crater*.95,28),lavaM);lake.rotation.x=-Math.PI/2;lake.position.set(V.x,islandHeight(V.x,V.z)+.02,V.z);lake.name='gj-volcano';root.add(lake);
  const E=GJ.channelEnd;const pts:import('three').Vector3[]=[];for(let i=0;i<=10;i++){const u=i/10;const x=V.x+(E.x-V.x)*u+Math.sin(u*5)*.25,z=V.z+(E.z-V.z)*u+Math.cos(u*4)*.2;const start=i===0?islandHeight(V.x+.5*Math.sign(E.x-V.x),V.z):0;pts.push(new THREE.Vector3(x,Math.max(GJ.sea+.02,(i===0?start:islandHeight(x,z))+.03),z));}
  const channel=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),low?24:48,.07,6,false),lavaM);root.add(channel);
  const glow=new THREE.PointLight(0xff6a2a,low?0:2.2,5,2);glow.position.set(V.x,lake.position.y+.6,V.z);root.add(glow);
  // ---- lava bombs
  const NB=low?8:16;const bombs=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.1,0),new THREE.MeshBasicMaterial({color:0xff7a2a,toneMapped:false}),NB);bombs.frustumCulled=false;root.add(bombs);
  const B:{x:number;y:number;z:number;vx:number;vy:number;vz:number;t:number;on:boolean}[]=Array.from({length:NB},()=>({x:0,y:0,z:0,vx:0,vy:0,vz:0,t:0,on:false}));const hide=new THREE.Matrix4().makeScale(0,0,0);for(let i=0;i<NB;i++)bombs.setMatrixAt(i,hide);
  function launch(n:number){let k=0;for(const b of B){if(b.on||k>=n)continue;const a=r()*6.283,s=.6+r()*1.4;Object.assign(b,{x:V.x,y:lake.position.y+.1,z:V.z,vx:Math.cos(a)*s,vy:3+r()*2.5,vz:Math.sin(a)*s,t:0,on:true});k++;}}
  let erupt=0,shake=0,manualGeyser=-1,lastPhase='';
  const api={root,U,on:(f:(e:string)=>void)=>{listeners.push(f);},
    erupt(){erupt=4.5;launch(NB);isl.tip(.35);emit('erupt');},
    tremor(){shake=2.4;isl.tip(.9);launch(Math.ceil(NB/2));for(let i=0;i<6;i++)isl.splash((r()-.5)*12,(r()-.5)*12,.3);emit('tremor');},
    geyser(){manualGeyser=0;emit('geyser-tap');},
    phase:'refill',jet:0,
    update(dt:number,t:number){const d=Math.min(.05,Math.max(0,dt||0));U.uT.value=t;
      // geyser: natural cycle, or a tap jumps straight to surge → burst
      const gt=manualGeyser>=0?(manualGeyser+=d,5.8+manualGeyser):t;if(manualGeyser>4.5)manualGeyser=-1;const gc:any=geyserCycle(gt);api.phase=gc.phase;api.jet=gc.jet;
      if(gc.phase!==lastPhase){if(gc.phase==='burst'){emit('geyser');isl.splash(G.x,G.z,.35);}lastPhase=gc.phase;}
      dome.scale.setScalar(.001+gc.dome*1.0);dome.visible=gc.dome>.01;pool.scale.setScalar(.6+.4*gc.pool);
      if(gc.jet>.02){for(let i=0;i<(low?2:4);i++)puff(G.x+(r()-.5)*.06,gy+.05,G.z+(r()-.5)*.06,2,(r()-.5)*.3,4.2*gc.jet+r()*.8,(r()-.5)*.3,.35);if(r()<.5)puff(G.x,gy+.2+gc.jet*2.2,G.z,0,0,.5,0,1.2);}
      else if(r()<d*3)puff(G.x,gy+.05,G.z,0,0,.25,0,.5);
      for(const s of springs)if(s!==mud&&r()<d*1.5)puff(s.position.x,s.position.y+.02,s.position.z,0,0,.2,0,.4);
      mud.position.y=islandHeight(mud.position.x,mud.position.z)+.012+Math.max(0,Math.sin(t*5))*.012;
      // volcano: heat, lava-sea steam, eruption fountain + ash
      erupt=Math.max(0,erupt-d);shake=Math.max(0,shake-d);U.uHeat.value=Math.min(1,erupt*.4+shake*.2);glow.intensity=(low?0:1.6)+U.uHeat.value*3;
      if(r()<d*4)puff(E.x+(r()-.5)*.2,GJ.sea+.05,E.z+(r()-.5)*.2,0,0,.35,0,.7);
      if(erupt>0){if(r()<.6)puff(V.x+(r()-.5)*.2,lake.position.y+.2,V.z+(r()-.5)*.2,1,(r()-.5)*.4,1.4+r(),(r()-.5)*.4,1.1);if(r()<.4)launch(1);}
      isl.root.position.x=GJ.cx+(shake>0?Math.sin(t*61)*.03*shake:0);isl.root.position.z=GJ.cz+(shake>0?Math.cos(t*53)*.03*shake:0);
      const m=new THREE.Matrix4();B.forEach((b,i)=>{if(!b.on)return;b.t+=d;const p=bombAt(b,b.t);const gh=Math.max(GJ.sea,islandHeight(p.x,p.z));
        if(!Number.isFinite(p.y)||p.y<gh||b.t>4){b.on=false;bombs.setMatrixAt(i,hide);if(Number.isFinite(p.x)){puff(p.x,gh+.05,p.z,gh<=GJ.sea?0:1,0,.5,0,.7);if(gh<=GJ.sea)isl.splash(p.x,p.z,.2);}return;}
        m.makeTranslation(p.x,p.y,p.z);bombs.setMatrixAt(i,m);if(r()<.3)puff(p.x,p.y,p.z,1,0,.1,0,.3);});bombs.instanceMatrix.needsUpdate=true;
      for(let i=0;i<N;i++){if(pl[i]<=0)continue;const k=pk[i];pl[i]-=d*(k===2?.9:.45);const j=i*3;pv[j+1]+=k===2?-9.8*d*.5:.1*d;pp[j]+=pv[j]*d;pp[j+1]+=pv[j+1]*d;pp[j+2]+=pv[j+2]*d;if(!Number.isFinite(pp[j+1]))pl[i]=0;}
      (pg.attributes.position as any).needsUpdate=true;(pg.attributes.aL as any).needsUpdate=true;(pg.attributes.aK as any).needsUpdate=true;(pg.attributes.aS as any).needsUpdate=true;},
    pickables:()=>[pool,dome,lake],puff};
  return api;
}
