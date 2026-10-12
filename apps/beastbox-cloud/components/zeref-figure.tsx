/**
 * ZEREF // MOONWRAITH — original layered vector rig drawn to match Cory's
 * character card and sprite atlas (black fluffy kitten-dragon, violet starry
 * eyes, crescent horn + ear marks, star-membrane wings, smoky tail, glowing
 * paw pads, gem choker). Every animatable part carries data-part so the live
 * renderer can pose it; the static support mascot animates it with CSS.
 * viewBox 0 0 400 400, body centred on x=200.
 */
export const ZEREF_PARTS=['aura','shadow','float','tail','wisps','wingL','wingR','body','pawL','pawR','head','earL','earR','browL','browR',
 'irisL','irisR','pupilL','pupilR','lidL','lidR','lowL','lowR','blushL','blushR','mouth-smile','mouth-grin','mouth-o','mouth-frown','mouth-sleepy',
 'crescent','gem','ring','charge','fx-zzz','fx-question','fx-exclaim','fx-heart','fx-sparkle'] as const;

import {ZEREF_SKIN} from '../lib/zeref/rig-style.mjs';

export type RigSkin=import('../lib/zeref/rig-style.mjs').Skin;
const star=(x:number,y:number,r:number)=>`M${x} ${y-r}Q${x+r*.18} ${y-r*.18} ${x+r} ${y}Q${x+r*.18} ${y+r*.18} ${x} ${y+r}Q${x-r*.18} ${y+r*.18} ${x-r} ${y}Q${x-r*.18} ${y-r*.18} ${x} ${y-r}Z`;

function Eye({side,cx,id,skin}:{side:'L'|'R';cx:number;id:string;skin:RigSkin}){
 const LID=skin.lid;
 const cy=176;
 return <g className="zeref-eye">
  <clipPath id={`${id}-clip${side}`}><ellipse cx={cx} cy={cy} rx="35" ry="39"/></clipPath>
  <g clipPath={`url(#${id}-clip${side})`}>
   <ellipse cx={cx} cy={cy} rx="33" ry="37" fill="#05030b"/>
   <ellipse cx={cx} cy={cy} rx="31" ry="35" fill="#140a2c"/>
   <g data-part={`iris${side}`}>
    <ellipse cx={cx} cy={cy+2} rx="27" ry="31" fill={`url(#${id}-iris)`}/>
    <g data-part={`pupil${side}`} style={{transformOrigin:`${cx}px ${cy+4}px`,transformBox:'view-box'}}>
     <ellipse cx={cx} cy={cy+4} rx="12" ry="16" fill="#1a0638"/>
     <path d={`M${cx+3} ${cy-4}a8 8 0 1 0 0 16a6 6 0 1 1 0-16z`} fill="#c9a6ff" opacity=".55"/>
    </g>
    <path d={star(cx-10,cy-13,9)} fill="#fff"/>
    <circle cx={cx+11} cy={cy+13} r="4" fill="#fff" opacity=".9"/>
    <circle cx={cx+14} cy={cy-6} r="1.8" fill="#e9dcff"/><circle cx={cx-12} cy={cy+16} r="1.4" fill="#e9dcff"/>
   </g>
   <ellipse cx={cx} cy={cy} rx="33" ry="37" fill="none" stroke="#2a1b45" strokeWidth="2.5"/>
   {/* Upper lid slides down to meet the lower lid (closed = soft ∪ lash line); lower lid alone = happy ^^ squint. */}
   <g data-part={`lid${side}`}><rect x={cx-42} y={cy-124} width="84" height="86" fill={LID}/><path d={`M${cx-30} ${cy-39}Q${cx} ${cy-28} ${cx+30} ${cy-39}`} stroke="#c7a2ff" strokeWidth="3.5" strokeLinecap="round" fill="none"/></g>
   <g data-part={`low${side}`}><rect x={cx-42} y={cy+37} width="84" height="84" fill={LID}/><path d={`M${cx-30} ${cy+39}Q${cx} ${cy+27} ${cx+30} ${cy+39}`} stroke="#d3b3ff" strokeWidth="4" strokeLinecap="round" fill="none"/></g>
  </g>
 </g>;
}

function Ear({side,id,skin}:{side:'L'|'R';id:string;skin:RigSkin}){
 const inner=<>
  <path d="M112 146Q104 92 122 50Q154 70 180 106Z" fill={`url(#${id}-fur)`} stroke={skin.stroke} strokeWidth="2.5" strokeLinejoin="round"/>
  <path d="M124 128Q120 94 128 70Q150 86 166 108Z" fill={`url(#${id}-ear)`}/>
  {skin.features.crescent?<path d="M133 104a9 9 0 1 0 9 -12a7 7 0 1 1 -9 12z" fill="#e7d7ff" opacity=".9"/>:<circle cx="140" cy="100" r="5" fill={skin.moon[0]} opacity=".75"/>}
  <path d="M118 52l6 -12M126 58l8 -10" stroke="#3b2a5c" strokeWidth="3" strokeLinecap="round"/>
 </>;
 return side==='L'?<g data-part="earL" style={{transformOrigin:'150px 128px',transformBox:'view-box'}}>{inner}</g>
  :<g transform="translate(400 0) scale(-1 1)"><g data-part="earR" style={{transformOrigin:'150px 128px',transformBox:'view-box'}}>{inner}</g></g>;
}

function Wing({side,id}:{side:'L'|'R';id:string}){
 const inner=<>
  <path d="M244 252C262 206 300 176 344 168C334 186 338 200 350 210C332 213 324 226 330 242C312 238 298 250 298 266C282 256 264 258 250 270Z" fill={`url(#${id}-wing)`} stroke="#1a1030" strokeWidth="4" strokeLinejoin="round"/>
  <path d="M250 262C276 222 306 196 344 170M262 262C290 238 312 226 330 224M276 266C290 256 300 254 312 252" stroke="#1a1030" strokeWidth="3" fill="none" opacity=".8"/>
  <path d={star(300,212,5)} fill="#f3e9ff"/><path d={star(318,236,3.5)} fill="#d8c2ff"/><circle cx="282" cy="236" r="2" fill="#fff"/><circle cx="326" cy="194" r="1.6" fill="#fff"/>
 </>;
 return side==='R'?<g data-part="wingR" style={{transformOrigin:'246px 256px',transformBox:'view-box'}}>{inner}</g>
  :<g transform="translate(400 0) scale(-1 1)"><g data-part="wingL" style={{transformOrigin:'246px 256px',transformBox:'view-box'}}>{inner}</g></g>;
}

function Paw({side,skin}:{side:'L'|'R';skin:RigSkin}){
 const FUR=skin.furSolid;
 const cx=side==='L'?168:232;
 return <g data-part={`paw${side}`} style={{transformOrigin:`${cx}px 340px`,transformBox:'view-box'}}>
  <ellipse cx={cx} cy="348" rx="23" ry="16" fill={FUR} stroke={skin.stroke} strokeWidth="2"/>
  <g fill={skin.beans} className="zeref-beans"><ellipse cx={cx} cy="352" rx="7" ry="5"/><circle cx={cx-10} cy="343" r="3"/><circle cx={cx} cy="340" r="3"/><circle cx={cx+10} cy="343" r="3"/></g>
 </g>;
}

export default function ZerefFigure({id,accent,glow,css=false,skin=ZEREF_SKIN}:{id:string;accent?:string;glow?:string;css?:boolean;skin?:RigSkin}){
 accent=accent||skin.accent;glow=glow||skin.glow;
 const FUR=skin.furSolid,F=skin.features;
 /** css=true: the static support mascot animates these groups with its existing CSS keyframes. */
 const k=(name:string)=>css?name:undefined;
 return <>
  <defs>
   <radialGradient id={`${id}-aura`}><stop stopColor={accent} stopOpacity=".55"/><stop offset=".55" stopColor="#6a3fd1" stopOpacity=".18"/><stop offset="1" stopColor="#000" stopOpacity="0"/></radialGradient>
   <radialGradient id={`${id}-fur`} cx=".4" cy=".3" r=".85"><stop stopColor={skin.fur[0]}/><stop offset=".45" stopColor={skin.fur[1]}/><stop offset="1" stopColor={skin.fur[2]}/></radialGradient>
   <radialGradient id={`${id}-iris`} cx=".45" cy=".35" r=".75"><stop stopColor={skin.iris[0]}/><stop offset=".25" stopColor={skin.iris[1]}/><stop offset=".6" stopColor={skin.iris[2]}/><stop offset="1" stopColor={skin.iris[3]}/></radialGradient>
   <linearGradient id={`${id}-ear`} x2="0" y2="1"><stop stopColor={skin.ear[0]}/><stop offset="1" stopColor={skin.ear[1]}/></linearGradient>
   <linearGradient id={`${id}-wing`} x1="0" y1="1" x2="1" y2="0"><stop stopColor={skin.wing[0]}/><stop offset=".55" stopColor={skin.wing[1]}/><stop offset="1" stopColor={skin.canonical?glow:skin.wing[2]}/></linearGradient>
   <linearGradient id={`${id}-moon`} x2="1" y2="1"><stop stopColor={skin.moon[0]}/><stop offset="1" stopColor={skin.moon[1]}/></linearGradient>
   <linearGradient id={`${id}-tail`} x1="0" y1="1" x2="1" y2="0"><stop stopColor={skin.tail[0]}/><stop offset=".7" stopColor={skin.tail[1]}/><stop offset="1" stopColor={skin.tail[2]}/></linearGradient>
  </defs>
  <circle data-part="aura" cx="200" cy="215" r="185" fill={`url(#${id}-aura)`} opacity=".5"/>
  <ellipse data-part="shadow" cx="200" cy="368" rx="96" ry="12" fill="#05020c" opacity=".55" style={{transformOrigin:'200px 368px',transformBox:'view-box'}}/>
  <g data-part="float" className={k("support-mascot-float")}>
   <ellipse data-part="ring" cx="200" cy="330" rx="130" ry="26" fill="none" stroke={glow} strokeWidth="3" opacity="0" strokeDasharray="10 8"/>
   <g data-part="tail" className={k("support-mascot-tail")} style={{transformOrigin:'258px 318px',transformBox:'view-box'}}>
    <path d="M246 330C300 340 352 318 356 268C360 226 334 198 310 206C300 210 304 220 314 222C334 228 338 252 326 274C310 300 276 306 246 304Z" fill={`url(#${id}-tail)`} stroke={skin.stroke} strokeWidth="2.5"/>
    <path d="M318 206C330 192 328 178 316 170M328 214C346 206 350 190 344 180" stroke="#7b54c7" strokeWidth="5" fill="none" strokeLinecap="round" opacity=".55"/>
    <g data-part="wisps" fill={skin.canonical?"#4b2f86":skin.tail[2]} opacity={F.tailTip==="none"?0:.7}><circle cx="356" cy="250" r="7"/><circle cx="366" cy="232" r="5"/><circle cx="350" cy="214" r="4"/><circle cx="372" cy="270" r="3.5"/></g>
    <circle cx="340" cy="262" r="5" fill={skin.beans}/><path d={star(322,292,5)} fill="#e6d6ff"/>
   </g>
   <g className={k("support-mascot-wings")} opacity={F.wings?1:0}><Wing side="L" id={id}/><Wing side="R" id={id}/></g>
   <g data-part="body" className={k("support-mascot-breathe")} style={{transformOrigin:'200px 352px',transformBox:'view-box'}}>
    <ellipse cx="136" cy="338" rx="30" ry="22" fill={FUR} stroke={skin.stroke} strokeWidth="2"/>
    <ellipse cx="264" cy="338" rx="30" ry="22" fill={FUR} stroke={skin.stroke} strokeWidth="2"/>
    <path d="M140 246C120 276 116 326 140 352L260 352C284 326 280 276 260 246C240 226 160 226 140 246Z" fill={`url(#${id}-fur)`} stroke={skin.stroke} strokeWidth="2.5"/>
    <path d="M164 248L174 276L184 258L192 288L200 264L208 288L216 258L226 276L236 248Q200 262 164 248Z" fill={skin.canonical?"#33244f":skin.fur[0]} opacity={skin.canonical?1:.55}/>
    <g fill="#c9a6ff" opacity=".8"><circle cx="152" cy="300" r="2"/><circle cx="246" cy="292" r="2.4"/><circle cx="230" cy="326" r="1.6"/><circle cx="168" cy="330" r="1.6"/></g>
    <Paw side="L" skin={skin}/><Paw side="R" skin={skin}/>
   </g>
   <g data-part="head" className={k("support-mascot-head")} style={{transformOrigin:'200px 238px',transformBox:'view-box'}}>
    <Ear side="L" id={id} skin={skin}/><Ear side="R" id={id} skin={skin}/>
    {/* Crescent horns sitting at the ear bases. */}
    {F.moonHorns?<><path d="M108 140C92 122 92 98 106 84C102 104 108 122 124 134Z" fill={`url(#${id}-moon)`} opacity=".95"/>
    <path d="M292 140C308 122 308 98 294 84C298 104 292 122 276 134Z" fill={`url(#${id}-moon)`} opacity=".95"/></>:null}
    <path d="M104 172C100 112 150 88 200 88C250 88 300 112 296 172C298 188 312 198 320 208C302 206 298 214 302 224C288 220 278 228 272 238C250 250 150 250 128 238C122 228 112 220 98 224C102 214 98 206 80 208C88 198 102 188 104 172Z" fill={`url(#${id}-fur)`} stroke={skin.stroke} strokeWidth="2.5" strokeLinejoin="round"/>
    <path d="M176 94L184 70L194 92L204 64L212 92L222 72L226 96Z" fill={skin.fur[1]}/>
    <path data-part="crescent" className={k("support-mascot-halo")} style={{transformOrigin:'210px 117px',transformBox:'view-box'}} d={F.crescent?"M214 102a17 17 0 1 0 0 30a13 13 0 1 1 0 -30z":"M200 100L208 116L200 132L192 116Z"} fill={`url(#${id}-moon)`}/>
    <path d={star(236,112,4)} fill="#e6d6ff"/>
    <path data-part="browL" d="M138 132Q156 124 174 130" stroke={skin.brow} strokeWidth="4" strokeLinecap="round" fill="none" style={{transformOrigin:'156px 129px',transformBox:'view-box'}}/>
    <path data-part="browR" d="M226 130Q244 124 262 132" stroke={skin.brow} strokeWidth="4" strokeLinecap="round" fill="none" style={{transformOrigin:'244px 129px',transformBox:'view-box'}}/>
    <g className={k("support-mascot-eyes")}><Eye side="L" cx={156} id={id} skin={skin}/><Eye side="R" cx={244} id={id} skin={skin}/></g>
    <ellipse data-part="blushL" cx="122" cy="214" rx="17" ry="9" fill="#ff7fd6" opacity=".3"/>
    <ellipse data-part="blushR" cx="278" cy="214" rx="17" ry="9" fill="#ff7fd6" opacity=".3"/>
    <path d="M194 206L206 206L200 213Z" fill="#7b4fc4"/>
    <g className={k("support-mascot-mouth")}>
     <path data-part="mouth-smile" d="M184 216Q192 228 200 216Q208 228 216 216" stroke={skin.mouth} strokeWidth="3" strokeLinecap="round" fill="none"/>
     <g data-part="mouth-grin" opacity="0"><path d="M178 216Q200 254 222 216Q200 224 178 216Z" fill="#2a0b2e" stroke={skin.mouth} strokeWidth="2"/><ellipse cx="200" cy="236" rx="10" ry="6" fill="#ff7aa8"/><path d="M184 218L188 229L192 219ZM208 219L212 229L216 218Z" fill="#fff"/></g>
     <ellipse data-part="mouth-o" cx="200" cy="225" rx="7" ry="9" fill="#2a0b2e" stroke={skin.mouth} strokeWidth="2" opacity="0"/>
     <path data-part="mouth-frown" d="M186 228Q200 216 214 228" stroke={skin.mouth} strokeWidth="3" strokeLinecap="round" fill="none" opacity="0"/>
     <path data-part="mouth-sleepy" d="M192 222Q200 226 208 222" stroke={skin.mouth} strokeWidth="3" strokeLinecap="round" fill="none" opacity="0"/>
    </g>
   </g>
   {/* Gem choker sits over the neck seam. */}
   <path d="M146 244Q200 266 254 244" stroke="#0a0612" strokeWidth="8" fill="none" strokeLinecap="round"/>
   <path d="M146 244Q200 266 254 244" stroke="#6f52a8" strokeWidth="2" fill="none" strokeDasharray="3 5"/>
   <path data-part="gem" d="M200 250L209 260L200 272L191 260Z" fill={accent} stroke="#f2e6ff" strokeWidth="1.5"/>
   <path d="M224 256a5 5 0 1 0 5 6a4 4 0 1 1 -5 -6z" fill="#e8dcff"/>
   <circle data-part="charge" cx="200" cy="230" r="150" fill="none" stroke={accent} strokeWidth="6" opacity="0"/>
  </g>
  <g className="zeref-fx">
   <g data-part="fx-zzz" opacity="0" fill="#e6d6ff" fontFamily="Space Grotesk,system-ui,sans-serif" fontWeight="800"><text x="292" y="96" fontSize="30">z</text><text x="318" y="70" fontSize="22">z</text><text x="338" y="50" fontSize="16">z</text></g>
   <text data-part="fx-question" x="300" y="92" opacity="0" fontSize="46" fontWeight="800" fill="#f3e9ff" fontFamily="Space Grotesk,system-ui,sans-serif">?</text>
   <text data-part="fx-exclaim" x="304" y="92" opacity="0" fontSize="50" fontWeight="900" fill="#ffe28a" fontFamily="Space Grotesk,system-ui,sans-serif">!</text>
   <g data-part="fx-heart" opacity="0" fill="#ff8fd8"><path d="M304 92c-10-9-18-15-18-23 0-6 5-10 10-10 4 0 7 2 8 5 1-3 4-5 8-5 5 0 10 4 10 10 0 8-8 14-18 23z"/><path d="M84 112c-6-5-11-9-11-14 0-4 3-6 6-6 2 0 4 1 5 3 1-2 3-3 5-3 3 0 6 2 6 6 0 5-5 9-11 14z" opacity=".8"/></g>
   <g data-part="fx-sparkle" opacity="0" fill="#fff3c4"><path d={star(86,110,12)}/><path d={star(318,84,14)}/><path d={star(334,170,8)}/><path d={star(66,190,7)}/></g>
  </g>
 </>;
}
