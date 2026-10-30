export const HORIZON_LABEL:string;export const HORIZON_TIERS:readonly string[];export const HORIZON_LAYERS:readonly any[];
export function horizonLayerIds(tier:string):string[];export function farLayersFor(tier:string):any[];export function aerialFade(d:number):number;
export function recentreAnchor(anchor:number[],cam:number[],distanceM:number,mPerUnit?:number):number[];export function layerPhase(tag:string):number[];
export function vertexEstimate(tier:string):number;export function vertexBudget(tier:string):number;export const HORIZON_AERIAL:any;export const HORIZON_PACK_INFO:any;
