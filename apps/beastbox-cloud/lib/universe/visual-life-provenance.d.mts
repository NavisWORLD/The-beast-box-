export const PROVENANCE_ROWS:ReadonlyArray<{key:string;out:string;text:string;driver:string}>;
export function provenance(snapshot?:any):{pack:{version:string;sha256:string;label:string};seed:{text:string;label:string};rows:{key:string;text:string;driver:string;label:string;on:boolean}[]};
