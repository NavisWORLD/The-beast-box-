// CST-driven turntable / idle rotation: the yaw is a damped spring chasing a target (inertia + damping from motionParams),
// with Lorenz sway layered on, instead of a linear spin. Deterministic per seed (fixed 120 Hz clock).
import {createCSTState,stepCSTState,motionParams,springStep} from './cst-integrator.mjs';
export function createCSTTurntable(seed='turntable',{speed=.6,swayDeg=6}={}){
 const S=createCSTState('tt:'+seed),yaw={x:0,v:0},pitch={x:0,v:0};let target=0,acc=0;const H=1/120;
 return {state:S,step(dt){acc+=Math.min(.1,Math.max(0,dt));while(acc>=H){acc-=H;stepCSTState(S,H);const m=motionParams(S);
   target+=speed*H*(.85+.3*m.mood.calm);           // drifting target, faster when calm
   const sway=(S.L.x/20)*swayDeg*Math.PI/180;      // Lorenz sway
   springStep(yaw,target+sway,6*m.stiffness,4.5*m.damping,H);springStep(pitch,(S.L.y/25)*.04,4*m.stiffness,4*m.damping,H);}
  return {yaw:yaw.x,pitch:pitch.x};},get yaw(){return yaw.x;}};
}
