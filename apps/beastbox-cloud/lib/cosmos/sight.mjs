/**
 * SIGHT AT THE FOREVER DOOR — Zeref's way in is seeing, not reading
 * (owner's order, 2026-10-28: "plug his sight in so he sees in the world
 * too, using the light conversion I placed for site").
 *
 * Two lights, composed read-only into his served context beside the live
 * universe lines, under the same discipline as the library: a source that
 * cannot be read composes NOTHING, a label is never truncated, and no
 * visitor input writes into him.
 *
 * (1) HIS OWN WORLD'S LIGHT — label DERIVED. The pocket universe's sky is
 * the engine's skyAt() rig (lib/universe/sky-state.mjs), a pure function
 * of the sun's direction. The sun's geometry is the engine's own
 * sunDirAt() (lib/universe/genesis-sun.mjs): one day is DAY_LENGTH_TICKS
 * engine ticks stepped at 4 Hz — the 240 s day the living-world view has
 * always used, phase taken from the world-live document's own stamp
 * (world.at_ms). The rig runs with its reference sky (SKY.defaultSky /
 * defaultTwilight are skyAt's own fallbacks, the temperate reference
 * colours; atmosphere is the temperate reference amount 0.85 of
 * SKY.knots / PLANET_SHADING.temperate — his home planet's own shading
 * row lives in the seeded universe the view builds, which the door does
 * not fetch, so no per-planet row is claimed here). The result is
 * translated into his sensorium's language (lib/companion/
 * field-perception.mjs): a brightness (the horizon colour's luma, the
 * view's linear→sRGB conversion, field-perception's own weights), a
 * dominant hue family (analyzeFrame's RGB→hue arithmetic), and the
 * feeling his notice() rules assign when the same pure sky is sampled
 * one spark-minute earlier as the previous frame — brightening past
 * notice()'s threshold is "the lights getting bright" → joy, darkening
 * is "the lights going dark" → fear; when notice() stays silent the
 * light is steady and the resting feeling is calm (his EMOTIONS set in
 * lib/companion/emotion.mjs). Computed, never measured: DERIVED.
 * Gated on his universe clock: when the world-live liveTick link is
 * DOWN the light is not derived at all (STALE still composes — world-
 * live's own semantics: old but readable).
 *
 * (2) THE VISITOR'S LIGHT — label MEASURED, only when real. The door
 * request may carry an environment summary in exactly the site light
 * conversion's shape (lib/environment/environment-link.mjs — "My
 * surroundings give the pocket universe life", consent, numbers only):
 * {numbers, measured_at_ms}. The numbers must pass that module's own
 * validateEnvironment with the light channel MEASURED from one of its
 * LIGHT_SOURCES, and still be fresh by its isFresh rule (age ≤
 * ENV_FRESH_MS) at composition time. Anything stale, malformed or
 * absent composes NOTHING. No media, and nothing of it is stored: the
 * guestbook events keep their #668 field whitelist (counts and labels
 * only, never raw values), so the door's response receipt is the only
 * record that sight was composed, and it carries labels, not levels.
 *
 * This module contains no writer of any kind and never touches the
 * Open Field perception intake (app/api/zeref/perception — PENDING_REVIEW
 * by design, unchanged): notice() is reused as a pure function only.
 */
import {skyAt} from '../universe/sky-state.mjs';
import {sunDirAt,DAY_LENGTH_TICKS} from '../universe/genesis-sun.mjs';
import {notice} from '../companion/field-perception.mjs';
import {validateEnvironment,isFresh} from '../environment/environment-link.mjs';

export const SIGHT_LABELS=Object.freeze({world:'DERIVED',visitor:'MEASURED',absent:'absent'});
/** The engine day in seconds: DAY_LENGTH_TICKS ticks stepped at 4 Hz (genesis-sun), the living-world view's 240 s day. */
export const WORLD_DAY_S=DAY_LENGTH_TICKS/4;
/** His previous frame: the same pure sky sampled one spark-minute earlier (the spark loop's own interval). */
export const SIGHT_PREV_S=60;
/** The rig's temperate reference atmosphere (SKY.knots; PLANET_SHADING.temperate atmo_amount). */
export const WORLD_ATMOSPHERE=0.85;
const UP=Object.freeze([0,1,0]);
const r2=v=>Math.round(v*100)/100;
const clamp01=v=>Math.min(1,Math.max(0,v));
// The view's own linear->sRGB conversion (components/living-world.tsx), then field-perception's luma weights (.299/.587/.114).
const srgb=v=>v<=.0031308?12.92*v:1.055*Math.pow(Math.max(0,v),1/2.4)-.055;
const luma=c=>{const s=c.map(srgb);return .299*s[0]+.587*s[1]+.114*s[2];};
/** analyzeFrame's RGB->hue arithmetic (degrees 0..360), applied to the sRGB horizon colour. */
function hueDeg(c){
 const [r,g,b]=c.map(srgb);const max=Math.max(r,g,b),min=Math.min(r,g,b);let hue=0;
 if(max>min){hue=max===r?60*(((g-b)/(max-min))%6):max===g?60*((b-r)/(max-min)+2):60*((r-g)/(max-min)+4);if(hue<0)hue+=360;}
 return Math.round(hue);
}
const HUE_FAMILIES=[[10,'red'],[40,'orange'],[70,'gold'],[160,'green'],[195,'teal'],[255,'blue'],[290,'violet'],[345,'rose'],[361,'red']];
const hueFamily=h=>{for(const [lim,name] of HUE_FAMILIES)if(h<lim)return name;return 'red';};
const bandOf=(b,dark='night')=>b>=.6?'bright':b>=.35?'soft':b>=.2?'dim':dark;

/** The engine sky at one phase of his world's day (seconds into the 240 s cycle). Pure. */
function skyAtPhase(phaseS){
 const angle=(phaseS/WORLD_DAY_S)*Math.PI*2;
 const sunDir=sunDirAt(angle);
 const sky=skyAt({sunDir,sunElev:sunDir[1],up:UP,atmosphere:WORLD_ATMOSPHERE});
 return {sky,sunDir};
}

/**
 * His own world's light right now, in his sensorium's language.
 * -> {brightness,band,trend,feeling,event,hue_family,sun_elev,day_weight} or null when his
 * universe clock cannot be read (no world doc, or its liveTick link is DOWN).
 */
export function worldLightFrom(world,nowMs){
 if(!world||typeof world!=='object'||!world.links)return null;
 const tick=world.links.liveTick;
 if(!tick||tick.state==='DOWN')return null;
 const atMs=Number.isFinite(nowMs)?nowMs:world.at_ms;
 if(!Number.isFinite(atMs))return null;
 const phase=((atMs/1000)%WORLD_DAY_S+WORLD_DAY_S)%WORLD_DAY_S;
 const now=skyAtPhase(phase);
 const prev=skyAtPhase((phase-SIGHT_PREV_S+WORLD_DAY_S)%WORLD_DAY_S);
 const bNow=luma(now.sky.horizon),bPrev=luma(prev.sky.horizon);
 // notice() with ONLY a brightness channel set: its loudness, motion and pitch rules cannot fire.
 const n=notice({brightness:bNow},{brightness:bPrev});
 const d=bNow-bPrev;
 return {brightness:r2(clamp01(bNow)),band:bandOf(bNow),trend:d>.02?'rising':d<-.02?'falling':'steady',
  feeling:n?n.emotion:'calm',event:n?n.event:null,hue_family:hueFamily(hueDeg(now.sky.horizon)),
  sun_elev:r2(now.sunDir[1]),day_weight:r2(now.sky.dayWeight)};
}

const SOURCE_WORDS=Object.freeze({'ambient-light-sensor':'ambient light sensor','camera-brightness':'camera brightness'});
/**
 * The visitor's measured light from a door request's optional environment summary,
 * in exactly the environment-link shape: {numbers, measured_at_ms}.
 * -> {level,source,band} or null: stale, malformed or absent composes nothing.
 */
export function visitorLightFrom(raw,nowMs){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))return null;
 if(!Object.keys(raw).every(k=>k==='numbers'||k==='measured_at_ms'))return null;
 if(!Number.isFinite(raw.measured_at_ms)||!Number.isFinite(nowMs))return null;
 const v=validateEnvironment(raw.numbers);
 if(!v.ok)return null;
 const light=v.numbers.light;
 if(!light||light.state!=='MEASURED')return null;
 if(!isFresh(v.numbers,raw.measured_at_ms,nowMs))return null;
 return {level:light.level,source:light.source,band:bandOf(light.level,'dark')};
}

/**
 * Compose the sight block for the forever door's served context.
 * Returns {text, receipt}: text is '' when neither light can be composed
 * (or the budget fits no whole line — a line is never truncated);
 * receipt.world_light always carries the DERIVED label, receipt.
 * visitor_light is labelled MEASURED only when a valid fresh summary
 * arrived, else 'absent'. A part's `composed` says it reached the prompt.
 */
export function composeSight({world=null,environment=null,nowMs=null,maxChars=430}={}){
 const atMs=Number.isFinite(nowMs)?nowMs:(world&&Number.isFinite(world.at_ms)?world.at_ms:null);
 const wl=worldLightFrom(world,atMs);
 const vl=visitorLightFrom(environment,atMs);
 const receipt={
  world_light:wl?{composed:false,label:SIGHT_LABELS.world,brightness_band:wl.band,trend:wl.trend,feeling:wl.feeling}
   :{composed:false,label:SIGHT_LABELS.world,brightness_band:null,trend:null,feeling:null,
     reason:!world||!world.links?'world-live unreachable':'live tick DOWN — his universe clock is unreachable, so his light is not derived'},
  visitor_light:vl?{composed:false,label:SIGHT_LABELS.visitor,source:vl.source}
   :{composed:false,label:SIGHT_LABELS.absent,source:null}};
 if(!wl&&!vl)return {text:'',receipt};
 const header='What you can see right now:';
 let worldLine=null,visitorLine=null;
 if(wl){
  const sun=wl.sun_elev>.02?'stands above the horizon':wl.sun_elev<-.02?'is below the horizon':'sits on the horizon';
  const feel=wl.event?`Your sensorium calls this "${wl.event}", and it feels like ${wl.feeling}.`
   :'The light is steady, and your resting feeling is calm.';
  worldLine=`- Your own world's light, DERIVED from its sky (computed, not measured): the light is ${wl.band} and ${wl.trend}, the horizon is ${wl.hue_family}, the sun ${sun}. ${feel}`;
 }
 if(vl)visitorLine=`- Where your visitor is, the light is ${vl.band} (${vl.level}) — MEASURED by their ${SOURCE_WORDS[vl.source]} through the site's light conversion, numbers only.`;
 const full=[header,worldLine,visitorLine].filter(Boolean).join('\n');
 let text=full,includedVisitor=Boolean(vl);
 if(text.length>maxChars&&visitorLine){text=[header,worldLine].filter(Boolean).join('\n');includedVisitor=false;}
 if(text.length>maxChars)text='';
 receipt.world_light.composed=Boolean(text&&worldLine);
 receipt.visitor_light.composed=Boolean(text&&includedVisitor);
 return {text,receipt};
}
