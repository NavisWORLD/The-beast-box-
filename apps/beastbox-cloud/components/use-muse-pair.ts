'use client';
import {useSyncExternalStore} from 'react';
import {getMusePair} from '../lib/companion/muse-pair.mjs';

const server={supported:false,status:'checking',message:'Checking for Web Bluetooth…',deviceName:'',battery:null,bands:{delta:0,theta:0,alpha:0,beta:0,gamma:0},traits:null,
 signal:{available:false,mode:'off',focus:0,calm:0,spark:0,reason:'signal-off'},influence:{active:false,mood:'idle',energy:.5,intensity:0},windows:0};
/** React view of the shared Pair Muse link (opt-in; nothing is uploaded). */
export function useMusePair(){
 const muse=getMusePair();
 const state=useSyncExternalStore(muse.subscribe,muse.getSnapshot,()=>server as unknown as ReturnType<typeof muse.getSnapshot>);
 return {muse,state};
}
