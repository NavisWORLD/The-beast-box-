// Glowing wireframe companion critters: one small line-mesh critter per creature, IK spider-walk on
// surfaces, jellyfish swim when airborne, feeding on drifting universe motes (river sparks, glyphs,
// creation remnants) with a glow pulse that grows them and shares energy with their creature.
import {COMPANION_LIMITS,companionTheme,kneeIK,legStep,feed,nearestMote,loadGrowth,saveGrowth} from './companion-math.mjs';
/** World-unit size of a companion (Zeref is ~0.8 tall): small but readable, same scale everywhere. */
export const COMPANION_SIZE=2.6;
type T=typeof import('three');type V3={x:number;y:number;z:number};
export type Owner={id:string;x:number;y:number;z:number;air?:number};
export function createCompanions(THREE:T,scene:import('three').Scene,{low}:{low:boolean}){
  const root=new THREE.Group();root.name='wire-companions';scene.add(root);
  const growth:Record<string,number>=typeof window!=='undefined'?loadGrowth(window.localStorage):{};
  const lineMat=(c:number,o=.9)=>new THREE.LineBasicMaterial({color:c,transparent:true,opacity:o,blending:THREE.AdditiveBlending,depthWrite:false,fog:false});
  // ---- food motes
  const NM=low?COMPANION_LIMITS.motesLow:COMPANION_LIMITS.motesHigh;const motes=[...Array(NM)].map(()=>({x:0,y:-999,z:0,alive:false,e:Math.random(),src:'river'}));
  const mg=new THREE.BufferGeometry();const mp=new Float32Array(NM*3);mg.setAttribute('position',new THREE.BufferAttribute(mp,3));
  const moteMat=new THREE.PointsMaterial({color:0xbff7ff,size:.07,transparent:true,opacity:.85,blending:THREE.AdditiveBlending,depthWrite:false});
  const motePts=new THREE.Points(mg,moteMat);motePts.frustumCulled=false;root.add(motePts);
  let spawnAcc=0;const remnants:V3[]=[];
  const spawn=(near:V3,src='river')=>{const m=motes.find(q=>!q.alive);if(!m)return;const a=Math.random()*6.283,r=.6+Math.random()*1.8;m.x=near.x+Math.cos(a)*r;m.z=near.z+Math.sin(a)*r;m.y=(near.y||0)+.15+Math.random()*.5;m.alive=true;m.e=Math.random();m.src=src;};
  // ---- critters
  type C={id:string;th:any;g:import('three').Group;body:import('three').LineSegments;legsL?:import('three').LineSegments;legs:any[];wings:import('three').Line[];tents:{ln:import('three').Line;pts:import('three').Vector3[];k:number;init?:boolean}[];
    x:number;y:number;z:number;vx:number;vz:number;grow:number;pulse:number;fed:number;head:number;air:number;wander:V3};
  const list=new Map<string,C>();
  function build(id:string):C{const th=companionTheme(id);const g=new THREE.Group();g.name='companion-'+id;
   const geo=th.motif==='crystal-mite'?new THREE.OctahedronGeometry(.07,0):th.motif==='scaled-jelly'?new THREE.SphereGeometry(.08,8,5,0,6.283,0,1.6):th.motif==='star-beetle'?new THREE.DodecahedronGeometry(.065,0):new THREE.IcosahedronGeometry(.065,th.motif==='ice-spider'?0:1);
   const body=new THREE.LineSegments(new THREE.EdgesGeometry(geo,1),lineMat(th.color));body.scale.set(1,th.motif==='cat-moth'?1.25:.8,th.motif==='horn-firefly'?1.4:1.15);g.add(body);
   const head=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(.035,0),1),lineMat(th.accent));head.position.set(0,.02,.08);g.add(head);
   if(th.motif==='cat-moth'){for(const s of [-1,1]){const ear=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(.012*s,.045,.09),new THREE.Vector3(.03*s,.085,.085),new THREE.Vector3(.035*s,.04,.075)]),lineMat(th.accent));g.add(ear);}}
   if(th.motif==='horn-firefly'){const horn=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,.04,.1),new THREE.Vector3(0,.09,.15)]),lineMat(th.accent));g.add(horn);}
   const legs:any[]=[];let legsL;
   if(th.legs){legsL=new THREE.LineSegments(new THREE.BufferGeometry(),lineMat(th.accent,.8));legsL.geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(th.legs*4*3),3));legsL.frustumCulled=false;root.add(legsL);
    for(let i=0;i<th.legs;i++){const side=i%2?1:-1,k=Math.floor(i/2),n=th.legs/2;const ang=(k-(n-1)/2)/Math.max(1,n-1)*1.2;legs.push({side,ang,foot:{x:0,y:0,z:0},from:{x:0,y:0,z:0},to:{x:0,y:0,z:0},t:1,init:false,phase:i%2});}}
   const wings:import('three').Line[]=[];if(th.wings)for(const s of [-1,1]){const pts=[...Array(13)].map((_,i)=>{const a=i/12*Math.PI;return new THREE.Vector3(s*Math.sin(a)*.13,Math.sin(a)*.03,-Math.cos(a)*.07+.01);});
    const w=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),lineMat(th.color,.75));w.userData.s=s;g.add(w);wings.push(w);}
   const tents:any[]=[];for(let i=0;i<th.tentacles;i++){const n=low?6:9;const gg=new THREE.BufferGeometry();gg.setAttribute('position',new THREE.BufferAttribute(new Float32Array(n*3),3));const ln=new THREE.Line(gg,lineMat(th.accent,.7));ln.frustumCulled=false;root.add(ln);tents.push({ln,pts:[...Array(n)].map(()=>new THREE.Vector3()),init:false,k:i});}
   root.add(g);return {id,th,g,body,legsL,legs,wings,tents,x:0,y:0,z:0,vx:0,vz:0,grow:growth[id]||1,pulse:0,fed:0,head:0,air:0,wander:{x:0,y:0,z:0}};}
  let feedCb:(id:string,e:number)=>void=()=>{};let saveT=0;const tmp=new THREE.Vector3();
  return {root,motes,list,
   onFeed(cb:typeof feedCb){feedCb=cb;},
   remnant(p:V3){remnants.push({...p});if(remnants.length>12)remnants.shift();for(let i=0;i<3;i++)spawn(p,'remnant');},
   glyph(p:V3){spawn(p,'glyph');},
   sync(owners:Owner[]){const ids=new Set(owners.slice(0,COMPANION_LIMITS.maxCompanions).map(o=>o.id));
    for(const [id,c] of list)if(!ids.has(id)){root.remove(c.g);if(c.legsL)root.remove(c.legsL);c.tents.forEach(t=>root.remove(t.ln));list.delete(id);}
    for(const o of owners.slice(0,COMPANION_LIMITS.maxCompanions))if(!list.has(o.id)){const c=build(o.id);c.x=o.x+.5;c.z=o.z+.3;c.y=o.y;c.wander={x:o.x+.5,y:o.y,z:o.z+.3};list.set(o.id,c);}},
   step(dt:number,t:number,owners:Owner[],ground:(p:V3)=>{y:number}){if(!(dt>0))return;
    spawnAcc+=dt;if(spawnAcc>(low?1.2:.7)&&owners.length){spawnAcc=0;spawn(owners[Math.floor(Math.random()*owners.length)]);}
    for(let i=0;i<NM;i++){const m=motes[i];if(m.alive){m.x+=Math.sin(t*.7+i)*.12*dt+.08*dt;m.z+=Math.cos(t*.5+i*1.3)*.12*dt;m.y+=Math.sin(t*1.3+i)*.05*dt;}mp[i*3]=m.x;mp[i*3+1]=m.alive?m.y:-999;mp[i*3+2]=m.z;}
    (mg.attributes.position as any).needsUpdate=true;
    const seen=new Set<string>();for(const o of owners){if(seen.has(o.id))continue;seen.add(o.id);const c=list.get(o.id);if(!c)continue;const air=(o.air||0);c.air+=(air-c.air)*Math.min(1,dt*3);
     let tx:number,tz:number,ty:number;
     if(c.air>.4){const a=t*.9;tx=o.x+Math.cos(a)*.55;tz=o.z+Math.sin(a)*.55;ty=o.y+.55+Math.sin(t*1.7)*.08;}
     else{const m=nearestMote(c,motes);if(m){tx=m.x;tz=m.z;}else{if(Math.hypot(c.wander.x-c.x,c.wander.z-c.z)<.1||Math.hypot(c.wander.x-o.x,c.wander.z-o.z)>1.3){const a=Math.random()*6.283;c.wander={x:o.x+Math.cos(a)*(.5+Math.random()*.7),y:0,z:o.z+Math.sin(a)*(.5+Math.random()*.7)};}tx=c.wander.x;tz=c.wander.z;}
      ty=ground({x:c.x,y:o.y+.5,z:c.z}).y+.06*COMPANION_SIZE*c.grow;}
     const dx=tx-c.x,dz=tz-c.z,d=Math.hypot(dx,dz)||1,sp=c.air>.4?3.5:.65;const k=Math.min(1,dt*sp/d);c.vx=dx*k/dt;c.vz=dz*k/dt;c.x+=dx*k;c.z+=dz*k;c.y+=(ty-c.y)*Math.min(1,dt*(c.air>.4?3:10));
     if(d>.02)c.head+=((Math.atan2(dx,dz)-c.head+Math.PI*3)%(Math.PI*2)-Math.PI)*Math.min(1,dt*6);
     // feed (also grab motes at mote height)
     const e=feed({get x(){return c.x},get y(){return c.y+.2},get z(){return c.z},set pulse(v:number){c.pulse=v},get grow(){return c.grow},set grow(v:number){c.grow=v},get fed(){return c.fed},set fed(v:number){c.fed=v}} as any,motes,{reach:.3});
     if(e){growth[c.id]=c.grow;feedCb(c.id,e);}
     c.pulse=Math.max(0,c.pulse-dt*1.6);const s=COMPANION_SIZE*c.grow*(1+c.pulse*.35);
     c.g.position.set(c.x,c.y+(c.air>.4?Math.sin(t*2.4)*.03:0),c.z);c.g.rotation.set(Math.sin(t*2)*.15*c.air,c.head,Math.sin(t*1.5)*.12*c.air);c.g.scale.setScalar(s);
     (c.body.material as any).opacity=.65+.35*c.pulse;
     for(const w of c.wings){const f=Math.sin(t*(c.air>.4?9:4))*(.35+.4*c.air);w.rotation.z=w.userData.s*f;}
     // legs: spider IK on the surface; airborne they trail like jelly tentacles
     if(c.legsL){const P=(c.legsL.geometry.attributes.position as any);const L=.075*s;const ch=Math.cos(c.head),sh=Math.sin(c.head);
      c.legs.forEach((lg,i)=>{const lx=lg.side*Math.cos(lg.ang)*.16*s,lz=Math.sin(lg.ang)*.16*s;const rx=c.x+lx*ch+lz*sh,rz=c.z-lx*sh+lz*ch;
       const hip={x:c.x+lx*.35*ch+lz*.35*sh,y:c.y,z:c.z-lx*.35*sh+lz*.35*ch};
       let foot:V3;if(c.air>.4){foot={x:hip.x-c.vx*.06+Math.sin(t*3+i)*.02,y:hip.y-.13*s,z:hip.z-c.vz*.06+Math.cos(t*3+i)*.02};lg.init=false;}
       else{const gy=ground({x:rx,y:c.y+.3,z:rz}).y;if(!lg.init){lg.foot={x:rx,y:gy,z:rz};lg.init=true;}legStep(lg,{x:rx+c.vx*.05,y:gy,z:rz+c.vz*.05},dt,{stride:.08*s});foot=lg.foot;}
       const kn=kneeIK(hip,foot,L);P.setXYZ(i*4,hip.x,hip.y,hip.z);P.setXYZ(i*4+1,kn.x,kn.y,kn.z);P.setXYZ(i*4+2,kn.x,kn.y,kn.z);P.setXYZ(i*4+3,foot.x,foot.y,foot.z);});
      P.needsUpdate=true;}
     for(const tn of c.tents){const a=(tn.ln.geometry.attributes.position as any);const k2=tn.k/c.tents.length*6.283;tmp.set(c.x+Math.cos(k2)*.05*s,c.y-.01,c.z+Math.sin(k2)*.05*s);
      if(!(tn as any).init){tn.pts.forEach(p=>p.copy(tmp));(tn as any).init=true;}tn.pts[0].copy(tmp);
      for(let i=1;i<tn.pts.length;i++){const p=tn.pts[i],q=tn.pts[i-1];p.x+=(q.x-p.x)*Math.min(1,dt*10)+Math.sin(t*2+i*.6+k2)*.004;p.y+=(q.y-.028*s-p.y)*Math.min(1,dt*10);p.z+=(q.z-p.z)*Math.min(1,dt*10)+Math.cos(t*2.3+i*.5)*.004;}
      tn.pts.forEach((p,i)=>a.setXYZ(i,p.x,p.y,p.z));a.needsUpdate=true;}}
    saveT+=dt;if(saveT>5&&typeof window!=='undefined'){saveT=0;saveGrowth(window.localStorage,growth);}},
   dispose(){scene.remove(root);}};
}
