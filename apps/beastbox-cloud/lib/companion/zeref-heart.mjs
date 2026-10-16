/** Zeref's heart rhythm, derived from Cory's heartbeat recording (features only; see
 * evidence/zeref-heartbeat-001). A rhythm/creative seed, not a biological signal. */
export const HEART_FALLBACK=Object.freeze({bpm:72.29,beat_interval_ms:830,packet_sha256:'4f02b66d9b677dfb7407ed60f1fcda03103f60a8c912d11b0c59d52445cb0e94'});
export function beatMs(heart){const b=Number(heart?.bpm);return b>=30&&b<=220?Math.round(60000/b):HEART_FALLBACK.beat_interval_ms;}
/** Autonomy tick = a whole number of heartbeats (about 30 s). */
export function autonomyTickMs(heart,beats=36){return beatMs(heart)*beats;}
/** Mood nudges speed the heart a little (delivery only, never truth claims). */
export function moodBeatMs(heart,emotion){const f={joy:.9,mischief:.85,fear:.8,curiosity:.95,calm:1.1}[emotion]||1;return Math.round(beatMs(heart)*f);}
