// Shared camera-gesture helpers for the pocket views (home pocket, cage world, /universe).
// Rotate = one finger or left drag. Zoom = pinch or wheel. Pan (new) = two-finger drag, right drag, or Shift+drag; Shift+arrows on the keyboard.
// Pure maths only: no clock, no Math.random. Each view keeps its own camera model and feeds in its camera basis.

/** A pan gesture: a right-button drag, a Shift+drag, or two fingers down. */
export function isPanGesture({button=0,shiftKey=false,pointers=1}={}){return button===2||!!shiftKey||pointers>=2;}

/** World units per screen pixel at the focus distance for a perspective camera. */
export function worldPerPixel(fovDeg,dist,viewH){return 2*Math.tan((fovDeg*Math.PI/180)/2)*dist/Math.max(1,viewH);}

/** The pan offset after dragging dx,dy pixels: the scene follows the finger (drag right = the world slides right).
 *  basis = {rx,ry,rz,ux,uy,uz,k}: camera right and up vectors in world space and world units per pixel. Offset is clamped to maxR. */
export function panStep(pan,basis,dx,dy,maxR=Infinity){
 const o={x:pan.x-(basis.rx*dx-basis.ux*dy)*basis.k,y:pan.y-(basis.ry*dx-basis.uy*dy)*basis.k,z:pan.z-(basis.rz*dx-basis.uz*dy)*basis.k};
 return clampPan(o,maxR);}

export function clampPan(p,maxR){const l=Math.hypot(p.x,p.y,p.z);if(!(l>maxR)||l===0)return {x:p.x,y:p.y,z:p.z};const s=maxR/l;return {x:p.x*s,y:p.y*s,z:p.z*s};}

/** Ease the offset back to zero (used when the camera is told to focus something). Frame-rate independent. */
export function decayPan(p,dt,rate=3){const s=Math.exp(-Math.max(0,dt)*rate);return {x:p.x*s,y:p.y*s,z:p.z*s};}

/** Midpoint of two pointers. */
export function centroid(a,b){return {x:(a.x+b.x)/2,y:(a.y+b.y)/2};}

/** Keyboard pan step in pixels for Shift+arrow (the caller feeds it to panStep). */
export function keyPanPixels(key,px=40){return key==='ArrowLeft'?[px,0]:key==='ArrowRight'?[-px,0]:key==='ArrowUp'?[0,px]:key==='ArrowDown'?[0,-px]:null;}
