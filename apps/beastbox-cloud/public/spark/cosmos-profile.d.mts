export const COSMOS_PROFILE_SCHEMA:string;
export type CosmosProfile={schema:string;id:string;name:string;provenance:Record<string,any>;traits:Record<string,any>};
export function cosmosIdFor(raw:unknown):string|null;
export function publicProfileFromBeast(beast:any,o?:{name?:string}):CosmosProfile|null;
export function publicProfileFromCreature(c:any):CosmosProfile|null;
export function validatePublicProfile(raw:unknown):{ok:true;profile:CosmosProfile}|{ok:false;error:string};
