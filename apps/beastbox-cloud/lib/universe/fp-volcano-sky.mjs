// First-person sky: world-volcano at Cosmo's spot (azimuth 191.8°, 30.4° up, 9.29° across, no ring, lava glow on its night side only,
// lit by the one sun) and the seeded neighbours kept smaller than it and well away from it. SEEDED placement, pure maths, no random calls.
export const VOLCANO_FP=Object.freeze({label:'SEEDED',azimuthDeg:191.785,elevationDeg:30.4477,angularDeg:9.292});
/** Neighbours (rings included) never look bigger than this share of world-volcano, and keep at least this much sky between centres. */
export const FP_NEIGHBOUR_RULE=Object.freeze({label:'SEEDED',maxShare:.6,minSepDeg:30,stepDeg:15});
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
export const angleDeg=(a,b)=>Math.acos(Math.max(-1,Math.min(1,dot(a,b)/((Math.hypot(...a)*Math.hypot(...b))||1))))*180/Math.PI;
function rotAbout(v,k,th){const c=Math.cos(th),s=Math.sin(th),kd=dot(k,v);const x=[k[1]*v[2]-k[2]*v[1],k[2]*v[0]-k[0]*v[2],k[0]*v[1]-k[1]*v[0]];return [0,1,2].map(i=>v[i]*c+x[i]*s+k[i]*kd*(1-c));}
/** Turn dir about the local up (unit) in fixed steps, away from world-volcano, until it sits at least minSepDeg from it. */
export function clearOfVolcano(dir,vol,up,rule=FP_NEIGHBOUR_RULE){
 if(!vol||angleDeg(dir,vol)>=rule.minSepDeg)return dir;
 const x=[up[1]*vol[2]-up[2]*vol[1],up[2]*vol[0]-up[0]*vol[2],up[0]*vol[1]-up[1]*vol[0]];const sg=dot(dir,x)>=0?1:-1; // which side of the volcano's bearing we are on
 let d=dir;for(let k=1;k<=24&&angleDeg(d,vol)<rule.minSepDeg;k++)d=rotAbout(dir,up,sg*k*rule.stepDeg*Math.PI/180);return d;}
/** Distance so a neighbour of this radius (ring outer factor included) spans at most maxShare of world-volcano's 9.29°. */
export function fpNeighbourDist(radius,ringOuter,dd,rule=FP_NEIGHBOUR_RULE){const ext=radius*Math.max(1,ringOuter||1);const half=VOLCANO_FP.angularDeg*rule.maxShare*Math.PI/360;return Math.max(dd,ext/Math.tan(half));}
/** Cosmo's day/crack look for world-volcano (SEEDED pattern, DERIVED colours): shader-drawn Voronoi-edge cracks ~0.02 wide on the unit sphere,
 *  antialiased with fwidth; glow #FF7A2E falling off to #B5532E. By day the sky lies over the disc at no more than 0.2, cracks show at 0.3 of
 *  their night strength, and a thin sunlit crescent rim follows the one sun. Night is unchanged (day = 0). */
export const VOLCANO_DAY_LOOK=Object.freeze({label:'SEEDED',crackHex:'#FF7A2E',crackFallHex:'#B5532E',dayBodyHex:'#B5532E',lineWidth:.02,cellScale:7,daySkyMax:.2,dayCrackK:.3,dayBodyK:.3});
/** Seed offset for the crack cells from a fixed tag (FNV-1a, no random calls). */
export function crackSeed(tag='world-volcano:cracks'){let h=2166136261;const o=[];for(let k=0;k<3;k++){for(let i=0;i<tag.length;i++){h^=tag.charCodeAt(i)+k;h=Math.imul(h,16777619)>>>0;}o.push((h%10007)/10007*97);}return o;}
/** Sky share laid over the disc for a day factor 0..1 (never above daySkyMax; 0 at night). */
export const daySkyK=(day,L=VOLCANO_DAY_LOOK)=>L.daySkyMax*Math.max(0,Math.min(1,day||0));
/** Crack strength multiplier: 1 at night, dayCrackK at full day. */
export const crackK=(day,L=VOLCANO_DAY_LOOK)=>1+(L.dayCrackK-1)*Math.max(0,Math.min(1,day||0));
