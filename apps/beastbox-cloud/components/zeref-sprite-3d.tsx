'use client';
import {useEffect,useId,useRef,useState} from 'react';
import ZerefFigure from './zeref-figure';
import {rigParts,paintRig} from './zeref-paint';
import {useUniverseMotion} from './use-universe-motion';
import {ZEREF_PROFILE,createMind,frameFor,stepMind,tapMind,greetMind} from '../lib/zeref/zeref-mind.mjs';
import {LAYERS,clampYaw,ctmToMatrix4,faceKey,depthPose,MAX_YAW_DEG,volumeFor} from '../lib/zeref/sprite-layers.mjs';

type Props={className?:string;
 /** Live inside the home pocket's three.js world (the pocket renders him); falls back to own canvas. */
 embed?:boolean;autoRotate?:boolean;turntable?:boolean;turntableAngle?:number|null;greet?:number;label?:string};
const TEX=512;

/**
 * 3D Zeref built from Cory's own Moonwraith sprite (the same ZerefFigure the
 * 2D guide draws). The sprite is cut into alpha layers (aura, tail, each wing,
 * body, paws, ears, head with live face), each placed at real depth with a
 * thickness shell and rim light in three.js. Every frame the hidden 2D rig is
 * posed by the same mind/frameFor/paintRig as the flat guide, and each layer
 * copies its part's live 2D transform, so from the front it is the sprite.
 * Full 360° orbit: sculpted volumes fitted to each part's sprite bounds give the
 * sides and back; double-sided membranes (wings, ears, tail) show from behind.
 */
const FACE=['irisL','irisR','pupilL','pupilR','lidL','lidR','lowL','lowR','browL','browR','blushL','blushR','mouth-smile','mouth-grin','mouth-o','mouth-frown','mouth-sleepy','.zeref-eye'];
export default function ZerefSprite3D({className='',embed=false,autoRotate=false,turntable=false,turntableAngle=null,greet=0,label='Zeref in 3D, built from the Moonwraith sprite'}:Props){
 const id='zs'+useId().replace(/[^a-zA-Z0-9]/g,'');
 const svgRef=useRef<SVGSVGElement>(null),canvasRef=useRef<HTMLCanvasElement>(null),wrapRef=useRef<HTMLDivElement>(null);
 const yawRef=useRef(0),dragRef=useRef<{x:number;yaw:number}|null>(null),mindRef=useRef<any>(null);
 const rotRef=useRef({turntable:turntable||autoRotate,angle:turntableAngle});rotRef.current={turntable:turntable||autoRotate,angle:turntableAngle};const idleRef=useRef(0);const holdRef=useRef(false);
 const {reduced}=useUniverseMotion();
 const [state,setState]=useState<'loading'|'ready'|'fallback'>('loading');
 const [embedOn,setEmbedOn]=useState(false);
 useEffect(()=>{if(greet&&mindRef.current)greetMind(mindRef.current);},[greet]);
 useEffect(()=>{
  const svg=svgRef.current,canvas=canvasRef.current;if(!svg||!canvas)return;
  let disposed=false,raf=0,cleanup=()=>{};let embedded=false,embedDeadline=0;
  // Never hang in 'loading': if the layers are not cut within 9s, show the flat sprite fallback.
  const guard=setTimeout(()=>{if(!disposed)setState(st=>st==='loading'?'fallback':st);},9000);
  void (async()=>{try{
   const THREE=await import('three');if(disposed)return;
   const P=rigParts(svg);const mind=createMind({profile:ZEREF_PROFILE,reduced,hour:new Date().getHours()});mindRef.current=mind;
   paintRig(P,frameFor(mind),mind.t);
   const ref=svg.querySelector('[data-sprite-ref]') as SVGGElement;
   // His own WebGL context is created lazily. Embedded on home he is drawn by the pocket's renderer, so a second
   // context (a long synchronous main-thread block on software GL / weak phones) is only made if the pocket never claims him.
   let renderer:import('three').WebGLRenderer|null=null;
   const ensureRenderer=()=>{if(renderer)return renderer;
    const r=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,premultipliedAlpha:true});
    r.setPixelRatio(Math.min(2,window.devicePixelRatio||1));
    // Software GL (CI, old phones): drop to 1x so frames stay cheap.
    try{const gl=r.getContext();const dbg=gl.getExtension('WEBGL_debug_renderer_info');if(dbg&&/swiftshader|llvmpipe|software/i.test(String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL))))r.setPixelRatio(1);}catch{}r.outputColorSpace=THREE.SRGBColorSpace;
    renderer=r;resize();return r;};
   const scene=new THREE.Scene();const camera=new THREE.OrthographicCamera(-2,2,2,-2,-20,20);camera.position.set(0,0,10);camera.lookAt(0,0,0);
   const root=new THREE.Group();scene.add(root);
   scene.add(new THREE.AmbientLight(0x8f7ad8,1.1));
   const key=new THREE.DirectionalLight(0xd9c6ff,1.4);key.position.set(1.5,2,3);scene.add(key);
   const rimA=new THREE.PointLight(0xb57bff,18,9);rimA.position.set(-2.4,1.2,-2.6);scene.add(rimA);
   const rimB=new THREE.PointLight(0x7fe6ff,10,9);rimB.position.set(2.6,.4,-2.4);scene.add(rimB);
   const fur=new THREE.MeshStandardMaterial({color:0x1a1030,emissive:0x0b0618,roughness:.62,metalness:.05});
   const sphere=new THREE.SphereGeometry(1,28,20),cone=new THREE.ConeGeometry(1,1,18);
   const geo=new THREE.PlaneGeometry(4,4);
   // Cut one layer: same SVG, only this part visible, its own+ancestor transforms removed (re-applied as 3D bones).
   const cut=async(part:string,exclude:string[]=[])=>{
    const clone=svg.cloneNode(true) as SVGSVGElement;clone.setAttribute('xmlns','http://www.w3.org/2000/svg');clone.setAttribute('width',String(TEX));clone.setAttribute('height',String(TEX));
    clone.style.cssText='';clone.removeAttribute('style');clone.removeAttribute('class');
    const el=clone.querySelector(`[data-part="${part}"]`) as SVGElement|null;if(!el)return null;
    // Keep only this part (plus <defs>): prune every sibling along its ancestor path. (WebKit ignores
    // per-child visibility overrides inside SVG-as-image, so pruning is the reliable cut.)
    for(let n:Element|null=el;n&&n!==clone;n=n.parentElement){
     (n as SVGElement).style.transform='none';n.removeAttribute('transform');(n as SVGElement).style.opacity='1';n.setAttribute('opacity','1');
     const par=n.parentElement;if(par)[...par.children].forEach(sib=>{if(sib!==n&&sib.tagName.toLowerCase()!=='defs'&&!sib.querySelector('defs'))sib.remove();});
    }
    exclude.forEach(x=>{clone.querySelectorAll(x.startsWith('.')?x:`[data-part="${x}"]`).forEach(e=>e.remove());});
    const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)],{type:'image/svg+xml'}));
    try{const img=new Image();img.decoding='async';img.src=url;await Promise.race([img.decode(),new Promise((_,no)=>setTimeout(()=>no(new Error('decode timeout')),4000))]);const c=document.createElement('canvas');c.width=c.height=TEX;c.getContext('2d')!.drawImage(img,0,0,TEX,TEX);return c;}
    finally{URL.revokeObjectURL(url);}
   };
   const layers:any[]=[];let order=0;
   // Decode every layer cut in parallel (image decode is off-thread), so the ready signal is not a serial chain of decodes
   // competing with the pocket for the main thread on slow / software-GL machines.
   const cuts=await Promise.all(LAYERS.map(L=>cut(L.part,L.exclude).catch(()=>null)));if(disposed)return;
   for(const [li,L] of LAYERS.entries()){
    const c=cuts[li];if(!c)continue;
    const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;tex.premultiplyAlpha=true;tex.generateMipmaps=false;tex.minFilter=THREE.LinearFilter;
    const bone=new THREE.Group();bone.matrixAutoUpdate=false;root.add(bone);
    // Hinge (local sprite px -> plane units): wings at their root, tail at its base; other parts hinge at centre.
    const hinge=L.wing?[.46,-.56]:L.part==='tail'?[.58,-1.18]:[0,0];
    const depth=new THREE.Group();depth.position.set(hinge[0],hinge[1],0);bone.add(depth);
    const inner=new THREE.Group();inner.position.set(-hinge[0],-hinge[1],0);depth.add(inner);
    const shells:any[]=[];
    for(let i=(L.thick||0);i>0;i--){const m=new THREE.MeshBasicMaterial({toneMapped:false,fog:false,map:tex,transparent:true,depthTest:true,depthWrite:false,color:0x2a1748,opacity:0,side:THREE.DoubleSide});const s=new THREE.Mesh(geo,m);s.position.z=L.z-i*0.018;s.renderOrder=order++;inner.add(s);shells.push(s);}
    const rimM=new THREE.MeshBasicMaterial({toneMapped:false,fog:false,map:tex,transparent:true,depthTest:true,side:THREE.DoubleSide,depthWrite:false,color:0xb98aff,opacity:0,blending:THREE.AdditiveBlending});
    const rim=new THREE.Mesh(geo,rimM);rim.position.z=L.z-0.01;rim.scale.setScalar(1.012);rim.renderOrder=order++;if(L.thick)inner.add(rim);
    // Sculpted volume from this part's own sprite bounds, behind its face plane (sides/back read solid).
    const vol=volumeFor(L.part,(P[L.part] as SVGGraphicsElement|undefined)?.getBBox?.()||null);
    if(vol){
     // Painted volume: the part's own sprite art is projected front-to-back onto the sculpted shape
     // (back half gets the "back" cut: same fur, crescent, stripes and silhouette, no face), and the
     // art's alpha clips the volume to Zeref's real silhouette (ears, crown spikes, tail curl).
     const back=L.part==='head'?await cut('head',['earL','earR',...FACE]):L.part==='body'?await cut('body',['pawL','pawR']):c;if(disposed)return;
     const backTex=back===c?tex:new THREE.CanvasTexture(back!);backTex.colorSpace=THREE.SRGBColorSpace;
     // The face lives only on the front sprite plane; the head volume is painted with the face-free cut
     // on both halves so eyes/mouth never smear onto the sides.
     const frontTex=L.part==='head'?backTex:tex;
     const zc=L.z-0.04-vol.rz;
     for(const half of [0,1]){
      const g=vol.kind==='cone'?new THREE.ConeGeometry(1,1,18,1,true,half?Math.PI:0,Math.PI):new THREE.SphereGeometry(1,24,16,half?Math.PI:0,Math.PI);
      const sy=vol.kind==='cone'?vol.ry*2.1:vol.ry,pos=g.attributes.position,uv=g.attributes.uv;
      if(L.part==='head'&&vol.kind!=='cone'){
       // Cat skull, not a ball: flatter crown, fuller cheeks, slight muzzle push, flatter back of head.
       for(let i=0;i<pos.count;i++){let x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i);
        if(y>0)y*=.82;else{x*=1+.16*Math.min(1,-y*1.6);}
        if(z>0&&y<0&&y>-.6)z*=1+.18*(1-Math.abs(x));if(z<0)z*=.86;pos.setXYZ(i,x,y,z);}
       pos.needsUpdate=true;g.computeVertexNormals();
      }
      for(let i=0;i<pos.count;i++){const x=vol.cx+pos.getX(i)*vol.rx,y=vol.cy+pos.getY(i)*sy;uv.setXY(i,(x+2)/4,(y+2)/4);}uv.needsUpdate=true;
      const mm=new THREE.MeshStandardMaterial({fog:false,map:half?backTex:frontTex,alphaTest:.45,roughness:.7,metalness:.05,emissive:0x140a26,side:THREE.DoubleSide});
      const m=new THREE.Mesh(g,mm);m.scale.set(vol.rx,sy,vol.rz);m.position.set(vol.cx,vol.cy,zc);m.renderOrder=-10;inner.add(m);
     }
    }
    const two=!!(L.wing||L.part==='tail'||L.part==='earL'||L.part==='earR'||L.floor||L.part==='aura'||L.part==='ring');
    const mat=new THREE.MeshBasicMaterial({toneMapped:false,fog:false,map:tex,transparent:true,premultipliedAlpha:true,depthTest:true,depthWrite:false,side:two?THREE.DoubleSide:THREE.FrontSide});
    const mesh=new THREE.Mesh(geo,mat);mesh.position.z=L.z;mesh.renderOrder=order++;inner.add(mesh);
    layers.push({L,el:P[L.part],bone,depth,mesh,mat,tex,shells,rim,canvas:c});
   }
   const head=layers.find(x=>x.L.live);let lastFace='',cutting=false;
   const resize=()=>{if(!renderer)return;const r=canvas.getBoundingClientRect();renderer.setSize(Math.max(1,r.width),Math.max(1,r.height),false);};
   resize();const ro=new ResizeObserver(resize);ro.observe(canvas);
   let prev=performance.now();
   const frame=(now:number)=>{
    raf=0;if(disposed)return;const dt=Math.min(.1,(now-prev)/1000);prev=now;
    if(!reduced)stepMind(mind,dt,{hour:new Date().getHours()});
    const f=frameFor(mind);paintRig(P,f,mind.t);
    const rot=rotRef.current;
    if(holdRef.current){}else if(rot.turntable&&!reduced&&!dragRef.current&&now>idleRef.current){yawRef.current=clampYaw(yawRef.current+dt*24);}
    else if(typeof rot.angle==='number'&&!dragRef.current)yawRef.current=clampYaw(rot.angle>180?rot.angle-360:rot.angle);
    const ze=embedded?(window as any).__zerefEmbed:null;
    if(embedded&&!ze?.claimed&&now>embedDeadline){embedded=false;setEmbedOn(false);if((window as any).__zerefEmbed?.root===root)(window as any).__zerefEmbed=null;scene.add(root);}
    const inWorld=!!(embedded&&ze?.claimed);
    if(inWorld)yawRef.current=clampYaw(ze.viewYaw||0);
    const yaw=clampYaw(yawRef.current);root.rotation.y=inWorld?0:yaw*Math.PI/180;
    const dp=depthPose(yaw,mind.t,reduced);
    // Near the front the sprite layers paint in sprite order over the volumes (front == sprite);
    // once the view turns, the planes depth-test against the sculpted volumes.
    const paintOrder=Math.abs(yaw)<=25;
    const base=ref.getCTM();const inv=base?base.inverse():null;
    for(const x of layers){
     const ctm=x.el&&inv&&(x.el as SVGGraphicsElement).getCTM?inv.multiply((x.el as SVGGraphicsElement).getCTM()!):null;
     if(ctm){x.bone.matrix.fromArray(ctmToMatrix4(ctm));x.bone.matrixWorldNeedsUpdate=true;}
     const op=x.el?Number(getComputedStyle(x.el).opacity||1)*Number(x.el.getAttribute('opacity')||1):1;x.mat.opacity=op;x.mat.depthTest=!paintOrder;
     x.shells.forEach((s:any,i:number)=>{s.material.opacity=op*dp.shell*(0.55+0.4*i/Math.max(1,x.shells.length));});x.rim.material.opacity=op*dp.rim;
     if(x.L.wing)x.depth.rotation.y=dp.wingFold;
     if(x.L.part==='tail')x.depth.rotation.y=dp.tailYaw+(inWorld?(ze.motion?.tail||0):0);
     if(inWorld&&x.L.wing)x.depth.rotation.y+=(ze.motion?.ear||0)*.6*(x.L.wing>0?1:-1);
    }
    const key=faceKey(f);
    if(head&&key!==lastFace&&!cutting){cutting=true;lastFace=key;void cut('head',['earL','earR']).then(c=>{if(c&&!disposed){head.tex.image=c;head.tex.needsUpdate=true;}}).finally(()=>{cutting=false;});}
    // Waiting to be claimed by the pocket: draw nothing yet (the deadline above falls back to his own canvas).
    if(!inWorld&&!embedded)ensureRenderer().render(scene,camera);
    if(!reduced||dragRef.current||embedded)raf=requestAnimationFrame(frame);
   };
   if(!embed)ensureRenderer();
   if(embed){embedded=true;embedDeadline=performance.now()+14000;(window as any).__zerefEmbed={root,claimed:false,viewYaw:0};setEmbedOn(true);}
   clearTimeout(guard);setState('ready');raf=requestAnimationFrame(frame);
   const kick=()=>{if(!raf)raf=requestAnimationFrame(frame);};
   const down=(e:PointerEvent)=>{dragRef.current={x:e.clientX,yaw:yawRef.current};kick();};
   const move=(e:PointerEvent)=>{if(!dragRef.current)return;const w=canvas.getBoundingClientRect().width||1;yawRef.current=clampYaw(dragRef.current.yaw+(e.clientX-dragRef.current.x)/w*360);kick();};
   const up=()=>{if(dragRef.current&&Math.abs(yawRef.current-dragRef.current.yaw)<2)tapMind(mind);if(dragRef.current)idleRef.current=performance.now()+2500;dragRef.current=null;kick();};
   canvas.addEventListener('pointerdown',down);window.addEventListener('pointermove',move);window.addEventListener('pointerup',up);
   cleanup=()=>{ro.disconnect();canvas.removeEventListener('pointerdown',down);window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);layers.forEach(x=>{x.tex.dispose();x.mat.dispose();x.rim.material.dispose();x.shells.forEach((s:any)=>s.material.dispose());});geo.dispose();renderer?.dispose();};
   (window as any).__zerefSprite3D={yaw:(d:number|null)=>{if(d===null){holdRef.current=false;return yawRef.current;}holdRef.current=true;yawRef.current=clampYaw(d);kick();return clampYaw(d);},layers:layers.map(x=>x.L.part),scene};
  }catch{if(!disposed)setState('fallback');}})();
  return()=>{if((window as any).__zerefEmbed?.root&&embedded){(window as any).__zerefEmbed.root.removeFromParent();(window as any).__zerefEmbed=null;}disposed=true;clearTimeout(guard);if(raf)cancelAnimationFrame(raf);cleanup();};
 },[reduced]);
 return <div ref={wrapRef} className={'zeref-sprite3d '+className} data-zeref-sprite3d={state} data-embed={embedOn?'on':'off'} data-max-yaw={MAX_YAW_DEG} aria-label={label} role="img">
  <svg ref={svgRef} className="zeref-svg zeref-sprite3d-source" viewBox="0 0 400 400" fill="none" aria-hidden="true" focusable="false"><g data-sprite-ref=""/><ZerefFigure id={id}/></svg>
  <canvas ref={canvasRef} className="zeref-sprite3d-canvas" aria-hidden="true"/>
 </div>;
}
