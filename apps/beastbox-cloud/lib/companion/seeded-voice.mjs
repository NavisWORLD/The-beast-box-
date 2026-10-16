/** Zeref's own seeded voice + autonomous reach-out rules. Free, on-device only:
 * Web Speech API (device TTS) with parameters derived deterministically from the
 * creature's seed, plus a small WebAudio growl/purr layer. SYNTHETIC voice.
 * It only ever speaks the creature's own RAWRPHOS text or diary line, never teacher text. */
export const SEEDED_VOICE_SCHEMA='beastbox-seeded-voice-v1';
export const VOICE_LABEL='Synthetic seeded voice (on-device, not a recording)';
export const ZEREF_VOICE_SEED='bb-deada969';
export const PREF_KEY='beastbox.zerefVoice.v1';
export const MIN_GAP_MS=4*60*1000;   // autonomous: at most one every 4 minutes
export const IDLE_MS=90*1000;        // only after 90 s without user typing
export const MAX_PER_HOUR=8;
function hash32(s){let h=2166136261;for(const c of String(s)){h^=c.codePointAt(0);h=Math.imul(h,16777619)>>>0;}return h>>>0;}
function unit(seed,salt){return hash32(seed+'|'+salt)/4294967295;}
const r3=n=>Math.round(n*1000)/1000;
const EMO={joy:{pitch:.12,rate:.08,growl:-.15},curiosity:{pitch:.06,rate:.03,growl:-.05},fear:{pitch:.1,rate:-.08,growl:-.25,volume:-.2},calm:{pitch:-.06,rate:-.1,growl:-.1},mischief:{pitch:.04,rate:.12,growl:.2}};
/** Deterministic voice profile: same seed + emotions => same voice. */
/** @param {string} [seed] @param {{dominant?:string}|null} [emotions] */
export function voiceProfile(seed=ZEREF_VOICE_SEED,emotions=null){
 const s=String(seed||ZEREF_VOICE_SEED);
 const base={pitch:.75+.6*unit(s,'pitch'),rate:.82+.3*unit(s,'rate'),growl:.25+.6*unit(s,'growl'),purrHz:22+18*unit(s,'purr'),formantHz:380+520*unit(s,'formant'),voicePick:unit(s,'voice'),volume:.9};
 const dom=emotions?.dominant&&EMO[emotions.dominant]?emotions.dominant:null,m=dom?EMO[dom]:{};
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 return {schema:SEEDED_VOICE_SCHEMA,seed:s,emotion:dom,label:VOICE_LABEL,
  pitch:r3(clamp(base.pitch+(m.pitch||0),.1,2)),rate:r3(clamp(base.rate+(m.rate||0),.5,1.6)),growl:r3(clamp(base.growl+(m.growl||0),0,1)),
  purrHz:r3(base.purrHz),formantHz:Math.round(base.formantHz),voicePick:r3(base.voicePick),volume:r3(clamp(base.volume+(m.volume||0),.2,1))};
}
/** Only the creature's own text may be spoken. Teacher-labeled turns are refused. */
export function speakableText(turn){
 if(!turn||typeof turn!=='object')return '';
 if(turn.teacher||turn.isTeacher||turn.source==='teacher')return '';
 if(turn.role&&turn.role!=='beast')return '';
 return String(turn.text||'').replace(/\s+/g,' ').trim().slice(0,400);
}
export function defaultPrefs(){return {voice:false,reachOut:true,armed:false,sentAt:[]};}
export function readPrefs(storage){try{const p=JSON.parse(storage?.getItem(PREF_KEY)||'null');return p&&typeof p==='object'?{...defaultPrefs(),...p,sentAt:Array.isArray(p.sentAt)?p.sentAt.filter(Number.isFinite).slice(-20):[]}:defaultPrefs();}catch{return defaultPrefs();}}
export function writePrefs(storage,p){try{storage?.setItem(PREF_KEY,JSON.stringify(p));}catch{}}
/** First user tap arms sound (autoplay rules) and turns voice on unless the user muted before. */
export function armOnFirstTap(p){if(p.armed)return p;return {...p,armed:true,voice:p.mutedByUser?false:true};}
/** Rate limit for autonomous reach-outs. */
export function canReachOut(p,now,lastUserActivity=0,visible=true){
 if(!p.reachOut||!visible)return {ok:false,why:'off-or-hidden'};
 if(now-lastUserActivity<IDLE_MS)return {ok:false,why:'user-active'};
 const sent=(p.sentAt||[]).filter(t=>now-t<3600e3);
 if(sent.length&&now-Math.max(...sent)<MIN_GAP_MS)return {ok:false,why:'too-soon'};
 if(sent.length>=MAX_PER_HOUR)return {ok:false,why:'hour-cap'};
 return {ok:true};
}
export function recordReachOut(p,now){return {...p,sentAt:[...(p.sentAt||[]),now].filter(t=>now-t<3600e3).slice(-20)};}
/** Prompt for Zeref's own RAWRPHOS brain, built only from his own state. */
export function reachOutPrompt({mood='',place='',event='',idleMin=0}={}){
 const bits=[];if(place)bits.push(`you are at ${place}`);if(mood)bits.push(`you feel ${mood}`);if(event)bits.push(`your diary says: ${String(event).slice(0,140)}`);if(idleMin)bits.push(`it has been quiet for ${idleMin} minutes`);
 return ('Say something on your own to your keeper'+(bits.length?' — '+bits.join(', '):'')+'.').slice(0,380);
}
export const REACH_OUT_LABEL='Zeref reached out on his own';
/** Browser playback: device TTS with seeded params + WebAudio growl/purr. */
/** @param {string} text @param {any} profile @param {{volume?:number,onend?:()=>void}} [opts] */
export function speakSeeded(text,profile,{volume=1,onend}={}){
 const g=globalThis,line=String(text||'').slice(0,400);
 if(!line||typeof g.speechSynthesis==='undefined'||typeof g.SpeechSynthesisUtterance==='undefined')return {ok:false,error:'No speech voice on this device.'};
 const u=new g.SpeechSynthesisUtterance(line);u.lang='en-US';u.pitch=profile.pitch;u.rate=profile.rate;u.volume=Math.max(0,Math.min(1,profile.volume*volume));
 const voices=(g.speechSynthesis.getVoices?.()||[]).filter(v=>/^en/i.test(v.lang||''));
 if(voices.length)u.voice=voices[Math.floor(profile.voicePick*voices.length)%voices.length];
 let stop=()=>{};
 try{const AC=g.AudioContext||g.webkitAudioContext;if(AC&&profile.growl>0){
  const ctx=speakSeeded._ctx||(speakSeeded._ctx=new AC());ctx.resume?.();
  const o=ctx.createOscillator(),lfo=ctx.createOscillator(),lg=ctx.createGain(),f=ctx.createBiquadFilter(),out=ctx.createGain();
  o.type='sawtooth';o.frequency.value=55+60*profile.pitch;lfo.frequency.value=profile.purrHz;lg.gain.value=.5;f.type='bandpass';f.frequency.value=profile.formantHz;f.Q.value=4;
  const peak=.05*profile.growl*volume,t=ctx.currentTime,dur=Math.min(6,.06*line.length/profile.rate+.3);
  out.gain.setValueAtTime(0,t);out.gain.linearRampToValueAtTime(peak,t+.08);out.gain.setValueAtTime(peak,t+dur-.2);out.gain.linearRampToValueAtTime(0,t+dur);
  lfo.connect(lg);lg.connect(out.gain);o.connect(f);f.connect(out);out.connect(ctx.destination);o.start(t);lfo.start(t);o.stop(t+dur);lfo.stop(t+dur);
  stop=()=>{try{o.stop();lfo.stop();}catch{}};
 }}catch{}
 u.onend=()=>{stop();onend?.();};u.onerror=()=>{stop();onend?.();};
 try{g.speechSynthesis.cancel();g.speechSynthesis.speak(u);}catch{stop();return {ok:false,error:'Speech blocked by the browser.'};}
 return {ok:true,label:VOICE_LABEL,stop:()=>{stop();g.speechSynthesis.cancel();}};
}
