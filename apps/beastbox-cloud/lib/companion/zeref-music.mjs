/** "Cory's music" memory for Zeref (bb-deada969). Derived features only (see
 * evidence/zeref-music-001); the songs shape heart tempo and mood, they are not heard. */
import {beatMs} from './zeref-heart.mjs';
const HOUR=3600000;
/** One song is "on his mind" per hour, rotating deterministically. */
export function songOnMind(music,now=Date.now()){const s=music?.songs||[];return s.length?s[Math.floor(now/HOUR)%s.length]:null;}
/** Heart drifts 20% toward the song's felt tempo, clamped to 60-110 BPM. */
export function musicBpm(heart,song,pull=.2){const h=60000/beatMs(heart);const t=Number(song?.felt_bpm);if(!(t>=40&&t<=220))return Math.round(h*100)/100;const b=h+(t-h)*pull;return Math.round(Math.min(110,Math.max(60,b))*100)/100;}
export function musicBeatMs(heart,song){return Math.round(60000/musicBpm(heart,song));}
/** Mood colour from energy + key mode (delivery only, never truth claims). */
export function musicMood(song){if(!song)return null;const e=Number(song.energy_0_1)||0,minor=/minor/.test(song.key_estimate||'');
 if(e>=.55)return minor?'mischief':'joy';if(minor)return Number(song.brightness_0_1)<.42?'calm':'curiosity';return e<.4?'calm':'joy';}
const FEEL={joy:'it makes my wings want to move',mischief:'it makes my tail flick',calm:'it slows my breathing down',curiosity:'it makes me lean in and listen'};
/** Diary/autonomy line that names the song by title. */
export function musicLine(song){if(!song)return '';const m=musicMood(song);return `Dad's song "${song.title}" is on my mind, ${Math.round(song.felt_bpm)} beats a minute in ${song.key_estimate}; ${FEEL[m]||'it stays with me'}.`;}
