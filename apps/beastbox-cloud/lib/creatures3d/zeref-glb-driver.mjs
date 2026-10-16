/**
 * Runtime driver for the sculpted Zeref GLB (public/creatures3d/zeref.glb).
 * Every moving part runs on the shared CST integrator (lib/physics/cst-integrator.mjs):
 * a fixed 120 Hz seeded clock advances Cory's CST state (Lorenz, coherence, mood), whose
 * motion params (arousal→stiffness, Lorenz→wind, coherence→damping, chaos→turbulence,
 * phi→phase) drive spring-bone chains for the tail, ears and wings, plus breathing, the head bob
 * and expression morph targets (blink, happy, scared, curious, sleepy, angry, mouth grin/o/smile, brows up/angry).
 * Pure three.js math: no DOM, so it can be unit-tested with a synthetic skeleton.
 */
import {createCSTClock,createCSTState,stepCSTState,motionParams,seededRng,springStep} from '../physics/cst-integrator.mjs';
import {createSpringChain,stepSpringChain,applyToBones} from '../physics/spring-bones.mjs';

export const ZEREF_GLB_URL='/creatures3d/zeref.glb';
export const ZEREF_MORPHS=Object.freeze(['blink','happy','scared','curious','sleepy','angry','mouth_grin','mouth_o','mouth_smile','brows_up','brows_angry']);
/** Mood presets → CST emotion inputs + expression morph targets. */
export const ZEREF_MOODS=Object.freeze({
 calm:{emotion:{valence:.6,arousal:.3,curiosity:.4,fear:.05},morph:{mouth_smile:.6}},
 happy:{emotion:{valence:.95,arousal:.65,curiosity:.5,fear:0},morph:{happy:1,mouth_grin:.85}},
 curious:{emotion:{valence:.7,arousal:.55,curiosity:.95,fear:.05},morph:{curious:1,brows_up:.5,mouth_smile:.4}},
 scared:{emotion:{valence:.15,arousal:.9,curiosity:.2,fear:.95},morph:{scared:1,mouth_o:1,brows_up:1}},
 sleepy:{emotion:{valence:.55,arousal:.05,curiosity:.1,fear:0},morph:{sleepy:1}},
 walk:{emotion:{valence:.75,arousal:.55,curiosity:.6,fear:0},morph:{mouth_smile:.6,curious:.2},walk:true},
 angry:{emotion:{valence:.1,arousal:.85,curiosity:.2,fear:.3},morph:{angry:1,brows_angry:1}},
});
const CHAINS=[
 {name:'tail',bones:['tail.0','tail.1','tail.2','tail.3','tail.4'],stiffness:.06,drag:.1,gravity:-.25},
 {name:'earL',bones:['ear.0.L','ear.1.L'],stiffness:.22,drag:.18,gravity:-.05},
 {name:'earR',bones:['ear.0.R','ear.1.R'],stiffness:.22,drag:.18,gravity:-.05},
 {name:'wingL',bones:['wing.0.L','wing.1.L','wing.2.L'],stiffness:.12,drag:.14,gravity:-.15},
 {name:'wingR',bones:['wing.0.R','wing.1.R','wing.2.R'],stiffness:.12,drag:.14,gravity:-.15},
];
/** Bones are exported with their length along local +Y; add a virtual tip so the last bone can swing too. */
function addTip(THREE,bones){
 const last=bones[bones.length-1];let tip=last.children.find(c=>c.userData.springTip);
 if(!tip){tip=new THREE.Object3D();tip.userData.springTip=true;
  const len=bones.length>1?bones[bones.length-1].position.length():.1;tip.position.set(0,len*.9||.1,0);last.add(tip);}
 return [...bones,tip];
}
export function createZerefDriver(THREE,root,{seed='zeref',mood='calm'}={}){
 // GLTFLoader sanitizes node names (PropertyBinding strips '.', ':', '/', '[', ']'), so 'tail.0' arrives as 'tail0': look up both forms
 const san=n=>String(n).replace(/\s/g,'_').replace(/[\[\]\.:\/]/g,'');
 const byName={};root.traverse(o=>{if(o.isBone||o.type==='Bone'||o.name){const k=san(o.name);byName[k]=byName[k]||o;}});
 const bone=n=>byName[san(n)];
 const meshes=[];root.traverse(o=>{if(o.morphTargetDictionary)meshes.push(o);});
 const clock=createCSTClock({seed,hz:120});const S=createCSTState(seed,{emotion:ZEREF_MOODS[mood]?.emotion});
 const rng=seededRng('blink:'+seed);
 const chains=[];
 for(const def of CHAINS){
  const bones=def.bones.map(bone).filter(Boolean);if(bones.length!==def.bones.length)continue;
  const all=addTip(THREE,bones);all.forEach(b=>{b.userData.bindQuat=b.quaternion.clone();});
  root.updateMatrixWorld(true);
  const rest=all.map(b=>{const v=new THREE.Vector3().setFromMatrixPosition(b.matrixWorld);return {x:v.x,y:v.y,z:v.z};});
  chains.push({def,all,ch:createSpringChain(rest,{name:def.name,stiffness:def.stiffness,drag:def.drag,gravity:def.gravity})});
 }
 const head=bone('head'),neck=bone('neck'),spine=bone('spine'),chest=bone('chest'),rootB=bone('root');
 const limbs=['paw.L','paw.R','leg.L','leg.R'].map(bone).filter(Boolean);
 const bind=new Map();for(const b of [head,neck,spine,chest,rootB,...limbs].filter(Boolean))bind.set(b,{q:b.quaternion.clone(),s:b.scale.clone(),p:b.position.clone()});
 // gait: feet are locked in the model frame (M) during stance (treadmill against the scrolling floor), swing in an arc
 const M=rootB?.parent||root;root.updateMatrixWorld(true);
 const feet=limbs.map(L=>({L,name:L.name,front:L.name.startsWith('paw'),off:(san(L.name)==='pawL'||san(L.name)==='legR')?0:.5,m0:M.worldToLocal(L.getWorldPosition(new THREE.Vector3())),lift:0,z:0}));
 const GAIT={stride:.17,stance:.62,liftF:.055,liftH:.04};
 const weights={};for(const k of ZEREF_MORPHS)weights[k]={x:0,v:0};
 const st={mood,blinkT:1.5+rng()*2.5,blink:0,mp:motionParams(S),t:0,steps:0,walkW:0,angW:0,sleepW:0,scaredW:0,walkPh:0,travel:0,swirl:0,beatPh:0,stir:0};
 const tmp=new THREE.Vector3(),e=new THREE.Euler(),q=new THREE.Quaternion();
 function poseBody(){
  const mp=st.mp,m=mp.mood,ph=mp.phase;
  if(spine&&bind.has(spine)){const b=bind.get(spine);const br=1+.018*Math.sin(st.t*(1.6+S.ch.arousal*1.4));spine.scale.set(b.s.x*br,b.s.y*(2-br),b.s.z*br);}
  if(head&&bind.has(head)){const b=bind.get(head);
   const tilt=(m.curiosity-.4)*.22*Math.sin(st.t*.7)+mp.wind.x*.05,nod=.04*Math.sin(st.t*1.3)-.18*st.sleepW+.08*st.scaredW;
   // story pose: caught mid-thought, a resting head tilt that the CST mood modulates
   const think=-.13*(1-m.fear)+.1*st.angW;
   const yawH=.12*Math.sin(st.t*.45+ph*.1)*m.curiosity;
   if(neck&&bind.has(neck)){e.set(nod*.35,yawH*.4,(tilt+think)*.3);neck.quaternion.copy(bind.get(neck).q).multiply(q.setFromEuler(e));e.set(nod*.65,yawH*.6,(tilt+think)*.7);}  // turns are shared neck/head: no crease
   else e.set(nod,yawH,tilt+think);
   head.quaternion.copy(b.q).multiply(q.setFromEuler(e));}
  const ww=st.walkW,walk=ww>.001,w=st.walkPh;
  if(rootB&&bind.has(rootB)){const b=bind.get(rootB);rootB.position.copy(b.p);if(walk){rootB.position.y+=(Math.abs(Math.cos(w))*.022-.008)*ww;rootB.position.x+=.022*ww*Math.sin(w);}  // bob at 2x + hip shift over the stance feet
   e.set(walk?.03*ww*Math.sin(2*w):0,walk?.05*ww*Math.sin(w):0,walk?-.045*ww*Math.sin(w):0);rootB.quaternion.copy(b.q).multiply(q.setFromEuler(e));}
  root.updateMatrixWorld(true);
  const G=GAIT;
  for(const f of feet){const L=f.L,b=bind.get(L);L.quaternion.copy(b.q);
   const p=((w/(2*Math.PI)+f.off)%1+1)%1;let z,y=0;
   if(p<G.stance){z=G.stride/2-G.stride*(p/G.stance);}
   else{const u=(p-G.stance)/(1-G.stance),s=u*u*(3-2*u);z=-G.stride/2+G.stride*s;y=(f.front?G.liftF:G.liftH)*Math.sin(Math.PI*u);}
   f.z=z*ww;f.lift=y*ww;
   tmp.set(f.m0.x,f.m0.y+f.lift,f.m0.z+f.z);M.localToWorld(tmp);L.position.copy(L.parent.worldToLocal(tmp));
   if(f.front){e.set(-.5*f.lift/G.liftF*ww,0,0);L.quaternion.multiply(q.setFromEuler(e));}}
 }
 function wingFlap(c){
  if(!c.def.name.startsWith('wing'))return;const side=c.def.name.endsWith('L')?-1:1;const b0=c.all[0];
  const amp=.05+.16*S.ch.arousal,f=1.0+2.0*S.ch.arousal,ph=st.t*f*Math.PI+(side>0?.35:0);
  // organic flap: lift + slight sweep/twist, quicker downstroke
  const stroke=Math.sin(ph)+.25*Math.sin(2*ph);e.set(.06*Math.cos(ph),side*.08*Math.sin(ph+.6),side*amp*stroke);b0.quaternion.copy(b0.userData.bindQuat).multiply(q.setFromEuler(e));
 }
 return {
  chains,state:S,clock,
  setMood(m){if(ZEREF_MOODS[m])st.mood=m;},
  get mood(){return st.mood;},
  get params(){return st.mp;},
  get travel(){return st.travel;},
  /** Live CST drive for the shaders: swirl (rad), beat (0..1 lub-dub pulse), stir (0..1), chaos, coherence, lorenz dir. */
  cosmic(){const c=S.ch,p=st.beatPh%1,beat=Math.exp(-((p-.08)**2)/.002)+.6*Math.exp(-((p-.26)**2)/.002),s=Math.hypot(S.L.x,S.L.y,S.L.z)||1;
   return {swirl:st.swirl,beat:Math.min(1,beat),stir:st.stir,chaos:c.chaos,coherence:c.coherence,arousal:c.arousal,lorenz:{x:S.L.x/s,y:S.L.y/s,z:S.L.z/s}};},
  get walk(){return st.walkW;},
  feet(){return feet.map(f=>({name:f.name,x:f.m0.x,z:f.m0.z+f.z,lift:f.lift}));},
  update(dt){
   const md=ZEREF_MOODS[st.mood]||ZEREF_MOODS.calm;
   const n=clock.tick(dt,h=>{stepCSTState(S,h,md.emotion);st.t+=h;st.steps++;
    // pose blends eased on the fixed clock so mood switches don't pop
    const a=1-Math.exp(-h*4);st.walkW+=((md.walk?1:0)-st.walkW)*a;st.angW+=((st.mood==='angry'?1:0)-st.angW)*a;
    st.sleepW+=((st.mood==='sleepy'?1:0)-st.sleepW)*a;st.scaredW+=((st.mood==='scared'?1:0)-st.scaredW)*a;
    // inner cosmos: starlight swirl speed from chaos + Lorenz energy, heartbeat from arousal, 'stirred' beast from fear/anger/chaos
    {const c=S.ch,le=Math.min(2,Math.hypot(S.L.x,S.L.y,S.L.z)/25);st.swirl+=h*(.15+1.8*c.chaos+.5*le);st.beatPh+=h*(1+1.6*c.arousal);
     const tgt=Math.max(st.mood==='scared'||st.mood==='angry'?1:0,Math.min(1,Math.max(0,(c.chaos-.45)/.3)));st.stir+=(tgt-st.stir)*(1-Math.exp(-h*2.5));}
    const rate=5.2+1.6*S.ch.arousal;st.walkPh+=h*rate*st.walkW;st.travel+=h*st.walkW*GAIT.stride/(GAIT.stance*2*Math.PI/rate);
    // expressions: seeded blinks + morph springs integrated at the fixed step (stable at any frame rate)
    st.blinkT-=h;if(st.blinkT<=0){st.blink=.16;st.blinkT=1.8+rng()*3.2*(1-S.ch.arousal*.5);}
    st.blink=Math.max(0,st.blink-h);
    for(const name of ZEREF_MORPHS){
     let target=md.morph[name]||0;
     if(name==='blink')target=st.blink>0&&st.mood!=='sleepy'?1:0;
     springStep(weights[name],target,name==='blink'?900:60*st.mp.stiffness,name==='blink'?50:12*st.mp.damping,h);
    }});
   st.mp=motionParams(S);
   poseBody();
   for(const c of chains){
    c.all.forEach(b=>b.quaternion.copy(b.userData.bindQuat));wingFlap(c);
    if(c.def.name==='tail'&&st.walkW>.001){const b0=c.all[0];b0.parent.getWorldQuaternion(q);const qi=q.clone().invert();const qw=new THREE.Quaternion().setFromAxisAngle(tmp.set(0,1,0),-.32*st.walkW*Math.sin(st.walkPh));b0.quaternion.premultiply(q).premultiply(qw).premultiply(qi);}
    if(c.def.name==='earR'){e.set(-.22*(1-st.mp.mood.fear),0,.16);c.all[0].quaternion.multiply(q.setFromEuler(e));}  // one ear cocked
   }
   root.updateMatrixWorld(true);
   for(const c of chains){
    const rest=c.all.map(b=>{tmp.setFromMatrixPosition(b.matrixWorld);return {x:tmp.x,y:tmp.y,z:tmp.z};});
    for(let i=0;i<n;i++)stepSpringChain(c.ch,clock.h,{rest,mp:st.mp,t:st.t});
    // bones re-aim at the simulated points (the wing flap survives through the flapped rest targets, with lag)
    applyToBones(THREE,c.ch,c.all);
   }
   // expressions: target morph weights + seeded blinks (no blinking while sleepy-closed)
   for(const name of ZEREF_MORPHS){
    const w=Math.min(1,Math.max(0,weights[name].x));
    for(const mesh of meshes){const i=mesh.morphTargetDictionary[name];if(i!==undefined)mesh.morphTargetInfluences[i]=w;}
   }
   return n;
  },
 };
}
