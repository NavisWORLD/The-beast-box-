export type Creation={id:string;name:string;kind:'active'|'saved'|'beast'|'trainer';genome:any|null;seed:string|null;origin:string;look:string|null;art:string|null};
export const MAX_SAVED_ROAMERS:number;
export function listCreations(session:any):Creation[];
export function savedRoamers(session:any,max?:number):Creation[];
export function homeLabel(name:string|null|undefined):string;
export function depthFar(dist:number,near?:number,far?:number):number;
