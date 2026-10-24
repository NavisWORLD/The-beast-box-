// Ocean life renderer for the pocket world (Oct 24 2026). Positions come from ocean-life.mjs (seeded from the recorded IBM genesis seed).
// Shown at the water surface (the sea is opaque): silver fish glints, ray silhouettes under the surface, whale backs with spouts, plankton glow at night.
// Procedural placeholders, no art: if Cosmo's pack ships fish/ray/whale models, swap the meshes here.
import {oceanLife,memberAt,headingAt,surfacing,planktonGlow} from './ocean-life.mjs';
type T=typeof import('three');
export function addOceanLife(THREE:T,scene:import('three').Scene,o:{seed:string;R:number;mpu:number;isWater:(n:number[])=>boolean;phone:boolean;life?:number}){
 const data=oceanLife(o.seed,o.isWater,{life:(o.life??1)*(o.phone?.6:1),plankton:o.phone?160:320});
 const group=new THREE.Group();group.name='ocean-life';scene.add(group);const R=o.R,m=o.mpu;
 const dot=(()=>{const c=document.createElement('canvas');c.width=c.height=32;const g=c.getContext('2d')!;const gr=g.createRadialGradient(16,16,0,16,16,16);gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(.4,'rgba(255,255,255,.55)');gr.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=gr;g.fillRect(0,0,32,32);return new THREE.CanvasTexture(c);})();
 const fish=data.schools.filter(s=>s.kind==='fish'),rays=data.schools.filter(s=>s.kind==='ray'),whales=data.schools.filter(s=>s.kind==='whale');
 const nF=fish.reduce((a,s)=>a+s.count,0);const fp=new Float32Array(nF*3);const fg=new THREE.BufferGeometry();fg.setAttribute('position',new THREE.BufferAttribute(fp,3));
 const fishPts=new THREE.Points(fg,new THREE.PointsMaterial({map:dot,color:0xdff3ff,size:.09,sizeAttenuation:true,transparent:true,opacity:.95,depthWrite:false}));fishPts.frustumCulled=false;group.add(fishPts);
 const nP=data.plankton.length;const pp=new Float32Array(nP*3),pc=new Float32Array(nP*3);data.plankton.forEach((p,i)=>{pp.set([p.n[0]*(R+.01),p.n[1]*(R+.01),p.n[2]*(R+.01)],i*3);});
 const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(pp,3));pg.setAttribute('color',new THREE.BufferAttribute(pc,3));
 const plank=new THREE.Points(pg,new THREE.PointsMaterial({map:dot,vertexColors:true,size:.16,sizeAttenuation:true,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));plank.frustumCulled=false;group.add(plank);
 const rayShape=new THREE.Shape();rayShape.moveTo(.5,0);rayShape.quadraticCurveTo(.1,.62,-.28,.5);rayShape.lineTo(-.18,.04);rayShape.lineTo(-1,0);rayShape.lineTo(-.18,-.04);rayShape.lineTo(-.28,-.5);rayShape.quadraticCurveTo(.1,-.62,.5,0);
 const rayGeo=new THREE.ShapeGeometry(rayShape);const rayMesh=rays.map(s=>{const mm=new THREE.Mesh(rayGeo,new THREE.MeshBasicMaterial({color:0x1d3b52,transparent:true,opacity:.6,depthWrite:false,side:THREE.DoubleSide}));mm.scale.setScalar(s.size*m*3);mm.frustumCulled=false;group.add(mm);return mm;});
 const whaleGeo=new THREE.SphereGeometry(1,18,12);const whaleMesh=whales.map(s=>{const mm=new THREE.Mesh(whaleGeo,new THREE.MeshStandardMaterial({color:0x2d3d58,roughness:.45,metalness:.05}));mm.scale.set(s.size*.5,s.size*.11,s.size*.14);mm.frustumCulled=false;group.add(mm);return mm;});
 const spN=14;const sp=whales.map(()=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(spN*3),3));const p=new THREE.Points(g,new THREE.PointsMaterial({map:dot,color:0xeaf8ff,size:.12,sizeAttenuation:true,transparent:true,opacity:.8,depthWrite:false}));p.frustumCulled=false;group.add(p);return p;});
 const V=(a:number[])=>new THREE.Vector3(a[0],a[1],a[2]);const mx=new THREE.Matrix4();let near=0;
 function update(t:number,s:{night:number;camPos?:import('three').Vector3}){
  let k=0;for(const sc of fish)for(let i=0;i<sc.count;i++){const p=memberAt(sc,i,t);const h=R+.012+.004*Math.sin(t*3+i);fp[k++]=p[0]*h;fp[k++]=p[1]*h;fp[k++]=p[2]*h;}(fg.attributes.position as any).needsUpdate=true;
  rays.forEach((sc,j)=>{const p=memberAt(sc,0,t),h=headingAt(sc,0,t);const n=V(p),hv=V(h),sd=new THREE.Vector3().crossVectors(n,hv);mx.makeBasis(hv,sd,n);rayMesh[j].quaternion.setFromRotationMatrix(mx);rayMesh[j].position.copy(n).multiplyScalar(R+.006+.003*Math.sin(t*.8+j));});
  whales.forEach((sc,j)=>{const p=memberAt(sc,0,t),h=headingAt(sc,0,t);const n=V(p),hv=V(h);const zv=new THREE.Vector3().crossVectors(hv,n);mx.makeBasis(hv,n,zv);whaleMesh[j].quaternion.setFromRotationMatrix(mx);
   const su=surfacing(sc,t);whaleMesh[j].position.copy(n).multiplyScalar(R-sc.size*.05+su*sc.size*.05+.02*Math.sin(t*.6+j));
   const pa=(sp[j].geometry.attributes.position as any);const base=n.clone().multiplyScalar(R+sc.size*.02).addScaledVector(hv,sc.size*.2);for(let q=0;q<spN;q++){const f=(q/spN);const rise=su*(.15+.5*f)*sc.size*.5;const sp2=su*Math.sin(q*2.4+t*4)*.05*sc.size;pa.setXYZ(q,base.x+n.x*rise+hv.x*sp2,base.y+n.y*rise+hv.y*sp2,base.z+n.z*rise+hv.z*sp2);}pa.needsUpdate=true;(sp[j].material as any).opacity=Math.min(.85,su*1.2);});
  const pcA=pg.attributes.color as any;let lit=0;for(let i=0;i<nP;i++){const gl=planktonGlow(data.plankton[i].p,t,s.night);if(gl>.05)lit++;pc[i*3]=.2*gl;pc[i*3+1]=1*gl;pc[i*3+2]=.78*gl;}pcA.needsUpdate=true;near=lit;}
 return {data,group,update,state:()=>({label:data.label,fish:nF,schools:fish.length,rays:rays.length,whales:whales.length,plankton:nP,lit:near}),dispose:()=>{scene.remove(group);[fg,pg,rayGeo,whaleGeo].forEach(g=>g.dispose());dot.dispose();}};}
