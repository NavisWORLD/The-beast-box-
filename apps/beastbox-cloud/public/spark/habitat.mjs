/** Bounded idle motion driven by the existing genome's gait and temperament. */
export function habitatPose(gen,t,state='idle',reduced=false,anchor={x:72,y:38}){
 const be=gen.behavior,tempo=be.tempo_hz*(state==='celebrate'?1.55:state==='rest'?.4:1),p=t*tempo*Math.PI*2;
 let dx=0,dy=0,rotation=0;
 const pause=Math.floor(t/4)%5===3;
 if(!reduced&&state!=='rest'){
  const amp=be.amplitude_px*(state==='celebrate'?2.3:1);
  switch(be.gait){
   case 'hop':dy=-Math.abs(Math.sin(p*.5))*amp*5;break;
   case 'sway':dx=Math.sin(p)*amp*3;rotation=Math.sin(p)*.025;break;
   case 'scuttle':dx=Math.sin(p*1.7)*amp*2;dy=-Math.abs(Math.sin(p))*2;break;
   case 'float':dy=Math.sin(p*.5)*amp*3-3;break;
   case 'wobble':dx=Math.sin(p)*amp*2;rotation=Math.sin(p*.7)*.035;break;
   case 'pulse':dy=Math.sin(p)*amp;break;
   default:dy=-(.5-.5*Math.cos(p))*amp*3;
  }
  if(!pause){
   const speed=/Playful|Bold|Fierce/.test(gen.temperament)?1.35:/Serene|Gentle|Steadfast/.test(gen.temperament)?.6:1;
   dx+=Math.sin(t*.23*speed)*38;dy+=Math.sin(t*.17*speed)*9;
  }
 }
 return {x:Math.max(10,Math.min(134,anchor.x+dx)),y:Math.max(10,Math.min(54,anchor.y+dy)),rotation,reduced,pause,phase:p,scale:!reduced&&be.gait==='pulse'&&state!=='rest'?1+Math.sin(p)*.015:1};
}
