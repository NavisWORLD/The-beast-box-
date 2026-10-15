export const SPRITE_ID:string;
export const LAYERS:{part:string;z:number;thick?:number;wing?:number;floor?:boolean;exclude?:string[];live?:boolean}[];
export const MAX_YAW_DEG:number;
export function clampYaw(deg:number):number;
export function ctmToMatrix4(m:{a:number;b:number;c:number;d:number;e:number;f:number}):number[];
export function faceKey(f:any):string;
export function depthPose(yawDeg:number,t?:number,reduced?:boolean):{shell:number;wingFold:number;tailYaw:number;rim:number};
export function volumeFor(part:string,bbox:{x:number;y:number;width:number;height:number}|null):{kind:'cone'|'ellipsoid';cx:number;cy:number;rx:number;ry:number;rz:number}|null;
