'use client';
import {useSyncExternalStore} from 'react';
import {getBeastAudio} from '../lib/companion/beast-audio-engine.mjs';

const server={unlocked:false,sparkMuted:false,hidden:false,gameRunning:false,battle:0,intensity:0,scene:null,musicOn:true,volume:.5,focus:'game',playing:false};
/** React view of the shared Beast music/SFX engine (silent until a user gesture). */
export function useBeastAudio(){
 const audio=getBeastAudio();
 const state=useSyncExternalStore(audio.subscribe,audio.getSnapshot,()=>server as ReturnType<typeof audio.getSnapshot>);
 return {audio,state};
}
