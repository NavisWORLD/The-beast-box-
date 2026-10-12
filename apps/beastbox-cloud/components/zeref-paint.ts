import type {ZerefFrame} from '../lib/zeref/zeref-mind.mjs';

/** Map every data-part in a ZerefFigure SVG. */
export const rigParts=(root:SVGSVGElement)=>{
 const map:Record<string,SVGElement>={};
 root.querySelectorAll<SVGElement>('[data-part]').forEach(el=>{map[el.dataset.part as string]=el;});
 return map;
};
const n=(v:number,d=2)=>Number.isFinite(v)?+v.toFixed(d):0;
const tf=(el:SVGElement|undefined,v:string)=>{if(el)el.style.transform=v;};
const op=(el:SVGElement|undefined,v:number)=>{if(el)el.style.opacity=String(n(Math.max(0,Math.min(1,v))));};

/**
 * Pose the shared ZEREF vector rig from one pure frame (frameFor + optional
 * pocket blend). Shared by the home guide and the Beast Cage habitat beast so
 * both always animate identically. Extra `wisps` opacity 0 keeps tail-less skins clean.
 */
export function paintRig(P:Record<string,SVGElement>,f:ZerefFrame&{auraStage?:number},t:number,{wisps=true}:{wisps?:boolean}={}){
 tf(P.float,`translate(${n(f.floatX)}px,${n(f.floatY)}px) rotate(${n(f.rot)}deg) scaleX(${n(f.face,3)})`);
 if(P.float){P.float.style.transformOrigin='200px 340px';(P.float.style as any).transformBox='view-box';}
 tf(P.body,`scale(${n(f.bodySX,3)},${n(f.bodySY,3)})`);
 tf(P.head,`translateY(${n(f.headY)}px) rotate(${n(f.headRot)}deg)`);
 tf(P.earL,`rotate(${n(f.earL)}deg)`);tf(P.earR,`rotate(${n(-f.earR)}deg)`);
 tf(P.wingL,`rotate(${n(-f.wingL)}deg)`);tf(P.wingR,`rotate(${n(-f.wingR)}deg)`);
 tf(P.tail,`rotate(${n(f.tail)}deg)`);
 tf(P.wisps,`translate(${n(Math.sin(f.wisp*1.7)*4)}px,${n(Math.cos(f.wisp*1.3)*5)}px)`);op(P.wisps,wisps?.45+Math.sin(f.wisp*2)*.25:0);
 tf(P.pawL,`translateY(${n(-f.pawL*34)}px) rotate(${n(-f.pawL*24)}deg)`);tf(P.pawR,`translateY(${n(-f.pawR*34)}px) rotate(${n(f.pawR*24)}deg)`);
 const gx=f.gazeX*8,gy=f.gazeY*7;
 tf(P.irisL,`translate(${n(gx)}px,${n(gy)}px)`);tf(P.irisR,`translate(${n(gx)}px,${n(gy)}px)`);
 tf(P.pupilL,`scale(${n(f.pupil,3)})`);tf(P.pupilR,`scale(${n(f.pupil,3)})`);
 const lid=Math.min(1,Math.max(0,f.lid)),low=Math.min(1,Math.max(0,f.lower));
 const lowUp=Math.max(low*40,lid*30);
 tf(P.lidL,`translateY(${n(lid*44)}px)`);tf(P.lidR,`translateY(${n(lid*44)}px)`);
 tf(P.lowL,`translateY(${n(-lowUp)}px)`);tf(P.lowR,`translateY(${n(-lowUp)}px)`);
 tf(P.browL,`translateY(${n(-f.brow*6)}px) rotate(${n(f.brow*-10)}deg)`);tf(P.browR,`translateY(${n(-f.brow*6)}px) rotate(${n(f.brow*10)}deg)`);
 (['smile','grin','o','frown','sleepy'] as const).forEach(k=>op(P['mouth-'+k],f.mouth[k]*1.15));
 op(P.blushL,.15+f.blush*.75);op(P.blushR,.15+f.blush*.75);
 const auraBoost=f.auraStage??0;
 op(P.aura,.25+f.glow*.55+f.charge*.2+auraBoost*.25);if(P.crescent)P.crescent.style.filter=`drop-shadow(0 0 ${n(3+f.glow*10)}px #cfa8ff)`;
 op(P.gem,.6+f.glow*.4);op(P.ring,f.ring*.85);op(P.charge,f.charge*.75);
 tf(P.charge,`scale(${n(.85+f.charge*.2,3)})`);if(P.charge)P.charge.style.transformOrigin='200px 230px';
 tf(P.shadow,`scaleX(${n(f.shadow,3)})`);op(P.shadow,.25+f.shadow*.35);
 op(P['fx-zzz'],f.fx.zzz);tf(P['fx-zzz'],`translateY(${n(-Math.abs(Math.sin(t*.8))*8)}px)`);
 op(P['fx-question'],f.fx.question);op(P['fx-exclaim'],f.fx.exclaim);op(P['fx-heart'],f.fx.heart);
 tf(P['fx-heart'],`translateY(${n(-((t*20)%14))}px)`);op(P['fx-sparkle'],f.fx.sparkle);
}
