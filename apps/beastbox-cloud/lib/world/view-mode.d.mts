export const VIEW_MODES:readonly ['first','behind','orbit'];export const VIEW_MODE_KEY:string;export const VIEW_MODE_EVENT:string;export const DEFAULT_VIEW_MODE:string;
export function readViewMode(storage:any):string;export function writeViewMode(storage:any,m:string):string;export function nextViewMode(m:string):string;
export function viewModeLabel(m:string,name?:string|null):string;export function viewModeCamera(m:string):{eye:boolean;forceOrbit:boolean};
export function viewChipLabel(m:string,name:string|null|undefined,spawned:boolean):string;
