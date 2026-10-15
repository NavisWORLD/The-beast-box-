import {safeJson} from '@/lib/security';
export const runtime='nodejs';
export const dynamic='force-dynamic';
/** Voice capability status only: a boolean, never the key. Synthesis is not wired until a key exists and is reviewed. */
export async function GET(){
 const key=process.env.GROK_TTS_API_KEY||process.env.XAI_API_KEY||'';
 return safeJson(200,{schema:'beastbox-voice-v1',browser:true,grok:key.length>=20,synthesis:'not-implemented-until-configured'});
}
