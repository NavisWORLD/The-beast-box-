/**
 * Sprite-built 3D Zeref: layer plan for cutting Cory's own Moonwraith vector
 * sprite (ZerefFigure) into alpha-cut parts. Pure data + math, no DOM, so it is
 * unit-testable. The front view is the original sprite: every layer is drawn in
 * its own local coordinates and re-placed with the live 2D transform (CTM) of
 * the same part, so at yaw 0 the composite equals the 2D sprite.
 */
export const SPRITE_ID='bb-7f9c2a03';
// DOM order == back-to-front draw order. z = depth (world units, sprite is 4 wide).
export const LAYERS=[
 {part:'aura',z:-0.7},
 {part:'shadow',z:-0.05,floor:true},
 {part:'ring',z:-0.1},
 {part:'tail',z:-0.5,thick:4},
 {part:'wingL',z:-0.32,thick:2,wing:-1},
 {part:'wingR',z:-0.32,thick:2,wing:1},
 {part:'body',z:0,thick:6,exclude:['pawL','pawR']},
 {part:'pawL',z:0.22,thick:3},
 {part:'pawR',z:0.22,thick:3},
 {part:'earL',z:0.08,thick:2},
 {part:'earR',z:0.08,thick:2},
 {part:'head',z:0.2,thick:6,exclude:['earL','earR'],live:true},
 // Unlabelled float-level art (gem choker, its moon charm) rides on the float bob, over the neck seam.
 {part:'float',z:0.24,exclude:['ring','tail','wingL','wingR','body','head','charge','fx-zzz','fx-question','fx-exclaim','fx-heart','fx-sparkle']},
];
/** Full 360° orbit: sides and back come from sculpted volumes fitted to each part's own sprite bounds. */
export const MAX_YAW_DEG=180;
export function clampYaw(deg){let d=(Number(deg)||0)%360;if(d>180)d-=360;if(d<-180)d+=360;return d;}
/** Sculpted volume for a part, fitted inside its sprite silhouette (bbox in viewBox px) and kept behind the sprite face so the front stays the sprite. */
export function volumeFor(part,bbox){
 if(!bbox||!(bbox.width>0)||!(bbox.height>0))return null;
 const kind=part==='earL'||part==='earR'?'cone':part==='body'||part==='head'||part==='pawL'||part==='pawR'||part==='tail'?'ellipsoid':null;
 if(!kind)return null;
 const cx=(bbox.x+bbox.width/2-200)/100,cy=(200-(bbox.y+bbox.height/2))/100;
 const fit=part==='tail'?.3:part==='head'?.4:.42;
 // Thick side volumes (Oct 14 review): depth follows the wider axis so 90°/135° read as a full body.
 const rx=bbox.width/100*fit,ry=bbox.height/100*fit,rz=part==='head'?rx*.95:part==='body'?rx*1.02:part==='tail'?Math.min(rx,ry)*.9:Math.max(rx,ry)*.7;
 return {kind,cx,cy,rx,ry,rz};
}
/** Map an SVG CTM (a,b,c,d,e,f in viewBox px) to a column-major 4x4 for a plane whose texture spans the 400x400 viewBox, world units = px/100, y up, origin at viewBox centre. */
export function ctmToMatrix4({a,b,c,d,e,f}){
 // world = S * M * S^-1 where S maps px->world: x'=(x-200)/100, y'=(200-y)/100
 const A=a,B=-b,C=-c,D=d;
 const E=(a*200+c*200+e-200)/100, F=-(b*200+d*200+f-200)/100;
 return [A,B,0,0, C,D,0,0, 0,0,1,0, E,F,0,1];
}
/** Quantised face key: re-rasterise the live head layer only when the expression really changes. */
export function faceKey(f){if(!f)return '';const q=v=>Math.round((Number(v)||0)*8);const m=f.mouth||{};return [q(f.lid),q(f.lower),q(f.brow),q(f.gazeX),q(f.gazeY),q(f.pupil),q(f.blush),q(m.smile),q(m.grin),q(m.o),q(m.frown),q(m.sleepy)].join(',');}
/** 3D-only extras that are exactly zero at the front, so the front stays the sprite. */
export function depthPose(yawDeg,t=0,reduced=false){
 const s=Math.min(1,Math.abs(Math.sin(clampYaw(yawDeg)*Math.PI/180))*1.4);
 const sway=reduced?0:Math.sin(t*1.8);
 return {shell:s,wingFold:s*0.42,tailYaw:s*(0.25+0.08*sway),rim:s*0.55};
}
