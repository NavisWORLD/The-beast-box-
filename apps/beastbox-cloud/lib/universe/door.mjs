// The door: one continuous zoom from the /universe map into the pocket world (ZOOM_GUIDE.md). Pure maths, no randomness.
// The universe camera at d = 4.3 R of the home planet frames it exactly like the pocket world's orbit camera (PR*4.3, fov 55),
// so the two renderers cross-dissolve over d = 5.2 R -> 4.3 R with the framing already matched: nothing switches in one frame.
export const DOOR_FAR=5.2,DOOR_NEAR=4.3,DOOR_PRELOAD=9;
export const ss=(a,b,x)=>{if(a===b)return x>=b?1:0;const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
/** 0 = universe only, 1 = pocket world only. ratio = camera distance / planet radius. */
export const doorProgress=ratio=>ss(DOOR_FAR,DOOR_NEAR,ratio);
/** the pocket canvas is mounted early so its textures are ready before the dissolve starts */
export const doorPreload=ratio=>ratio<DOOR_PRELOAD;
/** ZOOM_GUIDE flat-ground layer: fully opaque below alt_full = min(3000 m, 0.05 R), gone by 2 alt_full */
export const altFull=Rm=>Math.min(3000,0.05*Rm);
export const groundAlpha=(altM,Rm)=>{const f=altFull(Rm);return 1-ss(f,2*f,altM);};
/** zoom-button routing once the door is open: the pocket world's own zoom z (1 = orbit, 0 = shoulder). dir<0 zooms in. */
export function doorZoomStep(z,dir,step=0.2){if(dir<0)return {z:Math.max(0,z-step),leave:false};if(z>=0.97)return {z:1,leave:true};return {z:Math.min(1,z+step),leave:false};}
