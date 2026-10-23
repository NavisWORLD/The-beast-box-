export const SESSION_KEY:string;export const COMPANION_KEY:string;
export function beastDisplayName(beast:any):string|null;
export function readActiveBeast(storage:Storage|null|undefined):any;
export function activeBeastName(storage:Storage|null|undefined):{name:string|null;source:'saved'|'seeded'|null};
export function nameOr(n:string|null|undefined,fallback?:string):string;
export function fillBeast(t:string,name:string|null|undefined):string;
