// Geyser Jelly life (PR 3/4): humpback whale (blow + breach), boat Hafdis (bay loop from the jetty), puffins,
// five horses, turf houses, church, flag, lighthouse, blue lagoon with bathers, boardwalk tourists, fish schools.
import {GJ,islandHeight,boatPose,whalePose,rng} from './geyser-math.mjs';
type T=typeof import('three');
type Isl={root:import('three').Group;tip:(a?:number,d?:number)=>void;splash:(x:number,z:number,a?:number)=>void};
type Puff=(x:number,y:number,z:number,k:0|1|2,vx?:number,vy?:number,vz?:number,s?:number)=>void;
export function addIslandLife(THREE:T,isl:Isl,puff:Puff,{low}:{low:boolean}){
  const root=new THREE.Group();root.name='gj-life';isl.root.add(root);const r=rng('gj-life');const H=(x:number,z:number)=>islandHeight(x,z);
  const std=(c:number,e=0)=>new THREE.MeshStandardMaterial({color:c,emissive:e,roughness:.8,flatShading:true});
  const listeners:((e:string)=>void)[]=[];const emit=(e:string)=>listeners.forEach(f=>f(e));
  // ---- lighthouse with a sweeping beam
  const L=GJ.lighthouse,ly=H(L.x,L.z);const lh=new THREE.Group();lh.position.set(L.x,ly,L.z);root.add(lh);
  const tower=new THREE.Mesh(new THREE.CylinderGeometry(.09,.13,.7,10),std(0xf2f0ea));tower.position.y=.35;const band=new THREE.Mesh(new THREE.CylinderGeometry(.1,.11,.12,10),std(0xc0302a));band.position.y=.45;
  const lamp=new THREE.Mesh(new THREE.SphereGeometry(.07,10,8),new THREE.MeshBasicMaterial({color:0xfff2b0,toneMapped:false}));lamp.position.y=.76;
  const beamG=new THREE.ConeGeometry(.35,3.2,16,1,true);beamG.translate(0,-1.6,0);beamG.rotateZ(Math.PI/2);const beam=new THREE.Mesh(beamG,new THREE.MeshBasicMaterial({color:0xfff2c0,transparent:true,opacity:.12,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide,fog:false}));beam.position.y=.76;lh.add(tower,band,lamp,beam);
  // ---- village: turf houses, church, flag, horses
  const Vg=GJ.village;const turf=std(0x3f6a35),wall=std(0xd8cfc0),door=std(0x2a1d14);
  for(let i=0;i<4;i++){const x=Vg.x-.6+i*.32,z=Vg.z+(i%2)*.18;const g=new THREE.Group();g.position.set(x,H(x,z),z);g.rotation.y=.2;
    const base=new THREE.Mesh(new THREE.BoxGeometry(.22,.12,.3),wall);base.position.y=.06;const roof=new THREE.Mesh(new THREE.CylinderGeometry(.001,.17,.3,3,1),turf);roof.rotation.set(Math.PI/2,0,Math.PI/2);roof.scale.set(1,1,.9);roof.position.y=.17;
    const d=new THREE.Mesh(new THREE.PlaneGeometry(.06,.08),door);d.position.set(0,.05,.151);g.add(base,roof,d);root.add(g);}
  {const x=Vg.x+.75,z=Vg.z-.15;const g=new THREE.Group();g.position.set(x,H(x,z),z);const nave=new THREE.Mesh(new THREE.BoxGeometry(.2,.18,.34),wall);nave.position.y=.09;
    const roof=new THREE.Mesh(new THREE.CylinderGeometry(.001,.16,.36,3,1),std(0xb0302a));roof.rotation.set(Math.PI/2,0,Math.PI/2);roof.position.y=.22;const st=new THREE.Mesh(new THREE.ConeGeometry(.06,.26,4),std(0xb0302a));st.position.set(0,.4,.13);
    const tw=new THREE.Mesh(new THREE.BoxGeometry(.1,.16,.1),wall);tw.position.set(0,.22,.13);g.add(nave,roof,tw,st);root.add(g);}
  const flagC=document.createElement('canvas');flagC.width=72;flagC.height=50;{const x=flagC.getContext('2d')!;x.fillStyle='#02529C';x.fillRect(0,0,72,50);x.fillStyle='#fff';x.fillRect(18,0,14,50);x.fillRect(0,18,72,14);x.fillStyle='#DC1E35';x.fillRect(21,0,8,50);x.fillRect(0,21,72,8);}
  const flagT=new THREE.CanvasTexture(flagC);flagT.colorSpace=THREE.SRGBColorSpace;const flagG=new THREE.PlaneGeometry(.22,.15,8,1);const flag=new THREE.Mesh(flagG,new THREE.MeshBasicMaterial({map:flagT,side:THREE.DoubleSide}));
  {const x=Vg.x+.4,z=Vg.z+.45,y=H(x,z);const pole=new THREE.Mesh(new THREE.CylinderGeometry(.008,.008,.55,5),std(0xdddddd));pole.position.set(x,y+.27,z);flag.position.set(x+.11,y+.47,z);root.add(pole,flag);}
  const flagBase=Float32Array.from((flagG.attributes.position as any).array as Float32Array);
  const horses=Array.from({length:5},(_,i)=>{const g=new THREE.Group();const c=[0x6b4a2a,0xd9c9a8,0x2a211a,0x8a6a4a,0xf0ece4][i];const m=std(c);
    const body=new THREE.Mesh(new THREE.BoxGeometry(.16,.07,.06),m);body.position.y=.1;const neck=new THREE.Mesh(new THREE.BoxGeometry(.04,.09,.045),m);neck.position.set(.08,.15,0);neck.rotation.z=-.5;const head=new THREE.Mesh(new THREE.BoxGeometry(.06,.035,.035),m);head.position.set(.11,.18,0);
    g.add(body,neck,head);for(const [lx,lz] of [[.06,.02],[.06,-.02],[-.06,.02],[-.06,-.02]]){const leg=new THREE.Mesh(new THREE.BoxGeometry(.018,.07,.018),m);leg.position.set(lx,.035,lz);g.add(leg);}
    root.add(g);return {g,ph:r()*6.283,cx:Vg.x-.4+r()*.9,cz:Vg.z-1.1+r()*.5};});
  // ---- blue lagoon with bathers; boardwalk tourists
  const Lg=GJ.lagoon;const lag=new THREE.Mesh(new THREE.CircleGeometry(Lg.r*.98,28),new THREE.MeshStandardMaterial({color:0x8fe3ee,emissive:0x2a8a9a,emissiveIntensity:.6,roughness:.25,transparent:true,opacity:.95}));lag.rotation.x=-Math.PI/2;lag.position.set(Lg.x,.06,Lg.z);root.add(lag);
  const skin=[0xf1c9a5,0xc68642,0x8d5524,0xe0ac69];const bathers=Array.from({length:low?3:5},(_,i)=>{const m=new THREE.Mesh(new THREE.SphereGeometry(.03,8,6),std(skin[i%4]));root.add(m);return {m,a:i*1.3,rr:.2+r()*.4};});
  const G=GJ.geyser;const coats=[0xe0402a,0x2a6ae0,0xf2c12a,0x2aa06a,0xffffff];const tourists=Array.from({length:low?3:5},(_,i)=>{const g=new THREE.Group();const b=new THREE.Mesh(new THREE.CapsuleGeometry(.022,.05,3,6),std(coats[i]));b.position.y=.06;const hd=new THREE.Mesh(new THREE.SphereGeometry(.018,6,5),std(skin[i%4]));hd.position.y=.115;g.add(b,hd);root.add(g);return {g,u:r(),sp:.04+r()*.05,dir:i%2?1:-1};});
  // ---- jetty + boat Hafdis
  const J=GJ.jetty;const jetty=new THREE.Mesh(new THREE.BoxGeometry(.18,.04,1.1),std(0x5a4030));jetty.position.set(J.x,GJ.sea+.06,J.z-.5);root.add(jetty);
  const boat=new THREE.Group();boat.name='gj-boat';const hull=new THREE.Mesh(new THREE.BoxGeometry(.18,.08,.5),std(0xd03a2a));hull.position.y=.03;const bow=new THREE.Mesh(new THREE.ConeGeometry(.09,.18,4),std(0xd03a2a));bow.rotation.x=Math.PI/2;bow.position.set(0,.03,.33);bow.rotation.y=Math.PI/4;
  const cab=new THREE.Mesh(new THREE.BoxGeometry(.13,.09,.16),std(0xf4f1ea));cab.position.set(0,.11,-.05);const mast=new THREE.Mesh(new THREE.CylinderGeometry(.006,.006,.28,4),std(0xffffff));mast.position.set(0,.22,.05);boat.add(hull,bow,cab,mast);root.add(boat);
  const hitBoat=new THREE.Mesh(new THREE.BoxGeometry(.5,.4,.8),new THREE.MeshBasicMaterial({visible:false}));boat.add(hitBoat);hitBoat.name='gj-boat';
  // ---- humpback whale
  const whale=new THREE.Group();whale.name='gj-whale';const wm=std(0x2a3240);const wbody=new THREE.Mesh(new THREE.SphereGeometry(.2,16,10),wm);wbody.scale.set(1,.7,2.6);const belly=new THREE.Mesh(new THREE.SphereGeometry(.19,12,8),std(0xc8ccd2));belly.scale.set(.9,.55,2.3);belly.position.y=-.04;
  const fluke=new THREE.Mesh(new THREE.BoxGeometry(.5,.02,.14),wm);fluke.position.z=-.6;const fin1=new THREE.Mesh(new THREE.BoxGeometry(.45,.015,.09),wm);fin1.position.set(0,-.05,.18);fin1.rotation.y=.3;
  const hitW=new THREE.Mesh(new THREE.BoxGeometry(.8,.8,1.6),new THREE.MeshBasicMaterial({visible:false}));hitW.name='gj-whale';whale.add(wbody,belly,fluke,fin1,hitW);root.add(whale);
  // ---- puffins (instanced): perched on the cliffs + a few circling
  const nP=low?10:22;const pufG=new THREE.SphereGeometry(.025,6,5);const puffins=new THREE.InstancedMesh(pufG,std(0x15151a),nP);const beaks=new THREE.InstancedMesh(new THREE.ConeGeometry(.01,.025,4),new THREE.MeshBasicMaterial({color:0xff7a1a}),nP);root.add(puffins,beaks);
  const PF=Array.from({length:nP},(_,i)=>{const a=1.4+r()*2.3;const R=GJ.R*(1+.12*Math.sin(a*3+.7)+.07*Math.sin(a*7-1.1))-.15;return {a,R,fly:i<nP/4,ph:r()*6.283};});
  // ---- fish schools (instanced)
  const nF=low?24:60;const fish=new THREE.InstancedMesh(new THREE.ConeGeometry(.015,.06,4).rotateX(Math.PI/2),new THREE.MeshStandardMaterial({color:0xbfd8e6,emissive:0x22404a,metalness:.6,roughness:.3}),nF);fish.frustumCulled=false;root.add(fish);
  const FS=[{x:4.2,z:1.5},{x:-3.8,z:4.6},{x:3.2,z:-4.6}];let scare=0;
  let breach=-1,blowT=6,boatT=-1;const m4=new THREE.Matrix4(),q=new THREE.Quaternion(),e=new THREE.Euler(),v=new THREE.Vector3(),s1=new THREE.Vector3(1,1,1);
  const api={root,on:(f:(e:string)=>void)=>{listeners.push(f);},
    breach(){if(breach<0){breach=0;emit('breach');}},
    castoff(){if(boatT<0){boatT=0;emit('castoff');}},
    scare(){scare=2;},
    pickables:()=>[hitBoat,hitW],
    update(dt:number,t:number){const d=Math.min(.05,Math.max(0,dt||0));
      beam.rotation.y=t*.9;
      {const P=flagG.attributes.position as any;for(let i=0;i<P.count;i++){const x=flagBase[i*3];P.setZ(i,Math.sin(x*28-t*7)*.012*(x+.11)*8);}P.needsUpdate=true;}
      for(const h of horses){h.ph+=d*.15;const x=h.cx+Math.cos(h.ph)*.25,z=h.cz+Math.sin(h.ph*1.3)*.15;h.g.position.set(x,H(x,z),z);h.g.rotation.y=-h.ph+Math.PI/2;h.g.children[2].position.y=.18-Math.max(0,Math.sin(t*.7+h.ph*3))*.08;}
      bathers.forEach((b,i)=>{b.a+=d*.1;b.m.position.set(Lg.x+Math.cos(b.a)*b.rr*Lg.r,.065+Math.sin(t*1.5+i)*.006,Lg.z+Math.sin(b.a)*b.rr*Lg.r);});if(r()<d*2)puff(Lg.x+(r()-.5)*Lg.r,.08,Lg.z+(r()-.5)*Lg.r,0,0,.15,0,.6);
      tourists.forEach(tr=>{tr.u+=d*tr.sp*tr.dir;if(tr.u>1||tr.u<0){tr.dir*=-1;tr.u=Math.max(0,Math.min(1,tr.u));}const a=-.6+tr.u*1.55,R=.75;const x=G.x+Math.cos(a)*R,z=G.z+Math.sin(a)*R;tr.g.position.set(x,H(x,z)+.06,z);tr.g.rotation.y=-a+(tr.dir>0?0:Math.PI);});
      // boat: moored at the jetty until cast off, then one bay loop
      if(boatT>=0){boatT+=d;const bp=boatPose(boatT);boat.position.set(bp.x,GJ.sea+Math.sin(t*2)*.01,bp.z);boat.rotation.y=bp.heading;if(r()<.3)puff(bp.x,GJ.sea+.02,bp.z,2,0,.3,0,.25);if(r()<d*3)isl.splash(bp.x,bp.z,.06);if(boatT>34){boatT=-1;}}
      else{boat.position.set(J.x+.18,GJ.sea+Math.sin(t*1.6)*.008,J.z-.6);boat.rotation.y=0;}
      // whale: offshore circuit, blows every ~12 s, breach arc on demand
      let b=0;if(breach>=0){breach+=d/3.2;b=breach;if(breach>=1){breach=-1;b=0;const wp2=whalePose(t,0);isl.splash(wp2.x,wp2.z,.6);isl.tip(.5);for(let i=0;i<10;i++)puff(wp2.x,GJ.sea,wp2.z,2,(r()-.5)*1.4,1.5+r()*1.5,(r()-.5)*1.4,.4);emit('splash');}}
      const wp=whalePose(t,b);whale.position.set(wp.x,wp.y,wp.z);whale.rotation.set(wp.pitch,wp.heading,0,'YXZ');fluke.rotation.x=Math.sin(t*1.4)*.25;
      blowT-=d;if(blowT<=0&&b===0){blowT=10+r()*6;for(let i=0;i<8;i++)puff(wp.x,GJ.sea+.05,wp.z,2,(r()-.5)*.2,1.6+r()*.6,(r()-.5)*.2,.35);emit('blow');}
      // puffins
      PF.forEach((p,i)=>{let x,y,z;if(p.fly){p.ph+=d*.8;x=Math.cos(p.a+p.ph)*(p.R+.8);z=Math.sin(p.a+p.ph)*(p.R+.8);y=.9+Math.sin(p.ph*2)*.2;}else{x=Math.cos(p.a)*p.R;z=Math.sin(p.a)*p.R;y=Math.max(H(x,z),.35)+.03;}
        q.setFromEuler(e.set(0,-(p.a+(p.fly?p.ph:0)),0));m4.compose(v.set(x,y,z),q,s1);puffins.setMatrixAt(i,m4);v.x+=Math.cos(p.a+(p.fly?p.ph+1.57:0))*.025;m4.compose(v,q,s1);beaks.setMatrixAt(i,m4);});
      puffins.instanceMatrix.needsUpdate=true;beaks.instanceMatrix.needsUpdate=true;
      // fish schools circle under the surface; scatter on splashes / breaches
      scare=Math.max(0,scare-d);for(let i=0;i<nF;i++){const S=FS[i%3],k=Math.floor(i/3);const a=t*(.5+(i%3)*.1)+k*.7;const rr=.4+(k%5)*.07+scare*.5;const x=S.x+Math.cos(a)*rr,z=S.z+Math.sin(a)*rr,y=Math.max(GJ.bed+.08,-.2-(k%3)*.08);
        q.setFromEuler(e.set(0,-a,0));m4.compose(v.set(x,y,z),q,s1);fish.setMatrixAt(i,m4);}fish.instanceMatrix.needsUpdate=true;}};
  return api;
}
