import {checkIntegrity,hex,type Snapshot} from './verifier';
const toHex=(raw:ArrayBuffer)=>Array.from(new Uint8Array(raw),x=>x.toString(16).padStart(2,'0')).join('');
export async function createSigningKey(){
 const key=await crypto.subtle.generateKey({name:'Ed25519'},true,['sign','verify']) as CryptoKeyPair;
 return {privateKey:key.privateKey,publicKey:toHex(await crypto.subtle.exportKey('raw',key.publicKey))};
}
/** Host API only. Private key is never placed in the snapshot or model tools. */
export async function signSnapshot(snapshot:Snapshot,privateKey:CryptoKey,publicKey:string):Promise<Snapshot>{
 const safe=await checkIntegrity(snapshot);hex(publicKey);
 const value=toHex(await crypto.subtle.sign('Ed25519',privateKey,new TextEncoder().encode(safe.digest)));
 safe.signature={algorithm:'Ed25519',public_key:publicKey,value};return safe;
}
