/** A public recipe nonce for NEW creations; never an ownership credential.
 * Existing registry recipes and imports continue replaying their exact keeper field.
 */
export function personalRecipeLabel(cryptoImpl=globalThis.crypto){
 if(typeof cryptoImpl?.getRandomValues!=='function')throw Error('Secure randomness is required for a new personal creature.');
 const bytes=new Uint8Array(10);cryptoImpl.getRandomValues(bytes);
 return 'P-'+Array.from(bytes,byte=>byte.toString(16).padStart(2,'0')).join('');
}
