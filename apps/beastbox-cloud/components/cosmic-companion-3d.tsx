'use client';
import {stageRig,stageTimeOfHour,dirFromCam,STAGE_FLOOR} from '../lib/universe/open-stage-rig.mjs';
import {useUniverseMotion} from './use-universe-motion';
import {useEffect,useRef,useState} from 'react';
import {type CreatureProfile,validCreature} from '../lib/creature-profile';
import {createCreatureRig} from '../lib/creature-model';
import {buildDimensionalRig,dimensionalKind,poseDimensional} from '../lib/creature-dimensional.mjs';
import PixelBeast from './pixel-beast';

export type CreatureState='idle'|'listening'|'observing'|'thinking'|'remembering'|'celebrating'|'sleeping'|'halted';
export type CreatureLook='nebula'|'aurora'|'starlight';
type Props={state?:CreatureState;look?:CreatureLook;intensity?:number;quality?:'auto'|'low';className?:string;label?:string;turntable?:boolean;turntableAngle?:number|null;profile?:CreatureProfile|null;paused?:boolean;spriteGenome?:{seed?:string;facing?:string}|null;spriteStage?:number;spriteName?:string;spriteId?:string;preferSprite?:boolean;dimensionalId?:string|null;speaking?:boolean};

/**
 * Original procedural 3D model. All animation is VISUAL; inferred feelings,
 * intelligence growth and real sensor measurements are never generated here.
 * The user-provided concept art is a reference, not a downloaded texture.
 */
export default function CosmicCompanion3D({state='idle',look='nebula',intensity=0,quality='auto',className='',label='Cosmic companion',turntable=false,turntableAngle=null,profile=null,paused=false,spriteGenome=null,spriteStage=1,spriteName='',spriteId='',preferSprite=false,dimensionalId=null,speaking=false}:Props){
 const canvas=useRef<HTMLCanvasElement>(null);
 const stateRef=useRef(state),intensityRef=useRef(0),pausedRef=useRef(paused),speakingRef=useRef(speaking);
 const rotationRef=useRef({turntable,angle:turntableAngle});
 const boundKind=dimensionalKind({id:dimensionalId||''});
 useEffect(()=>{rotationRef.current={turntable,angle:typeof turntableAngle==='number'&&Number.isFinite(turntableAngle)?turntableAngle:null};},[turntable,turntableAngle]);
 const [ready,setReady]=useState(false),[fallback,setFallback]=useState(false);
 const {reduced}=useUniverseMotion();
 useEffect(()=>{stateRef.current=state;},[state]);
 useEffect(()=>{pausedRef.current=paused;},[paused]);
 useEffect(()=>{speakingRef.current=speaking;},[speaking]);
 useEffect(()=>{intensityRef.current=Number.isFinite(intensity)?Math.min(1,Math.max(0,intensity)):0;},[intensity]);
 useEffect(()=>{
  const element=canvas.current;
  if(!element||fallback||preferSprite||typeof window.WebGLRenderingContext==='undefined')return;
  if(reduced&&!boundKind)return;
  let disposed=false,animation=0,rendererCleanup=()=>{};
  void (async()=>{
   try{
    const THREE=await import('three');
    if(disposed)return;
    const renderer=new THREE.WebGLRenderer({canvas:element,alpha:true,antialias:quality!=='low',powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(quality==='low'?1:1.5,window.devicePixelRatio||1));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1.45;
    const dimensional0=!!boundKind;
    const scene=new THREE.Scene();
    const camera=new THREE.PerspectiveCamera(35,1,.1,50);
    camera.position.set(0,0,7.6);
    // Look Closer / turntable: Cosmo's open-stage key / fill / rim / hemisphere (SEEDED look, picked by the local hour). Everywhere else keeps its old lights.
    const stageLit=!!(rotationRef.current.turntable||rotationRef.current.angle!==null);
    if(stageLit){
     const rigT=stageRig('thick',stageTimeOfHour(new Date().getHours()+new Date().getMinutes()/60)),tgt=dimensional0?new THREE.Vector3(0,.95,0):new THREE.Vector3(0,.05,0);
     renderer.toneMappingExposure=Math.max(rigT.exposure>0?rigT.exposure*1.2:1.2,rigT.floor>=1.5?1.7:0);
     scene.add(new THREE.HemisphereLight(new THREE.Color(rigT.hemi.sky),new THREE.Color(rigT.hemi.ground),rigT.hemi.i*1.6));
     if(rigT.floor>0)scene.add(new THREE.AmbientLight(new THREE.Color(STAGE_FLOOR.colour),rigT.floor));
     for(const k of ['key','fill','rim'] as const){const l=rigT[k],d=dirFromCam(l.az,l.el);const light=new THREE.DirectionalLight(new THREE.Color(l.hex),l.i);light.position.set(tgt.x+d[0]*6,tgt.y+d[1]*6,tgt.z+d[2]*6);light.target.position.copy(tgt);scene.add(light,light.target);}
    }else{
    scene.add(new THREE.AmbientLight(0xaacfff,1.5));
    const warm=new THREE.PointLight(0xffd6ef,30,14);warm.position.set(-2.1,2.5,3.4);scene.add(warm);
    const rim=new THREE.PointLight(0x7fffff,34,13);rim.position.set(2,-1,-2);scene.add(rim);
    }
    const dimensional=boundKind?buildDimensionalRig(THREE,boundKind,{quality}):null;
    const rig=dimensional?{group:dimensional.root,dispose:()=>dimensional.dispose(),dimensional}:{...createCreatureRig(profile,look,quality),dimensional:null};
    const {group:creature,body,bodyMaterial,fins,halo,motes}=rig.dimensional?{group:rig.group,body:null,bodyMaterial:null,fins:[],halo:null,motes:null}:rig;
    scene.add(creature);
    if(dimensional){camera.position.set(0.15,1.05,4.35);camera.lookAt(0,0.95,0);}
    // Living Cosmos depth polish: grounded contact shadow + soft back glow, slight low-angle perspective.
    const bounds=new THREE.Box3().setFromObject(creature);
    const shadowTex=(()=>{const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d');if(g){const r=g.createRadialGradient(32,32,2,32,32,32);r.addColorStop(0,'rgba(4,2,16,.62)');r.addColorStop(1,'rgba(4,2,16,0)');g.fillStyle=r;g.fillRect(0,0,64,64);}return new THREE.CanvasTexture(c);})();
    const shadow=new THREE.Mesh(new THREE.PlaneGeometry(2.6,1.1),new THREE.MeshBasicMaterial({map:shadowTex,transparent:true,depthWrite:false}));
    shadow.rotation.x=-Math.PI/2;shadow.position.y=Number.isFinite(bounds.min.y)?bounds.min.y-.04:-1.3;scene.add(shadow);
    const glowTex=(()=>{const c=document.createElement('canvas');c.width=c.height=128;const g=c.getContext('2d');if(g){const r=g.createRadialGradient(64,64,0,64,64,64);r.addColorStop(0,'rgba(107,79,216,1)');r.addColorStop(.55,'rgba(107,79,216,.45)');r.addColorStop(1,'rgba(107,79,216,0)');g.fillStyle=r;g.fillRect(0,0,128,128);}return new THREE.CanvasTexture(c);})();
    const backGlow=new THREE.Mesh(new THREE.PlaneGeometry(3.8,3.8),new THREE.MeshBasicMaterial({map:glowTex,transparent:true,opacity:.34,depthWrite:false,blending:THREE.AdditiveBlending}));
    backGlow.position.set(0,.1,-1.6);scene.add(backGlow);
    if(!dimensional){camera.position.set(0,-.35,7.6);camera.lookAt(0,.05,0);}
    // Look Closer (Cosmo's open-stage pack): 46 degree lens, pulled in so the creature keeps its size; the turntable starts three-quarter, never edge-on.
    if(rotationRef.current.turntable||rotationRef.current.angle!==null){const tg=dimensional?new THREE.Vector3(0,.95,0):new THREE.Vector3(0,.05,0);camera.fov=46;camera.position.sub(tg).multiplyScalar(Math.tan(17.5*Math.PI/180)/Math.tan(23*Math.PI/180)).add(tg);camera.lookAt(tg);camera.updateProjectionMatrix();}
    const onLost=(event:Event)=>{event.preventDefault();cancelAnimationFrame(animation);setReady(false);setFallback(true);};
    element.addEventListener('webglcontextlost',onLost);
    const resize=()=>{
     if(disposed)return;
     const rect=element.getBoundingClientRect();
     if(rect.width<1||rect.height<1)return;
     const w=Math.max(1,Math.floor(rect.width)),h=Math.max(1,Math.floor(rect.height));
     renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
    };
    const observer=new ResizeObserver(resize);observer.observe(element);resize();
    let prev=performance.now(),lastPaint=0,velocity=0,energy=0,bodyHeight=0,rendered=false,turntablePhase=rotationRef.current.turntable?35*Math.PI/180:0,motionTime=0;
    const animate=(now:number)=>{
     if(disposed||document.hidden)return;
     const dt=Math.min((now-prev)/1000,.07);prev=now;
     animation=requestAnimationFrame(animate);
     if(pausedRef.current&&rendered)return;
     if(now-lastPaint<(quality==='low'?66:34))return;
     lastPaint=now;
     if(!pausedRef.current)motionTime+=dt;
     const mood=stateRef.current;
     const desired=mood==='halted'||mood==='sleeping'?0:intensityRef.current;
     energy+=((desired-energy)*Math.min(1,dt*5));
     const target=mood==='thinking'?.09:mood==='listening'?.08+energy*.17:mood==='celebrating'?.21:mood==='sleeping'?-.16:0;
     velocity+=(target-bodyHeight)*dt*15;
     velocity*=Math.exp(-dt*5);
     bodyHeight+=velocity*dt;
     const t=motionTime;
     if(rig.dimensional){
      poseDimensional(rig.dimensional,{state:mood,time:t,reduced,speaking:speakingRef.current});
      if(rotationRef.current.turntable)turntablePhase=(turntablePhase+dt*Math.PI/4)%(Math.PI*2);
      rig.dimensional.root.rotation.y=rotationRef.current.turntable?turntablePhase:rotationRef.current.angle!==null?rotationRef.current.angle*Math.PI/180:0;
      try{renderer.render(scene,camera);}catch{cancelAnimationFrame(animation);if(!disposed){setReady(false);setFallback(true);}return;}
      if(!rendered){rendered=true;setReady(true);}
      if(reduced){cancelAnimationFrame(animation);animation=0;return;}
      return;
     }
     const cosmicBody=body!,cosmicHalo=halo!,cosmicMotes=motes!,cosmicMaterial=bodyMaterial!;
     creature.position.y=bodyHeight+(mood==='sleeping'?0:Math.sin(t*1.25)*.07);
     // Actual geometry turntable: no fake interpolated 2D views. Pause respects reduced-motion.
     if(rotationRef.current.turntable)turntablePhase=(turntablePhase+dt*Math.PI/4)% (Math.PI*2);
     creature.rotation.y=rotationRef.current.turntable?turntablePhase:
      rotationRef.current.angle!==null?rotationRef.current.angle*Math.PI/180:
      Math.sin(t*.42)*.13+(mood==='observing'?.16:0);
     creature.rotation.z=Math.sin(t*.73)*.055;
     shadow.scale.setScalar(1-Math.min(.25,Math.max(0,creature.position.y)*.9));
     cosmicBody.scale.y=.99+energy*.08+(mood==='thinking'?.034*Math.sin(t*4):0);
     cosmicHalo.rotation.y=t*.57;
     fins.forEach((p,i)=>{p.rotation.z=-i*Math.PI*2/fins.length+Math.sin(t*1.4+i*.82)*(.04+energy*.06);});
     cosmicMotes.rotation.y=t*.046;
     cosmicMaterial.emissiveIntensity=.2+energy*.35+(mood==='thinking'?.1:0);
     // Runtime GL failures (not only constructor/context loss) must reveal the
     // same creature's 2D representation instead of leaving a blank canvas.
     try{renderer.render(scene,camera);}catch{
      cancelAnimationFrame(animation);
      if(!disposed){setReady(false);setFallback(true);}
      return;
     }
     if(!rendered){rendered=true;setReady(true);}
    };
    const visibility=()=>{if(!document.hidden&&!disposed){prev=performance.now();cancelAnimationFrame(animation);animation=requestAnimationFrame(animate);}else cancelAnimationFrame(animation);};
    document.addEventListener('visibilitychange',visibility);
    animation=requestAnimationFrame(animate);
    rendererCleanup=()=>{
     cancelAnimationFrame(animation);
     observer.disconnect();document.removeEventListener('visibilitychange',visibility);
     element.removeEventListener('webglcontextlost',onLost);
     rig.dispose();
     shadow.geometry.dispose();(shadow.material as import('three').Material).dispose();shadowTex.dispose();glowTex.dispose();backGlow.geometry.dispose();(backGlow.material as import('three').Material).dispose();
     renderer.dispose();
    };
   }catch{
    if(!disposed){setFallback(true);setReady(false);}
   }
  })();
  return()=>{disposed=true;rendererCleanup();};
 },[look,quality,reduced,fallback,preferSprite,profile,boundKind,dimensionalId]);
 const selected=profile&&validCreature(profile)?profile:null;
 const activeSprite=spriteGenome&&typeof spriteGenome.seed==='string'&&spriteGenome.seed.length>0?spriteGenome:null;
 const showSprite=Boolean(activeSprite)&&!boundKind&&(preferSprite||fallback||reduced||!ready);
 const earnedStage=Number.isFinite(spriteStage)?Math.max(1,Math.min(3,Math.floor(spriteStage))):1;
 const appearance=(selected?`hue-rotate(${selected.appearance.hueShift}deg) brightness(${.7+selected.appearance.glow/200})`:look==='aurora'?'hue-rotate(42deg)':look==='starlight'?'saturate(.68) brightness(1.18)':'none');
 return <div className={'cosmic-creature3d '+className} aria-label={label} data-creature-state={state} data-graphics={showSprite?'qbeast-sprite':ready?(boundKind?'dimensional-3d':'procedural-3d'):boundKind?'dimensional-fallback':'illustration'} data-motion={paused?'paused':reduced?'reduced':'active'} data-creature-id={boundKind?(dimensionalId||'preview'):showSprite&&spriteId?spriteId:(selected?.id??'preview')} data-dimensional-kind={boundKind||'none'} data-phenotype={boundKind?'artistic-representation':'procedural-cosmetic'} data-cosmetic-hue={selected?.appearance.hueShift??0}>
  {boundKind?null:<img className={'cosmic-creature-fallback '+(ready&&!reduced?'hidden':'')} src="/cosmic-creature.svg" alt="" style={{filter:appearance}}/>}
  {showSprite&&activeSprite?<div className="cosmic-creature-pixel" data-fallback="same-qbeast-sprite"><PixelBeast genome={activeSprite} stage={earnedStage} publicSpark pose={paused||reduced?'idle':state==='sleeping'?'emote':state==='celebrating'?'react':'idle'} emote={state==='sleeping'?'sleep':state==='celebrating'?'spark':'watch'} reduced={paused||reduced} label={`${spriteName||label} · same recorded-seed sprite, form ${earnedStage}`}/></div>:null}
  {(boundKind||!reduced)&&!fallback&&!preferSprite?<canvas ref={canvas} className="cosmic-creature-canvas" aria-hidden="true"/>:null}
 </div>;
}
