/**
 * PLUSH 3D CREATURES: every Spark body plan as a real rigged 3D creature, built from the Beast's
 * own genome (no placeholder art). Same palette (paletteOf), ears/tail/wings/pattern variants and
 * genes as the pixel sprite, so Regallet is Regallet in both views.
 *  - Rig: joint hierarchy (root → hips → body → neck/head → ears/eyes; legs; tail chain; wings).
 *  - Secondary motion: ears, tail and wings are damped springs on the shared CST integrator
 *    (springStep + motionParams wind/turbulence/phase), so the engine moves the fur.
 *  - Expressions (shape-key style, blended weights): blink, happy (^^), sleepy, curious, scared, mouth open.
 *  - Element FX: seeded motes per element (ember, frost, verdant, crystal, umbral, radiant, machine, grove).
 *  - Budget: ~6–14k triangles depending on plan (logged in userData.tris), well under 25k.
 * Pure THREE construction; driven each frame by drive() from the life brain.
 */
import {springStep,seededRng,clamp} from '../lib/physics/cst-integrator.mjs';
import {paletteOf} from '../public/spark/draw.mjs';
type Three=typeof import('three');type O3=import('three').Object3D;
export type PlushGenome={seed:string;body:string;island:string;element:string;ears:string;tail:string;wings:string;pattern:string;eye_style?:string;mouth?:string;glow?:string;genes:Record<string,number>;names?:Record<string,string>};
export const PLUSH_BODIES=Object.freeze(['pup','fox','sprout','moth','axolotl','golem','dragonling','bird','fish','serpent','biped']);
const ELEMENT_FX:Record<string,{c:number;rise:number;size:number}>={ember:{c:0xffa040,rise:.6,size:.05},frost:{c:0xd8f4ff,rise:-.15,size:.04},verdant:{c:0x9cff7a,rise:.2,size:.045},grove:{c:0x7affc0,rise:.15,size:.045},
 crystal:{c:0x9ffcff,rise:.25,size:.04},umbral:{c:0xc79bff,rise:.3,size:.05},radiant:{c:0xffe58a,rise:.4,size:.045},machine:{c:0x7fe8ff,rise:.5,size:.035}};

export function buildPlush(THREE:Three,gen:PlushGenome,{low=false}={}){
 const G=gen.genes||{},g=(k:string,d=.5)=>Number.isFinite(G[k])?G[k]:d;const R=seededRng('plush:'+gen.seed);
 const pal=paletteOf(gen as any) as any;const col=(r:number[])=>new THREE.Color(r[0]/255,r[1]/255,r[2]/255);
 const C={base:col(pal.base.mid),dark:col(pal.base.sh),light:col(pal.base.li),alt:col(pal.alt.mid),belly:col(pal.belly.mid),accent:col(pal.accent.mid),glow:col(pal.glow.mid)};
 const seg=low?14:22,rings=low?10:16;const geos:import('three').BufferGeometry[]=[],mats:import('three').Material[]=[];
 const fur=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:.78,sheen:1,sheenRoughness:.45,sheenColor:C.light,clearcoat:.05});mats.push(fur);
 const glowMat=new THREE.MeshStandardMaterial({color:C.glow,emissive:C.glow,emissiveIntensity:.9*(.4+g('glow_amount')),roughness:.4});mats.push(glowMat);
 const eyeMat=new THREE.MeshPhysicalMaterial({color:0x0b0a18,roughness:.08,clearcoat:1,clearcoatRoughness:.05});mats.push(eyeMat);
 const irisMat=new THREE.MeshBasicMaterial({color:C.glow});const shineMat=new THREE.MeshBasicMaterial({color:0xffffff});mats.push(irisMat,shineMat);
 const mouthMat=new THREE.MeshBasicMaterial({color:0x2a1222});mats.push(mouthMat);
 // pattern: seeded 3D value noise painted into vertex colours (spots / stripes / belly / stars / facets / moss / plates / cracks / circuits)
 const ph=[R()*10,R()*10,R()*10],pd=g('pattern_density'),ps=7+g('pattern_scale')*7;
 const n3=(x:number,y:number,z:number)=>Math.sin(x*ps+ph[0]+Math.sin(z*ps*.7+ph[1]))*Math.cos(y*ps*1.1+ph[2]+Math.sin(x*ps*.6))*.5+.5;
 const paint=(geo:import('three').BufferGeometry,{belly=true,pat=true,tint=C.base}:{belly?:boolean;pat?:boolean;tint?:import('three').Color}={})=>{
  const p=geo.attributes.position,n=geo.attributes.normal,c=new Float32Array(p.count*3),tmp=new THREE.Color();
  for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),z=p.getZ(i),ny=n.getY(i),nz=n.getZ(i);tmp.copy(tint);
   // soft top-light gradient baked like a plush toy
   tmp.lerp(C.light,clamp(ny*.35+.1)*.5);tmp.lerp(C.dark,clamp(-ny*.6)*.45);
   if(belly&&nz>.25&&ny<.45)tmp.lerp(C.belly,clamp((nz-.25)*2.2)*.85);
   if(pat){const v=n3(x,y,z),pt=gen.pattern;let m=0;
    if(pt==='stripes'||pt==='cracks'||pt==='circuits')m=Math.abs(Math.sin((x+y*.3)*ps*2+v*3))>.86-pd*.2?1:0;
    else if(pt==='stars'||pt==='facets')m=v>.9-pd*.12?1:0;else m=v>.78-pd*.18?1:0;
    if(m)tmp.lerp(pt==='stars'||pt==='cracks'?C.glow:C.alt,pt==='belly'?0:.8);}
   c[i*3]=tmp.r;c[i*3+1]=tmp.g;c[i*3+2]=tmp.b;}
  geo.setAttribute('color',new THREE.BufferAttribute(c,3));return geo;};
 const J=(name:string,parent:O3,x=0,y=0,z=0)=>{const o=new THREE.Group();o.name=name;o.position.set(x,y,z);parent.add(o);return o;};
 const blob=(parent:O3,sx:number,sy:number,sz:number,{x=0,y=0,z=0,mat=fur as import('three').Material,belly=true,pat=true,tint=C.base,s=seg,r=rings}={})=>{
  const geo=new THREE.SphereGeometry(1,s,r);geo.scale(sx,sy,sz);if(mat===fur)paint(geo,{belly,pat,tint});geos.push(geo);const m=new THREE.Mesh(geo,mat);m.position.set(x,y,z);m.castShadow=true;parent.add(m);return m;};
 const cone=(parent:O3,r:number,h:number,{x=0,y=0,z=0,mat=fur as import('three').Material,tint=C.base,rx=0,rz=0}={})=>{const geo=new THREE.ConeGeometry(r,h,low?8:12,3);geo.translate(0,h/2,0);if(mat===fur)paint(geo,{belly:false,pat:false,tint});geos.push(geo);const m=new THREE.Mesh(geo,mat);m.position.set(x,y,z);m.rotation.set(rx,0,rz);parent.add(m);return m;};

 const plan=PLUSH_BODIES.includes(gen.body)?gen.body:'pup';
 const quad=['pup','fox','axolotl','dragonling'].includes(plan),biped=['sprout','golem','biped','bird'].includes(plan),floaty=['moth','fish'].includes(plan);
 const chub=.9+g('chub')*.35,headS=1.05+g('head')*.3,legL=.45+g('legs')*.35;
 const root=new THREE.Group();root.name='plush-'+plan;
 const hips=J('hips',root,0,0,0),body=J('body',hips);
 let headY=0,headZ=0,bodyH=0;const legs:O3[]=[];const arms:O3[]=[];
 // ---------- body
 if(quad){const len=plan==='fox'?.5:plan==='axolotl'?.55:.42,ht=plan==='axolotl'?.16:.28;bodyH=(plan==='axolotl'?.18:.3)*legL+ht;
  blob(body,.27*chub,ht*chub,len*chub,{y:bodyH});headY=bodyH+ht*.9;headZ=len*chub*.85;
  for(const [sx,sz] of [[-1,1],[1,1],[-1,-1],[1,-1]]){const leg=J('leg',body,sx*.16*chub,bodyH-.05,sz*len*.55*chub);const l=bodyH-.04;
   blob(leg,.075,l*.55,.075,{y:-l*.5,belly:false,pat:false});blob(leg,.085,.05,.1,{y:-l+.02,z:.02,belly:false,pat:false,tint:C.light});legs.push(leg);}}
 else if(biped){const ht=plan==='golem'?.36:plan==='bird'?.3:.28;bodyH=.16*legL+ht;
  if(plan==='golem'){const geo=new THREE.BoxGeometry(.62,ht*2,.46,4,4,4);const p=geo.attributes.position;for(let i=0;i<p.count;i++){const v=new THREE.Vector3().fromBufferAttribute(p,i);const s=v.clone().normalize().multiply(new THREE.Vector3(.31,ht,.23));v.lerp(s,.35);p.setXYZ(i,v.x,v.y,v.z);}geo.computeVertexNormals();paint(geo);geos.push(geo);const m=new THREE.Mesh(geo,fur);m.position.y=bodyH;body.add(m);}
  else blob(body,.27*chub,ht*chub,.24*chub,{y:bodyH});
  headY=bodyH+ht*(plan==='bird'?.7:1.05);headZ=.03;
  for(const sx of [-1,1]){const leg=J('leg',body,sx*.13*chub,bodyH-ht*.6,0);const l=bodyH-ht*.6;blob(leg,.08,l*.6,.08,{y:-l*.45,belly:false,pat:false,tint:plan==='bird'?C.accent:C.base});blob(leg,.09,.045,.12,{y:-l+.02,z:.03,belly:false,pat:false,tint:plan==='bird'?C.accent:C.light});legs.push(leg);}
  if(plan!=='bird')for(const sx of [-1,1]){const arm=J('arm',body,sx*.27*chub,bodyH+ht*.25,0);blob(arm,.07,.17,.07,{y:-.13,x:sx*.03,belly:false,pat:false});arms.push(arm);}}
 else if(plan==='serpent'){bodyH=.14;headY=.28;headZ=.0;}
 else{// moth / fish (hover)
  bodyH=.75;if(plan==='fish'){blob(body,.2*chub,.26*chub,.42*chub,{y:bodyH});headY=bodyH+.02;headZ=.3*chub;}
  else{blob(body,.24*chub,.27*chub,.27*chub,{y:bodyH});blob(body,.15,.16,.22,{y:bodyH-.08,z:-.28,tint:C.alt});headY=bodyH+.28;headZ=.06;}}
 // ---------- serpent chain body (spring-driven)
 const spine:O3[]=[];if(plan==='serpent'){let par:O3=body;const n=low?7:10;for(let i=0;i<n;i++){const j=J('spine'+i,par,0,0,i===0?0:-.17);if(i===0)j.position.set(0,bodyH,0);const r=.16*chub*(1-i/n*.6);blob(j,r,r*.9,r*1.25,{});spine.push(j);par=j;}}
 // ---------- head
 const neck=J('neck',body,0,headY,headZ),head=J('head',neck);const hr=(plan==='golem'?.27:plan==='fish'?0:.3)*headS;
 if(plan==='serpent'){neck.position.set(0,.24,.18);}
 if(hr>0){if(plan==='golem'){blob(head,hr*1.05,hr*.85,hr*.9,{y:hr*.7,s:low?10:14,r:low?8:10});}else blob(head,hr*1.05,hr*.95,hr,{y:hr*.75});}
 const faceZ=plan==='fish'?.16:hr*.92,faceY=plan==='fish'?0:hr*.78;
 if(plan==='fox'||plan==='pup'||plan==='dragonling')blob(head,hr*.42,hr*.32,hr*.45,{y:hr*.55,z:hr*.82,tint:plan==='fox'?C.belly:C.light,pat:false});
 if(plan==='bird')cone(head,hr*.22,hr*.5,{y:hr*.62,z:hr*.85,rx:Math.PI/2,mat:fur,tint:C.accent});
 if(plan==='axolotl'){head.scale.set(1.25,.85,1);}
 // eyes (big, glossy, with iris glow + catchlight) on a lid-scaled group = blink/expressions
 const eyeR=hr>0?hr*(.2+g('eye_size')*.12):.07,gap=hr>0?hr*(.36+g('eye_gap')*.18):.1;const eyes:O3[]=[];
 for(const sx of [-1,1]){const e=J('eye',head,sx*gap,faceY+(plan==='fish'?bodyH-headY+.06:0),faceZ);const ball=blob(e,eyeR,eyeR*1.1,eyeR*.6,{mat:eyeMat,s:16,r:12});void ball;
  blob(e,eyeR*.5,eyeR*.55,eyeR*.3,{mat:irisMat,z:eyeR*.38,y:-eyeR*.15,s:10,r:8});blob(e,eyeR*.26,eyeR*.26,eyeR*.15,{mat:shineMat,z:eyeR*.52,y:eyeR*.38,x:sx*-eyeR*.3,s:8,r:6});eyes.push(e);}
 if(plan==='fish')for(const e of eyes)e.position.set(e.position.x*1.9,.07,.3*chub-headZ);
 // mouth: small dark ellipse (scale = open), cheeks
 const mouth=blob(head,hr*.12||.04,hr*.05||.02,.02,{mat:mouthMat,y:plan==='fish'?bodyH-headY:faceY-hr*.3,z:plan==='fish'?.42*chub:faceZ+hr*.06,s:10,r:6});
 if(plan==='fish')mouth.position.set(0,-.06,.42*chub-headZ);
 // ---------- ears / horns / gills / feelers (spring joints)
 const ears:O3[]=[];const earS=.7+g('ear_size')*.6;const et=gen.ears;
 if(hr>0&&plan!=='bird')for(const sx of [-1,1]){const ear=J('ear',head,sx*hr*.55,hr*1.35,-hr*.05);ear.rotation.z=-sx*.35;
  if(et==='round'){blob(ear,hr*.28*earS,hr*.28*earS,hr*.1,{y:hr*.12});}
  else if(et==='leaf'){blob(ear,hr*.16*earS,hr*.4*earS,hr*.05,{y:hr*.3,tint:C.accent,pat:false});}
  else if(et==='horns'||et==='crown'||et==='crystal'||et==='flame'){cone(ear,hr*.12,hr*.55*earS,{mat:et==='crystal'||et==='flame'?glowMat:fur,tint:C.accent});}
  else if(et==='antlers'){cone(ear,hr*.06,hr*.6*earS,{tint:C.alt});cone(ear,hr*.05,hr*.3*earS,{y:hr*.3,rz:-sx*.8,tint:C.alt});}
  else if(et==='feelers'||et==='antenna'){cone(ear,hr*.03,hr*.7*earS,{tint:C.dark});blob(ear,hr*.08,hr*.08,hr*.08,{y:hr*.72,mat:glowMat});}
  else if(et==='gills'){ear.position.set(sx*hr*1.1,hr*.75,0);ear.rotation.z=-sx*1.2;for(let k=-1;k<=1;k++)cone(ear,hr*.06,hr*.45*earS,{rz:k*.4,mat:glowMat});}
  else if(et==='bolts'){blob(ear,hr*.1,hr*.18,hr*.1,{y:hr*.1,tint:C.alt,pat:false});}
  else{cone(ear,hr*.2*earS,hr*.5*earS,{});cone(ear,hr*.1*earS,hr*.32*earS,{z:.01,tint:C.belly});}// pointy
  ears.push(ear);}
 if(plan==='sprout'){const leaf=J('ear',head,0,hr*1.6,0);blob(leaf,hr*.15,hr*.45,hr*.05,{y:hr*.35,rz:.3,tint:C.accent,pat:false} as any);ears.push(leaf);}
 // ---------- tail chain
 const tail:O3[]=[];const tlen=(plan==='fox'?7:plan==='serpent'?0:plan==='fish'?3:5);const ts=.6+g('tail_size')*.7;
 if(gen.tail!=='none'&&tlen>0){let par:O3=J('tail',body,0,bodyH+(plan==='fish'?0:.05),-(quad?.45:plan==='fish'?.38:.2)*chub);for(let i=0;i<tlen;i++){const j=J('tail'+i,par,0,i?.025:0,i?-.075*ts:0);const fluffy=plan==='fox'||gen.tail==='fluffy'||gen.tail==='plume';const r=(plan==='fox'?.12:fluffy?.1:.065)*ts*(fluffy?Math.sin((i+1)/(tlen+1)*Math.PI)*.8+.45:1-i/tlen*.6);
   if(plan==='fish'&&i===tlen-1){blob(j,.02,.2*ts,.14*ts,{z:-.1,tint:C.alt,pat:false});}else blob(j,r,r,r*1.3,{z:-.05,tint:i===tlen-1&&plan==='fox'?C.belly:C.base,pat:i<tlen-1});
   if(i===tlen-1&&(gen.tail==='flame'||gen.tail==='crystal'))cone(j,.06,.18,{mat:glowMat,rx:-1.2,z:-.1});tail.push(j);par=j;}}
 if(plan==='fish')for(const sx of [-1,1]){const fin=J('wing',body,sx*.2*chub,bodyH-.02,.05);blob(fin,.02,.08,.13,{z:-.06,x:sx*.03,tint:C.alt,pat:false});fin.rotation.z=sx*.6;}
 // ---------- wings
 const wings:O3[]=[];const wt=gen.wings;const ws=.7+g('wing_size')*.6;
 if((wt&&wt!=='none')||plan==='moth'||plan==='bird'){const kind=plan==='moth'?'moth':plan==='bird'?'feather':wt;
  for(const sx of [-1,1]){const w=J('wing',body,sx*.16*chub,bodyH+(plan==='moth'?.08:quad?.2:.15),quad?-.12:-.08);
   const wm=kind==='crystal'||kind==='flame'?glowMat:fur;const tint=kind==='moth'?C.alt:kind==='bat'?C.dark:C.base;
   if(kind==='moth'){blob(w,.36*ws,.3*ws,.025,{x:sx*.3*ws,y:.12,mat:wm,tint,belly:false});blob(w,.24*ws,.2*ws,.02,{x:sx*.22*ws,y:-.2,mat:wm,tint:C.accent,belly:false});blob(w,.07,.07,.03,{x:sx*.36*ws,y:.16,mat:glowMat});}
   else if(kind==='feather'||kind==='leaf'){for(let f=0;f<3;f++)blob(w,.022,.07*ws*(1-f*.18),.2*ws*(1-f*.15),{x:sx*(.05+f*.03),y:.06+f*.035,z:-.06-f*.04,mat:wm,tint:f===2?C.accent:(kind==='leaf'?C.accent:C.light),belly:false,pat:false,s:12,r:8});w.rotation.x=-.5;}
   else{for(let f=0;f<3;f++){const a=.5-f*.45;blob(w,.2*ws*(1-f*.12),.035,.06,{x:sx*Math.cos(a)*.17*ws,y:.06+Math.sin(a)*.17*ws,z:-.02,mat:wm,tint,belly:false,pat:false,s:12,r:8}).rotation.z=sx*a;}blob(w,.16*ws,.12*ws,.012,{x:sx*.14*ws,y:.08,z:-.03,mat:wm,tint:kind==='bat'?C.alt:tint,belly:false,pat:false});w.rotation.x=-.35;}
   w.rotation.y=sx*.25;wings.push(w);}}
 // ---------- element motes
 const fx=ELEMENT_FX[gen.element]||ELEMENT_FX.radiant;const moteN=low?14:28;const mp=new Float32Array(moteN*3);const motes=Array.from({length:moteN},()=>({a:R()*6.28,r:.25+R()*.35,y:R(),s:.5+R()}));
 const moteGeo=new THREE.BufferGeometry();moteGeo.setAttribute('position',new THREE.BufferAttribute(mp,3));geos.push(moteGeo);
 const moteMat=new THREE.PointsMaterial({color:fx.c,size:fx.size,transparent:true,opacity:.8,blending:THREE.AdditiveBlending,depthWrite:false});mats.push(moteMat);
 const moteObj=new THREE.Points(moteGeo,moteMat);moteObj.frustumCulled=false;root.add(moteObj);
 // contact shadow
 const shGeo=new THREE.CircleGeometry(.42*chub,24);geos.push(shGeo);const shMat=new THREE.MeshBasicMaterial({color:0,transparent:true,opacity:.35,depthWrite:false});mats.push(shMat);
 const shadow=new THREE.Mesh(shGeo,shMat);shadow.rotation.x=-Math.PI/2;shadow.position.y=.005;root.add(shadow);
 let tris=0;root.traverse(o=>{const m=o as import('three').Mesh;if(m.isMesh){const gg=m.geometry;tris+=(gg.index?gg.index.count:gg.attributes.position.count)/3;}});root.userData.tris=Math.round(tris);
 // ---------- springs (CST integrator springStep) + expression weights
 const S=(n:number)=>Array.from({length:n},()=>({x:0,v:0}));const earSp=S(ears.length),earSp2=S(ears.length),tailSp=S(tail.length),tailSp2=S(tail.length),wingSp=S(wings.length),spineSp=S(spine.length);
 const expr={blink:0,happy:0,sleepy:0,curious:0,scared:0,open:0};let blinkT=1+R()*3,prevHeading=0,t=0,beat=0;
 const headLook=new THREE.Vector3(),tmpQ=new THREE.Quaternion(),tmpV=new THREE.Vector3();
 /** life: {speed, mode, sleep, lookCam, bob, heading}; mp: CST motionParams; look: world point or null. */
 function drive(dt:number,life:{speed:number;mode:string;sleep:number;lookCam:number;bob:number;heading:number;startle?:number},mp:any,look:{x:number;y:number;z:number}|null){
  t+=dt;const sp=life.speed,ph=life.bob,mood=mp?.mood||{joy:.5,fear:.1,curiosity:.5,calm:.6,mischief:.3};
  const k=60*(mp?.stiffness||1),d=8*(mp?.damping||1),turb=mp?.turbulence||0,wind=mp?.wind||{x:0,z:0};
  // turn rate → secondary sway (tail/ears lag the body)
  let dh=life.heading-prevHeading;dh=((dh+Math.PI*3)%(Math.PI*2))-Math.PI;prevHeading=life.heading;const yawRate=clamp(dh/Math.max(dt,1e-3),-4,4);
  // gait
  const stride=clamp(sp*1.6);const sw=Math.sin(ph*1.0);
  if(quad)legs.forEach((l,i)=>{l.rotation.x=Math.sin(ph+(i===0||i===3?0:Math.PI))*.6*stride;});
  else legs.forEach((l,i)=>{l.rotation.x=Math.sin(ph+i*Math.PI)*.7*stride;});
  arms.forEach((a,i)=>{a.rotation.x=-Math.sin(ph+i*Math.PI)*.6*stride;a.rotation.z=(i?-1:1)*(.15+mood.joy*.15*Math.sin(t*2));});
  const nap=life.sleep;const breathe=Math.sin(t*(1.4+mood.calm*-.5))*.02;
  hips.position.y=(floaty?Math.sin(t*1.6)*.06+.02:Math.abs(sw)*.035*stride)-nap*(quad?bodyH*.45:biped?bodyH*.25:.0);
  body.rotation.z=(quad?0:Math.sin(ph)*.06*stride)+nap*(biped?.0:0);body.rotation.x=nap*(biped?.25:0)-(life.startle||0)*.2;
  body.scale.set(1+breathe,1-breathe+(beat*.015),1+breathe);
  if(spine.length){spine.forEach((s,i)=>{const target=Math.sin(ph*.8-i*.7)*(.25+sp*.4)+yawRate*.05*i;springStep(spineSp[i],target,k*.6,d,dt);s.rotation.y=spineSp[i].x;});}
  // head look: toward look target (clamped), else idle scan; sleepy droop
  if(look){neck.updateMatrixWorld();headLook.set(look.x,look.y,look.z);neck.worldToLocal(headLook);const yaw=clamp(Math.atan2(headLook.x,headLook.z),-1.1,1.1),pit=clamp(-Math.atan2(headLook.y-.2,Math.hypot(headLook.x,headLook.z)),-.5,.5);
   head.rotation.y+=(yaw-head.rotation.y)*Math.min(1,dt*4);head.rotation.x+=(pit-head.rotation.x)*Math.min(1,dt*4);}
  else{head.rotation.y+=(Math.sin(t*.4)*.3-head.rotation.y)*Math.min(1,dt*2);head.rotation.x+=(nap*.45-head.rotation.x)*Math.min(1,dt*2);}
  head.rotation.z=Math.sin(t*.7)*.05*mood.curiosity+expr.curious*.25;
  // ears / tail / wings: springs on the CST integrator (wind + turbulence from Lorenz/chaos)
  ears.forEach((e,i)=>{const sx=i%2?1:-1;const tgt=-yawRate*.06+(wind.x*sx)*.3+Math.sin(t*9+i)*turb*.12-expr.scared*.6+expr.happy*.15;springStep(earSp[i],tgt,k,d,dt);springStep(earSp2[i],Math.abs(sw)*stride*.25+expr.curious*.3,k,d,dt);
   e.rotation.x=earSp2[i].x-nap*.4;e.rotation.y=earSp[i].x*sx;});
  tail.forEach((s,i)=>{const wag=Math.sin(t*(4+mood.joy*6)-i*.6)*(.12+mood.joy*.35)*(1-nap*.8);const tgt=wag-yawRate*.12*(i+1)/tail.length+wind.x*.2+Math.sin(t*7+i*1.3)*turb*.1;springStep(tailSp[i],tgt,k*.8,d*.8,dt);
   springStep(tailSp2[i],(i===0?(plan==='fox'?.45:.7)-nap*.6:-.08)+stride*.1,k*.8,d,dt);s.rotation.y=tailSp[i].x;s.rotation.x=-tailSp2[i].x;});
  wings.forEach((w,i)=>{const sx=i%2?1:-1;const flap=floaty||plan==='bird'&&sp>.6?Math.sin(t*(plan==='moth'?9:12))*.6:Math.sin(t*1.5)*.08;springStep(wingSp[i],flap+wind.z*.1,k*1.5,d,dt);w.rotation.z=sx*wingSp[i].x;w.rotation.y=sx*(.25-nap*.2);});
  // expressions (weights blend like shape keys)
  blinkT-=dt;if(blinkT<=0){blinkT=2+((t*7919)%1)*4;expr.blink=1;}expr.blink=Math.max(0,expr.blink-dt*7);
  const tw=(k:keyof typeof expr,v:number,r=4)=>{expr[k]+=(v-expr[k])*Math.min(1,dt*r);};
  tw('sleepy',nap);tw('happy',life.mode==='play'||life.mode==='approach'?mood.joy:mood.joy*.3);tw('curious',life.mode==='glance'||life.mode==='sniff'?.8:mood.curiosity*.2);
  tw('scared',(life.startle||0)+mood.fear*.3);tw('open',life.mode==='sniff'&&sp<.05?.4+.4*Math.abs(Math.sin(t*6)):life.mode==='approach'?.5:0,8);
  const lid=Math.max(expr.blink,expr.sleepy,expr.happy*.75);eyes.forEach(e=>{e.scale.set(1+expr.scared*.15,Math.max(.08,1-lid*.92+expr.scared*.2),1);});
  mouth.scale.set(1+expr.happy*.6,1+expr.open*3+expr.happy*.6,1);
  // heartbeat glow (arousal) + element motes
  const rate=1+(mp?mp.stiffness:1)*.9;beat=Math.pow(Math.max(0,Math.sin(t*rate*Math.PI*2)),12);glowMat.emissiveIntensity=.5+g('glow_amount')*.7+beat*.6+mood.joy*.3;
  for(let i=0;i<moteN;i++){const m=motes[i];m.a+=dt*m.s*.6;m.y=(m.y+dt*fx.rise*m.s*.3+1)%1;mp[i*3]=Math.cos(m.a)*m.r+wind.x*m.y*.3;mp[i*3+1]=bodyH*.4+m.y*(.9+bodyH);mp[i*3+2]=Math.sin(m.a)*m.r+wind.z*m.y*.3;}
  moteGeo.attributes.position.needsUpdate=true;moteMat.opacity=.35+mood.joy*.4+beat*.2;
  shadow.scale.setScalar(1-clamp(hips.position.y*2,0,.5));void tmpQ;void tmpV;
 }
 return {root,drive,expr,plan,tris:root.userData.tris,dispose(){geos.forEach(x=>x.dispose());mats.forEach(x=>x.dispose());}};
}
