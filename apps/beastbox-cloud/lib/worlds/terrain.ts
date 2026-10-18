// Home-world land (three side): chunked LOD heightfield (cage purples + glowing wireframe light layer),
// dense instanced forest of large trees on the hills, and explorable caves (mouth arch + walkable tunnel).
import {TERRAIN,CAVES,caveLocal,terrainHeight,forest} from './terrain-math.mjs';
type T=typeof import('three');
export function buildTerrain(THREE:T,scene:import('three').Scene,{low}:{low:boolean}){
  const root=new THREE.Group();root.name='home-terrain';scene.add(root);
  const U={uTime:{value:0}};
  // land reads through the cage fog: thinner fog (40% density, capped at 80%) only on terrain materials; the cage keeps its fog
  const landFog=(m:any)=>{m.onBeforeCompile=(sh:any)=>{sh.fragmentShader=sh.fragmentShader.replace('#include <fog_fragment>','#if defined(USE_FOG)&&defined(FOG_EXP2)\n float lfD=fogDensity*.4;float lfF=min(.8,1.0-exp(-lfD*lfD*vFogDepth*vFogDepth));gl_FragColor.rgb=mix(gl_FragColor.rgb,fogColor,lfF);\n#endif');};m.customProgramCacheKey=()=>'landfog';return m;};
  const land=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.95,metalness:.02,emissive:0x1a1038,emissiveIntensity:1.4,flatShading:true});landFog(land);
  const wire=new THREE.LineBasicMaterial({color:0x7af0ff,transparent:true,opacity:low?.26:.34,blending:THREE.AdditiveBlending,depthWrite:false});
  const S=TERRAIN.size,N=TERRAIN.chunks,cs=S/N,ca=new THREE.Color(0x2a2048),cb=new THREE.Color(0x4a3790),cc=new THREE.Color(0x7656c8);
  function chunkGeo(cx:number,cz:number,seg:number){const g=new THREE.PlaneGeometry(cs,cs,seg,seg);g.rotateX(-Math.PI/2);const P=g.attributes.position as any;const col=new Float32Array(P.count*3);
    for(let i=0;i<P.count;i++){const x=P.getX(i)+cx,z=P.getZ(i)+cz,r=Math.hypot(x,z);const y=r<TERRAIN.flatR-1?-.4:terrainHeight(x,z)-.12;P.setY(i,y);const k=Math.min(1,Math.max(0,y/18));const c=ca.clone().lerp(cb,Math.min(1,k*2)).lerp(cc,Math.max(0,k*2-1));col.set([c.r,c.g,c.b],i*3);}
    g.setAttribute('color',new THREE.BufferAttribute(col,3));g.computeVertexNormals();return g;}
  const lods:import('three').LOD[]=[];
  for(let i=0;i<N;i++)for(let j=0;j<N;j++){const cx=-S/2+cs*(i+.5),cz=-S/2+cs*(j+.5);if(Math.hypot(cx,cz)<cs*.5)continue;// centre chunk sits under the cage floor
    const lod=new THREE.LOD();lod.position.set(cx,0,cz);
    const hi=chunkGeo(cx,cz,low?TERRAIN.segLow:TERRAIN.segHigh),lo=chunkGeo(cx,cz,low?8:TERRAIN.segLow);
    const mHi=new THREE.Mesh(hi,land);const wHi=new THREE.LineSegments(new THREE.WireframeGeometry(lo),wire);mHi.add(wHi);
    const mLo=new THREE.Mesh(lo,land);lod.addLevel(mHi,0);lod.addLevel(mLo,low?45:70);lod.addLevel(new THREE.Object3D(),low?150:220);root.add(lod);lods.push(lod);}
  // ---- forest: instanced trunks + layered canopies + wire canopy shells (light layer)
  const trees=forest(low?TERRAIN.treesLow:TERRAIN.treesHigh);
  const trunkG=new THREE.CylinderGeometry(.06,.14,1,low?5:7);trunkG.translate(0,.5,0);
  const crownG=new THREE.IcosahedronGeometry(.5,low?0:1);
  const trunkM=new THREE.MeshStandardMaterial({color:0x2a1f45,roughness:1,emissive:0x0c0820});
  const crownM=new THREE.MeshStandardMaterial({color:0x2c6a78,roughness:.8,emissive:0x15607a,emissiveIntensity:1.1,flatShading:true});
  const crownW=new THREE.MeshBasicMaterial({color:0x9ff4ff,wireframe:true,transparent:true,opacity:.26,blending:THREE.AdditiveBlending,depthWrite:false});
  [wire,trunkM,crownM,crownW].forEach(landFog);
  const trunks=new THREE.InstancedMesh(trunkG,trunkM,trees.length),crowns=new THREE.InstancedMesh(crownG,crownM,trees.length*2),shells=low?null:new THREE.InstancedMesh(crownG,crownW,trees.length);
  const m4=new THREE.Matrix4(),q=new THREE.Quaternion(),e=new THREE.Euler(),v=new THREE.Vector3(),s=new THREE.Vector3();
  trees.forEach((t,i)=>{q.setFromEuler(e.set(0,t.rot,0));m4.compose(v.set(t.x,t.y-.1,t.z),q,s.set(t.s*.9,t.s,t.s*.9));trunks.setMatrixAt(i,m4);
    for(let k=0;k<2;k++){const cy=t.y+t.s*(.7+k*.32),cr=t.s*(.55-k*.17);m4.compose(v.set(t.x,cy,t.z),q,s.set(cr*1.25,cr,cr*1.25));crowns.setMatrixAt(i*2+k,m4);if(k===0&&shells){m4.compose(v.set(t.x,cy,t.z),q,s.set(cr*1.4,cr*1.15,cr*1.4));shells.setMatrixAt(i,m4);}}});
  [trunks,crowns,shells].forEach(m=>{if(!m)return;m.instanceMatrix.needsUpdate=true;m.computeBoundingSphere();root.add(m);});
  // ---- caves: dark tunnel interior (back faces) + glowing mouth arch + inner glow motes
  const caves=CAVES.map(c=>{const ux=Math.cos(c.a),uz=Math.sin(c.a);const pts:import('three').Vector3[]=[];for(let k=0;k<=8;k++){const sd=-.6+k/8*(c.len+.6);pts.push(new THREE.Vector3(ux*(c.r+sd),c.w*.9-.06-Math.max(0,sd)*.05,uz*(c.r+sd)));}
    const curve=new THREE.CatmullRomCurve3(pts);const tube=new THREE.Mesh(new THREE.TubeGeometry(curve,low?16:32,c.w*.95,low?8:14,false),new THREE.MeshStandardMaterial({color:0x140c26,emissive:new THREE.Color(c.color).multiplyScalar(.08),side:THREE.BackSide,roughness:1}) as any);tube.name=c.id;
    const arch=new THREE.Mesh(new THREE.TorusGeometry(c.w*1.02,.06,8,low?20:36,Math.PI*1.15),new THREE.MeshBasicMaterial({color:c.color,transparent:true,opacity:.85,blending:THREE.AdditiveBlending}));
    arch.position.set(ux*(c.r-.5),.25,uz*(c.r-.5));arch.lookAt(0,.25,0);arch.rotateZ(-Math.PI*.075);
        const g=new THREE.Group();g.add(tube,arch);root.add(g);return {c,g,arch};});
  // keep the cage floor feel: terrain edge hides under fog; nothing here touches the cage floor itself
  return {root,caves,trees,U,
    update(t:number,cam:import('three').Camera){U.uTime.value=t;for(const l of lods)l.update(cam);wire.opacity=(low?.26:.34)*(.8+.2*Math.sin(t*.6));for(const k of caves)(k.arch.material as any).opacity=.65+.25*Math.sin(t*1.7+k.c.a);},
    /** is p inside a cave tunnel (for mood: creatures get curious/creepy-quiet inside) */
    inCave(x:number,z:number){for(const c of CAVES){const L=caveLocal(c,x,z);if(L.s>0&&L.s<c.len&&Math.abs(L.t)<c.w)return c.id;}return null;},
    dispose(){scene.remove(root);root.traverse((o:any)=>{o.geometry?.dispose?.();o.material?.dispose?.();});}};
}
