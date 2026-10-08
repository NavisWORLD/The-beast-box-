'use client';
import {useEffect,useRef,useState} from 'react';
import {type CreatureProfile,validCreature} from '../lib/creature-profile';
import {createCreatureRig} from '../lib/creature-model';
import PixelBeast from './pixel-beast';

export type CreatureState='idle'|'listening'|'observing'|'thinking'|'remembering'|'celebrating'|'sleeping'|'halted';
export type CreatureLook='nebula'|'aurora'|'starlight';
type Props={state?:CreatureState;look?:CreatureLook;intensity?:number;quality?:'auto'|'low';className?:string;label?:string;turntable?:boolean;turntableAngle?:number|null;profile?:CreatureProfile|null;paused?:boolean;spriteGenome?:{seed?:string;facing?:string}|null;spriteStage?:number;spriteName?:string;preferSprite?:boolean};

/**
 * Original procedural 3D model. All animation is VISUAL; inferred feelings,
 * intelligence growth and real sensor measurements are never generated here.
 * The user-provided concept art is a reference, not a downloaded texture.
 */
export default function CosmicCompanion3D({state='idle',look='nebula',intensity=0,quality='auto',className='',label='Cosmic companion',turntable=false,turntableAngle=null,profile=null,paused=false,spriteGenome=null,spriteStage=1,spriteName='',preferSprite=false}:Props){
 const canvas=useRef<HTMLCanvasElement>(null);
 const stateRef=useRef(state),intensityRef=useRef(0),pausedRef=useRef(paused);
 const rotationRef=useRef({turntable,angle:turntableAngle});
 useEffect(()=>{rotationRef.current={turntable,angle:typeof turntableAngle==='number'&&Number.isFinite(turntableAngle)?turntableAngle:null};},[turntable,turntableAngle]);
 const [ready,setReady]=useState(false),[fallback,setFallback]=useState(false);
 const [reduced,setReduced]=useState(false);
 useEffect(()=>{stateRef.current=state;},[state]);
 useEffect(()=>{pausedRef.current=paused;},[paused]);
 useEffect(()=>{intensityRef.current=Number.isFinite(intensity)?Math.min(1,Math.max(0,intensity)):0;},[intensity]);
 useEffect(()=>{
  const query=window.matchMedia('(prefers-reduced-motion: reduce)');
  const update=()=>setReduced(query.matches);
  update();query.addEventListener('change',update);
  return()=>query.removeEventListener('change',update);
 },[]);
 useEffect(()=>{
  const element=canvas.current;
  if(!element||reduced||fallback||preferSprite||typeof window.WebGLRenderingContext==='undefined')return;
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
    const scene=new THREE.Scene();
    const camera=new THREE.PerspectiveCamera(35,1,.1,50);
    camera.position.set(0,0,7.6);
    scene.add(new THREE.AmbientLight(0xaacfff,1.5));
    const warm=new THREE.PointLight(0xffd6ef,30,14);warm.position.set(-2.1,2.5,3.4);scene.add(warm);
    const rim=new THREE.PointLight(0x7fffff,34,13);rim.position.set(2,-1,-2);scene.add(rim);
    const rig=createCreatureRig(profile,look,quality);
    const {group:creature,body,bodyMaterial,fins,halo,motes}=rig;
    scene.add(creature);
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
    let prev=performance.now(),lastPaint=0,velocity=0,energy=0,bodyHeight=0,rendered=false,turntablePhase=0,motionTime=0;
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
     creature.position.y=bodyHeight+(mood==='sleeping'?0:Math.sin(t*1.25)*.07);
     // Actual geometry turntable: no fake interpolated 2D views. Pause respects reduced-motion.
     if(rotationRef.current.turntable)turntablePhase=(turntablePhase+dt*Math.PI/4)% (Math.PI*2);
     creature.rotation.y=rotationRef.current.turntable?turntablePhase:
      rotationRef.current.angle!==null?rotationRef.current.angle*Math.PI/180:
      Math.sin(t*.42)*.13+(mood==='observing'?.16:0);
     creature.rotation.z=Math.sin(t*.73)*.055;
     body.scale.y=.99+energy*.08+(mood==='thinking'?.034*Math.sin(t*4):0);
     halo.rotation.y=t*.57;
     fins.forEach((p,i)=>{p.rotation.z=-i*Math.PI*2/fins.length+Math.sin(t*1.4+i*.82)*(.04+energy*.06);});
     motes.rotation.y=t*.046;
     bodyMaterial.emissiveIntensity=.2+energy*.35+(mood==='thinking'?.1:0);
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
     renderer.dispose();
    };
   }catch{
    if(!disposed){setFallback(true);setReady(false);}
   }
  })();
  return()=>{disposed=true;rendererCleanup();};
 },[look,quality,reduced,fallback,preferSprite,profile]);
 const selected=profile&&validCreature(profile)?profile:null;
 const activeSprite=spriteGenome&&typeof spriteGenome.seed==='string'&&spriteGenome.seed.length>0?spriteGenome:null;
 const showSprite=Boolean(activeSprite)&&(preferSprite||fallback||reduced||!ready);
 const earnedStage=Number.isFinite(spriteStage)?Math.max(1,Math.min(3,Math.floor(spriteStage))):1;
 const appearance=(selected?`hue-rotate(${selected.appearance.hueShift}deg) brightness(${.7+selected.appearance.glow/200})`:look==='aurora'?'hue-rotate(42deg)':look==='starlight'?'saturate(.68) brightness(1.18)':'none');
 return <div className={'cosmic-creature3d '+className} aria-label={label} data-creature-state={state} data-graphics={showSprite?'qbeast-sprite':ready?'procedural-3d':'illustration'} data-motion={paused?'paused':reduced?'reduced':'active'} data-creature-id={selected?.id??'preview'} data-cosmetic-hue={selected?.appearance.hueShift??0}>
  <img className={'cosmic-creature-fallback '+(ready&&!reduced?'hidden':'')} src="/cosmic-creature.svg" alt="" style={{filter:appearance}}/>
  {showSprite&&activeSprite?<div className="cosmic-creature-pixel" data-fallback="same-qbeast-sprite"><PixelBeast genome={activeSprite} stage={earnedStage} publicSpark pose={paused||reduced?'idle':state==='sleeping'?'emote':state==='celebrating'?'react':'idle'} emote={state==='sleeping'?'sleep':state==='celebrating'?'spark':'watch'} reduced={paused||reduced} label={`${spriteName||label} · same recorded-seed sprite, form ${earnedStage}`}/></div>:null}
  {!reduced&&!fallback&&!preferSprite?<canvas ref={canvas} className="cosmic-creature-canvas" aria-hidden="true"/>:null}
 </div>;
}
