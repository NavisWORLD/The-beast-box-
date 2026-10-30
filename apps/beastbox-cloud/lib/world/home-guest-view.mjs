// Home tiny universe for guests (Oct 30): the embedded living world shows unless the guest picked the pocket explorer (or Classic) on this device.
// Read-only: never writes, never creates an identity.
import {VIEW_STORAGE} from './world-options.mjs';
export function guestPickedPocket(storage=globalThis.localStorage){let raw=null;try{raw=storage?.getItem?.(VIEW_STORAGE)??null;}catch{}return raw==='pocket'||raw==='classic';}
