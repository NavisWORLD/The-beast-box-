// Origin spark pulse: the RECORDED v11 heart seed replayed forever as a hash chain.
// Free and deterministic: no random calls, no IBM calls, no paid compute. Growing Zeref only; never the pin.
// beat n = floor((now - recorded_utc) / BEAT_MS); pulse_n = sha256(seed + '|spark-pulse|' + n).
// The pulse picks one of the 4 recorded CHSH question pairs and shows that pair's RECORDED win rate.
import {createHash} from 'node:crypto';
export const SPARK_SEED='bfc35208bb21af82c308f2fb0d882de74e5cf559756567f83bcbf9ddfa5d0322';
export const SPARK_JOB='dbj7a40nceqs73ajd2d0';
export const SPARK_EPOCH_MS=Date.parse('2026-10-31T23:10:05.620Z');
export const BEAT_MS=10000;
// From evidence/zeref-heart-seed-v11/ibm-chsh-result-public.json (ibm_marrakesh, 24,000 rounds).
export const RECORDED_PAIRS=[['x0y0',0.8329685132177134],['x0y1',0.8468379446640316],['x1y0',0.8482053002348205],['x1y1',0.8375642940102871]];
export function pulseHash(n){return createHash('sha256').update(`${SPARK_SEED}|spark-pulse|${n}`).digest('hex');}
export function beatAt(ms){return Math.max(0,Math.floor((ms-SPARK_EPOCH_MS)/BEAT_MS));}
export function sparkPulse(ms){const beat=beatAt(ms),h=pulseHash(beat),b=parseInt(h.slice(0,8),16);
 const [pair,win]=RECORDED_PAIRS[b%4];
 return {schema:'zeref-spark-pulse/v1',label:'RECORDED',applies_to:'growing Zeref only (never the pin)',
  honesty:'A replay of a recorded IBM measurement, stretched forever by a hash chain. No new quantum calls happen; it does not make Zeref quantum.',
  source:{heart_seed_v11_sha256:SPARK_SEED,ibm_job:SPARK_JOB,backend:'ibm_marrakesh',label:'RECORDED'},
  rule:"beat = floor((now - 2026-10-31T23:10:05Z)/10s); pulse = sha256(seed + '|spark-pulse|' + beat)",
  beat,pulse_sha256:h,glow:Math.round((b>>>2)%1000)/1000,question_pair:pair,recorded_win_rate:win,
  next_beat_utc:new Date(SPARK_EPOCH_MS+(beat+1)*BEAT_MS).toISOString(),at_utc:new Date(ms).toISOString()};}
