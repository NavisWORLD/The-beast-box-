/** Device-local presentation preferences for the EXISTING Three.js Cage pocket.
 * This module never changes the creature, game battery, source receipt, or model.
 */
export const POCKET_3D_KEY='beastbox-pocket-3d-settings-v1';
export const POCKET_3D_EVENT='beastbox:pocket-3d-settings';
export const POCKET_3D_CAMERA_RESET='beastbox:pocket-3d-reset-camera';
export const DEFAULT_POCKET_3D=Object.freeze({enabled:true,quality:'auto'});

export function normalizePocket3D(value){
 const object=value&&typeof value==='object'&&!Array.isArray(value)?value:{};
 return {
  enabled:typeof object.enabled==='boolean'?object.enabled:true,
  quality:['auto','low','high'].includes(object.quality)?object.quality:'auto'
 };
}
export function readPocket3D(storage){
 try {const text=storage?.getItem(POCKET_3D_KEY);return text?normalizePocket3D(JSON.parse(text)):{...DEFAULT_POCKET_3D};}
 catch{return {...DEFAULT_POCKET_3D};}
}
export function savePocket3D(storage,next){
 const value=normalizePocket3D(next);
 storage.setItem(POCKET_3D_KEY,JSON.stringify(value));
 return value;
}
