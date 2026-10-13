export const CREDENTIAL_AGE:number;
export const PRIVATE_COOKIE:string;
export function validSubject(value:unknown):boolean;
export function issueCredential(secret:string,options?:{subject?:string;now?:number;age?:number;kind?:'guest'|'pair'}):{subject:string;expiry:number;token:string};
export function verifyCredential(secret:string,token?:string|null,options?:{now?:number;kind?:'guest'|'pair'}):{subject:string;expiry:number;nonce:string}|null;
