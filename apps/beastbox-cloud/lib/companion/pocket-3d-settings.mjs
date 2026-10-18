/** Device-local presentation preferences for the EXISTING Three.js Cage pocket.
 * This module never changes the creature, game battery, source receipt, or model.
 */
export const POCKET_3D_KEY='beastbox-pocket-3d-settings-v1';
export const POCKET_3D_EVENT='beastbox:pocket-3d-settings';
export const POCKET_3D_CAMERA_RESET='beastbox:pocket-3d-reset-camera';
export const DEFAULT_POCKET_3D=Object.freeze({enabled:true,quality:'auto'});
/** Neon wireframe overlay: on unless explicitly saved as false (field only stored once the user flips it). */
export const neonWireOn=v=>v?.neonWire!==false;

export function normalizePocket3D(value){
 const object=value&&typeof value==='object'&&!Array.isArray(value)?value:{};
 return {
  enabled:typeof object.enabled==='boolean'?object.enabled:true,
  quality:['auto','low','high'].includes(object.quality)?object.quality:'auto',
  ...(typeof object.neonWire==='boolean'?{neonWire:object.neonWire}:{})
 };
}
export function readPocket3D(storage){
 try {const text=storage?.getItem(POCKET_3D_KEY);return text?normalizePocket3D(JSON.parse(text)):{...DEFAULT_POCKET_3D};}
 catch{return {...DEFAULT_POCKET_3D};}
}
/** Browser boundary: scene rendering never reads device storage directly. */
export function devicePocket3D(){
 try{return readPocket3D(window.localStorage);}
 catch{return {...DEFAULT_POCKET_3D};}
}
export function savePocket3D(storage,next){
 const value=normalizePocket3D(next);
 storage.setItem(POCKET_3D_KEY,JSON.stringify(value));
 return value;
}
/** Classic pixel Beast toggle for the 3D pocket (presentation-only, device-local). */
export const CLASSIC_PIXEL_KEY='beastbox-classic-pixel-v1';
export function deviceClassicPixel(){try{return globalThis.localStorage?.getItem(CLASSIC_PIXEL_KEY)==='1';}catch{return false;}}
export function saveClassicPixel(on){try{globalThis.localStorage?.setItem(CLASSIC_PIXEL_KEY,on?'1':'0');}catch{}return !!on;}
