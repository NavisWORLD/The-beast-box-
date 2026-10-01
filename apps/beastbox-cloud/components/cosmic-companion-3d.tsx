'use client';
import {useEffect,useRef,useState} from 'react';

export type CreatureState='idle'|'listening'|'observing'|'thinking'|'remembering'|'celebrating'|'sleeping'|'halted';
export type CreatureLook='nebula'|'aurora'|'starlight';
type Props={state?:CreatureState;look?:CreatureLook;intensity?:number;quality?:'auto'|'low';className?:string;label?:string};

/**
 * Original procedural 3D model. All animation is VISUAL; inferred feelings,
 * intelligence growth and real sensor measurements are never generated here.
 * The user-provided concept art is a reference, not a downloaded texture.
 */
export default function CosmicCompanion3D({state='idle',look='nebula',intensity=0,quality='auto',className='',label='Cosmic companion'}:Props){
 const canvas=useRef<HTMLCanvasElement>(null);
 const stateRef=useRef(state),intensityRef=useRef(0);
 const [ready,setReady]=useState(false),[fallback,setFallback]=useState(false);
 const [reduced,setReduced]=useState(false);
 useEffect(()=>{stateRef.current=state;},[state]);
 useEffect(()=>{intensityRef.current=Number.isFinite(intensity)?Math.min(1,Math.max(0,intensity)):0;},[intensity]);
 useEffect(()=>{
  const query=window.matchMedia('(prefers-reduced-motion: reduce)');
  const update=()=>setReduced(query.matches);
  update();query.addEventListener('change',update);
  return()=>query.removeEventListener('change',update);
 },[]);
 useEffect(()=>{
  const element=canvas.current;
  if(!element||reduced||fallback||typeof window.WebGLRenderingContext==='undefined')return;
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
    const creature=new THREE.Group();scene.add(creature);
    const palette=look==='aurora'?{base:0x83dfdf,lobe:0x70b3e9,petal:0x8ff6e1}:look==='starlight'?{base:0xf3dcff,lobe:0xdbb8ff,petal:0xffe0f4}:{base:0xb395fa,lobe:0x8d68e9,petal:0x8ad6fa};
    const stars=document.createElement('canvas');stars.width=512;stars.height=256;
    const ctx=stars.getContext('2d');
    if(!ctx)throw Error('2D material context unavailable');
    const glow=ctx.createRadialGradient(230,60,16,258,130,280);
    glow.addColorStop(0,look==='aurora'?'#dbfff4':look==='starlight'?'#fff0ff':'#e8d5ff');
    glow.addColorStop(.4,look==='aurora'?'#7aaacc':look==='starlight'?'#bf98e0':'#9b76e8');
    glow.addColorStop(.78,'#5b50a0');glow.addColorStop(1,'#1f245c');
    ctx.fillStyle=glow;ctx.fillRect(0,0,512,256);
    let seed=1729;const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
    for(let i=0;i<490;i++){
     const x=random()*512,y=random()*256,r=random()*.9+.15;
     ctx.fillStyle=i%9===0?'#a5f7ff':i%5===0?'#ffdafb':'#f6f8ff';
     ctx.globalAlpha=.25+random()*.74;
     ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
    }ctx.globalAlpha=1;
    const galaxy=new THREE.CanvasTexture(stars);galaxy.colorSpace=THREE.SRGBColorSpace;
    const bodyMat=new THREE.MeshPhysicalMaterial({map:galaxy,color:palette.base,roughness:.29,metalness:.12,clearcoat:.95,clearcoatRoughness:.17,emissive:palette.base,emissiveIntensity:.21});
    const lobeMat=new THREE.MeshPhysicalMaterial({color:palette.lobe,roughness:.22,metalness:.13,transparent:true,opacity:.9,clearcoat:1,emissive:palette.lobe,emissiveIntensity:.22});
    const petalMat=new THREE.MeshPhysicalMaterial({color:palette.petal,metalness:.17,roughness:.23,transparent:true,opacity:.86,side:THREE.DoubleSide,clearcoat:1,emissive:palette.petal,emissiveIntensity:.25});
    const eyeMat=new THREE.MeshPhysicalMaterial({color:0x0b102c,metalness:.24,roughness:.07,clearcoat:1});
    const starMat=new THREE.MeshPhysicalMaterial({color:0xffe2a0,metalness:.56,roughness:.15,emissive:0xffb960,emissiveIntensity:.3});
    const mouthMat=new THREE.MeshStandardMaterial({color:0x4b2057,roughness:.6});
    const cheekMat=new THREE.MeshBasicMaterial({color:0xffa8d8,transparent:true,opacity:.48});
    const sphere=new THREE.SphereGeometry(1,24,20);
    const body=new THREE.Mesh(sphere,bodyMat);body.scale.set(1.05,.99,.75);creature.add(body);
    for(let i=0;i<11;i++){
     const angle=i*Math.PI*2/11;
     const lobe=new THREE.Mesh(sphere,lobeMat);
     lobe.position.set(Math.sin(angle)*.79,Math.cos(angle)*.73,.1);
     lobe.scale.set(.36,.4,.33);creature.add(lobe);
    }
    const petals:InstanceType<typeof THREE.Mesh>[]=[];
    const shape=new THREE.Shape();
    shape.moveTo(0,-.23);shape.bezierCurveTo(-.22,-.06,-.26,.24,0,.52);shape.bezierCurveTo(.26,.24,.22,-.06,0,-.23);
    const leafGeo=new THREE.ExtrudeGeometry(shape,{depth:.07,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:.036,bevelThickness:.04,curveSegments:8});
    for(let i=0;i<11;i++){
     const angle=i*Math.PI*2/11;
     const pivot=new THREE.Group();pivot.position.set(Math.sin(angle)*.9,Math.cos(angle)*.81,-.13);
     pivot.rotation.z=-angle;const leaf=new THREE.Mesh(leafGeo,petalMat);
     leaf.scale.set(1.14,i%3===0?1.18:.91,1);pivot.add(leaf);creature.add(pivot);petals.push(leaf);
    }
    function star(radius:number,inner:number){
     const result=new THREE.Shape();
     for(let i=0;i<8;i++){const r=i%2===0?radius:inner,a=Math.PI/2-i*Math.PI/4;const x=Math.cos(a)*r,y=Math.sin(a)*r;if(i===0)result.moveTo(x,y);else result.lineTo(x,y);}result.closePath();
     return new THREE.ExtrudeGeometry(result,{depth:.055,bevelEnabled:true,bevelThickness:.023,bevelSize:.014,bevelSegments:2});
    }
    const glints=star(.087,.029),headStar=star(.23,.065);
    for(const side of [-1,1]){
     const x=side*.35;
     const eye=new THREE.Mesh(sphere,eyeMat);eye.position.set(x,.105,.665);eye.scale.set(.19,.255,.115);creature.add(eye);
     const pupilStar=new THREE.Mesh(glints,starMat);pupilStar.position.set(x+.027,.16,.773);creature.add(pupilStar);
     const reflection=new THREE.Mesh(sphere,new THREE.MeshBasicMaterial({color:0xffffff}));
     reflection.position.set(x-.06,.205,.786);reflection.scale.set(.03,.045,.013);creature.add(reflection);
     const cheek=new THREE.Mesh(sphere,cheekMat);cheek.position.set(x*1.52,-.25,.665);cheek.scale.set(.17,.09,.017);creature.add(cheek);
    }
    const mouthCurve=new THREE.QuadraticBezierCurve3(new THREE.Vector3(-.13,-.27,.72),new THREE.Vector3(0,-.43,.82),new THREE.Vector3(.13,-.27,.72));
    const mouth=new THREE.Mesh(new THREE.TubeGeometry(mouthCurve,12,.022,6,false),mouthMat);creature.add(mouth);
    const halo=new THREE.Group();halo.position.set(0,1.41,-.04);creature.add(halo);
    const topStar=new THREE.Mesh(headStar,starMat);topStar.position.set(0,.11,.13);halo.add(topStar);
    const orbit=new THREE.Mesh(new THREE.TorusGeometry(.32,.013,7,50),starMat);orbit.position.set(0,.12,0);orbit.rotation.set(.9,.25,-.17);orbit.scale.set(1,.46,1);halo.add(orbit);
    const points:number[]=[];for(let i=0;i<(quality==='low'?26:75);i++){
     const a=random()*Math.PI*2,r=1.47+random()*.84;
     points.push(Math.cos(a)*r,(random()-.5)*2.9,Math.sin(a)*.45-.5);
    }
    const motesGeo=new THREE.BufferGeometry();motesGeo.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
    const motes=new THREE.Points(motesGeo,new THREE.PointsMaterial({color:0xe0ecff,size:.025,transparent:true,opacity:.77,sizeAttenuation:true}));scene.add(motes);
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
    let prev=performance.now(),lastPaint=0,velocity=0,energy=0,bodyHeight=0,rendered=false;
    const animate=(now:number)=>{
     if(disposed||document.hidden)return;
     const dt=Math.min((now-prev)/1000,.07);prev=now;
     animation=requestAnimationFrame(animate);
     if(now-lastPaint<(quality==='low'?66:34))return;
     lastPaint=now;
     const mood=stateRef.current;
     const desired=mood==='halted'||mood==='sleeping'?0:intensityRef.current;
     energy+=((desired-energy)*Math.min(1,dt*5));
     const target=mood==='thinking'?.09:mood==='listening'?.08+energy*.17:mood==='celebrating'?.21:mood==='sleeping'?-.16:0;
     velocity+=(target-bodyHeight)*dt*15;
     velocity*=Math.exp(-dt*5);
     bodyHeight+=velocity*dt;
     const t=now/1000;
     creature.position.y=bodyHeight+(mood==='sleeping'?0:Math.sin(t*1.25)*.07);
     creature.rotation.y=Math.sin(t*.42)*.13+(mood==='observing'?.16:0);
     creature.rotation.z=Math.sin(t*.73)*.055;
     body.scale.y=.99+energy*.08+(mood==='thinking'?.034*Math.sin(t*4):0);
     halo.rotation.y=t*.57;
     petals.forEach((p,i)=>{p.rotation.z=Math.sin(t*1.4+i*.82)*(.04+energy*.06);});
     motes.rotation.y=t*.046;
     bodyMat.emissiveIntensity=.2+energy*.35+(mood==='thinking'?.1:0);
     renderer.render(scene,camera);
     if(!rendered){rendered=true;setReady(true);}
    };
    const visibility=()=>{if(!document.hidden&&!disposed){prev=performance.now();cancelAnimationFrame(animation);animation=requestAnimationFrame(animate);}else cancelAnimationFrame(animation);};
    document.addEventListener('visibilitychange',visibility);
    animation=requestAnimationFrame(animate);
    rendererCleanup=()=>{
     cancelAnimationFrame(animation);
     observer.disconnect();document.removeEventListener('visibilitychange',visibility);
     element.removeEventListener('webglcontextlost',onLost);
     scene.traverse(object=>{if(object instanceof THREE.Mesh){object.geometry.dispose();
       const material=object.material;for(const m of Array.isArray(material)?material:[material])m.dispose();
      }else if(object instanceof THREE.Points){object.geometry.dispose();
       const material=object.material;for(const m of Array.isArray(material)?material:[material])m.dispose();}});
     sphere.dispose();leafGeo.dispose();glints.dispose();headStar.dispose();galaxy.dispose();
     renderer.dispose();
    };
   }catch{
    if(!disposed){setFallback(true);setReady(false);}
   }
  })();
  return()=>{disposed=true;rendererCleanup();};
 },[look,quality,reduced,fallback]);
 const appearance=look==='aurora'?'hue-rotate(42deg)':look==='starlight'?'saturate(.68) brightness(1.18)':'none';
 return <div className={'cosmic-creature3d '+className} aria-label={label} data-creature-state={state} data-graphics={ready?'procedural-3d':'illustration'}>
  <img className={'cosmic-creature-fallback '+(ready&&!reduced?'hidden':'')} src="/cosmic-creature.svg" alt="" style={{filter:appearance}}/>
  {!reduced&&!fallback?<canvas ref={canvas} className="cosmic-creature-canvas" aria-hidden="true"/>:null}
 </div>;
}
