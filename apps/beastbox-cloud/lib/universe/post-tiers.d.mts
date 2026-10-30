export const TIERS:readonly ['LOW','MED','HIGH','GOD'];export const QUALITY_KEY:string;export const DEFAULT_TIER:string;
export function autoTier(h?:{phone?:boolean;cores?:number;memoryGB?:number;dpr?:number;reducedMotion?:boolean;softGL?:boolean}):string;
export function readTierOverride(storage:any):string|null;export function writeTierOverride(storage:any,tier:string|null):string|null;
export function activeTier(storage:any,hints:any):string;export function nextTier(t:string):string;export function tierSettings(t:string):any;
export function qualityLabel(t:string):string;export function bloomThresholdPreExposure(t:string):number;
