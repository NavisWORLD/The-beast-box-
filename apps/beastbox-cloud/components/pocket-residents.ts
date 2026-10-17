import {ARTIST_RESIDENTS,residentView} from '../lib/companion/artist-residents.mjs';
import {loadResident3D} from './resident-3d';
import {loadBeastGlb} from './creature-glb-beast';
import RES_PAINTS from '../lib/creatures3d/resident-paints.json';
import {motionPersona,createActor,stepActor} from '../lib/companion/film-motion.mjs';
import {UNIVERSE_R} from '../lib/living-core/roam-brain.mjs';
import {RESIDENT_LC} from '../lib/living-core/creatures.js';
import {getLivingCore,stepLivingCore,livingCoreScale,fitLivingCoreParticles,LC_FLYERS,LC_WORLD_H} from '../lib/living-core/core-cache';
type Three=typeof import('three');
/** Cory's artist-drawn residents (no quantum seed). They are separate creatures and never the
 * player's active Beast, which stays rendered by the Cage arena in front of the pocket. */
export function addPocketResidents(THREE:Three,scene:import('three').Scene,seedRandom:()=>number,reduced:boolean,low=false,glbTier:'med'|'low'|null=low?null:'med',groundAt:(x:number,z:number)=>number=()=>0,lcOk=!reduced){
 /* Low tier (phones, software GL such as CI SwiftShader): sculpted GLBs (fur shells, coat shader) stay off so the
    main thread never starves; the visual-hull model / sprite render instead. ?beastglb=1 forces them for review. */
 const glbOk=!reduced&&(!!glbTier||(typeof location!=='undefined'&&new URLSearchParams(location.search).get('beastglb')==='1'));
    const loader=new THREE.TextureLoader(),texCache=new Map<string,import('three').Texture>();
    const tex=(src:string)=>{let t=texCache.get(src);if(!t){t=loader.load(src);t.colorSpace=THREE.SRGBColorSpace;texCache.set(src,t);}return t;};
    let lcQueue:Promise<any>=Promise.resolve();
    const residents=ARTIST_RESIDENTS.map((r,i)=>{
     const mat=new THREE.SpriteMaterial({map:tex(r.views.front),transparent:true,depthWrite:false});
     const sprite=new THREE.Sprite(mat);const h=.95*r.scale;sprite.scale.set(h,h,1);sprite.name=r.id;
     const shadow=new THREE.Mesh(new THREE.CircleGeometry(.32*r.scale,20),new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:.32,depthWrite:false}));
     shadow.rotation.x=-Math.PI/2;shadow.position.y=-.03;scene.add(sprite);scene.add(shadow);
     // Film motion: artist-drawn → no quantum seed, so the persona comes from the resident's own id only.
     const home=(i/ARTIST_RESIDENTS.length)*Math.PI*2+.6,hr=r.kind==='trainer'?2.2:2.8;
     const actor=createActor(motionPersona({id:r.id}),{x:Math.cos(home)*hr,z:Math.sin(home)*hr*.85,radius:.9,seed:r.id,universe:UNIVERSE_R});
     const slot:{mesh:any;glb:any;foot:number;lc?:any;lcName?:string;lcK?:number}={mesh:null,glb:null,foot:0};
     // Zeref-pipeline sculpted resident GLB (Oct 15) with its artist palette + props; the visual-hull model / sprite stay as fallback.
     const stub=(RES_PAINTS as any[]).find(x=>x.body==='res_'+r.id.replace('art-',''));
     const hull=()=>loadResident3D(THREE,r.id).then(m=>{if(!m)return;slot.mesh=m;scene.add(m);sprite.visible=false;});
     // Oct 16 living-core rollout: residents with a living-core config get the true-3D body (built one at a time,
     // cached); GLB / visual hull / sprite stay as the fallback chain.
     const lcName=(RESIDENT_LC as Record<string,string>)[r.id];
     const legacy=()=>{if(stub&&glbOk)void loadBeastGlb(THREE,stub,{tier:glbTier||'med',paint:stub.paint}).then(gb=>{if(!gb){void hull();return;}slot.glb=gb;gb.root.scale.setScalar(.95*r.scale);gb.root.updateMatrixWorld(true);slot.foot=-new THREE.Box3().setFromObject(gb.root).min.y;slot.mesh=gb.root;gb.root.userData.glb=true;scene.add(gb.root);sprite.visible=false;}).catch(()=>void hull());else void hull();};
     if(lcName&&lcOk){lcQueue=lcQueue.catch(()=>{}).then(()=>getLivingCore(THREE,lcName)).then(({LC})=>{const root=new THREE.Group();const body=new THREE.Group();const k=livingCoreScale(LC,LC_WORLD_H*Math.min(1.2,Math.max(.85,r.scale)));body.scale.setScalar(k);fitLivingCoreParticles(LC,k,700);body.position.y=-LC.footY*k;body.add(LC.group);root.add(body);if(LC.shadow)root.add(LC.shadow);root.name=r.id+'-living-core';scene.add(root);slot.lc=LC;slot.lcName=lcName;slot.lcK=k;slot.mesh=root;sprite.visible=false;shadow.visible=false;}).catch(()=>legacy());}
     else legacy();
     return {r,sprite,shadow,h,actor,slot,phase:i*1.37+seedRandom()*2,radius:r.kind==='trainer'?2.2:2.7+seedRandom()*1.1,speed:(r.kind==='trainer'?.05:.09+seedRandom()*.06)*(i%2?1:-1),src:r.views.front,x:0,z:0};
    });
    let lastT=0;
    const stepResidents=(t:number,theta:number,cam?:{x:number;z:number},beast?:{x:number;z:number;moment?:string|null}|null)=>{
     // creature-to-creature moments: the resident the Beast greets / tussles with / follows turns to it (and backs off a little in a tussle)
     let meet=-1;if(beast?.moment&&beast.moment!=='splash'&&beast.moment!=='to-nap-spot'){let bd=1.3;residents.forEach((a,i)=>{const d=Math.hypot(a.x-beast.x,a.z-beast.z);if(d<bd){bd=d;meet=i;}});}
     const dt=Math.max(0,Math.min(.05,t-lastT));lastT=t;
     residents.forEach((a,i)=>{
      // Curious ones turn to the camera; the others turn toward the creature at the habitat centre.
      const look=i===meet&&beast?beast:i%2===0&&cam?cam:{x:0,z:0};if(i===meet&&beast&&a.actor){(a.actor as any).target={x:a.x+(a.x-beast.x)*(beast.moment==='play-fight'?.4:.05),z:a.z+(a.z-beast.z)*(beast.moment==='play-fight'?.4:.05)};}
      const p=stepActor(a.actor,reduced?0:dt,{lookAt:look,reduced});a.x=p.x;a.z=p.z;
      const hy=a.h*p.sy;const gy=groundAt(p.x,p.z);a.sprite.position.set(p.x,gy+hy/2+p.lift,p.z);a.shadow.position.set(p.x,gy+.005,p.z);
      a.shadow.scale.setScalar(1-Math.min(.5,p.lift*.9));
      const view=residentView(a.r,p.heading+p.head,theta);const m=a.sprite.material;
      if(view.src!==a.src){m.map=tex(view.src);m.needsUpdate=true;a.src=view.src;}
      a.sprite.scale.set(a.h*p.sx*(view.flip?-1:1),hy,1);m.rotation=-p.lean*(view.flip?-1:1);
      const gb=a.slot.glb;if(gb){gb.drive(reduced?0:dt,{speed:Math.min(1,Math.hypot(p.x-(a as any).px||0,p.z-(a as any).pz||0)/Math.max(dt,1e-3)),mode:'wander',sleep:0,lookCam:0,bob:t*6,heading:p.heading},null,null);(a as any).px=p.x;(a as any).pz=p.z;
       gb.root.position.set(p.x,gy+a.slot.foot+p.lift,p.z);gb.root.scale.setScalar(.95*a.r.scale);gb.root.rotation.set(0,p.heading+p.head,0);}
      if(a.slot.lc){const L=a.slot.lc,fly=LC_FLYERS.includes(a.slot.lcName||'');const hover=fly?.55+Math.sin(t*1.1*Math.PI*2*.35)*.08:0;
       a.slot.mesh.position.set(p.x,gy+p.lift+hover,p.z);a.slot.mesh.rotation.set(0,p.heading+p.head,0);// Near-camera cap: a resident walking right up to the lens shrinks a little so it never fills the pocket.
       const camD=cam?Math.hypot(p.x-cam.x,p.z-cam.z):9,near=Math.min(1,Math.max(.5,(camD-2.5)/4))*(a.slot.lcName==="kittenref"?.8:1);const kk=a.slot.lcK!*near;a.slot.mesh.children[0].scale.set(kk*p.sx,kk*p.sy,kk*p.sx);
       const sp=Math.hypot(p.x-((a as any).lx??p.x),p.z-((a as any).lz??p.z))/Math.max(dt,1e-3);(a as any).lx=p.x;(a as any).lz=p.z;
       const mood=i===meet&&beast?.moment==='play-fight'?'angry':i===meet?'happy':sp>.6?'happy':p.lift>.02?'happy':(Math.sin(t*.07+i*2)>.85?'curious':Math.sin(t*.05+i)>.92?'sleepy':'calm');
       if((a as any).mood!==mood){(a as any).mood=mood;L.setEmotion?.(mood);}stepLivingCore(L,reduced?0:dt);a.sprite.visible=false;return;}
      const mesh=gb?null:a.slot.mesh;if(mesh){mesh.position.set(p.x,gy+p.lift,p.z);const k=a.h*1.55;mesh.scale.set(k*p.sx,k*p.sy,k*p.sx);mesh.rotation.set(p.lean,p.heading+p.head,0,'YXZ');}
     });
    };
    const disturbers=()=>residents.map(a=>({x:a.x,z:a.z,r:.75*a.r.scale,s:2.4,id:a.r.id}));
    // Tap-to-focus targets: the 3D mesh once loaded, else the sprite.
    const pickables=()=>residents.map(a=>({id:a.r.id,obj:(a.slot.mesh??a.sprite) as import('three').Object3D}));
    if(typeof window!=='undefined')(window as any).__lcResidents=residents;// lets roamers visit each other's spots
    return {stepResidents,texCache,disturbers,pickables};
}
