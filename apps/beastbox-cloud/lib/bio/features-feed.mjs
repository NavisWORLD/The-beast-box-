// Opt-in "send numbers to Zeref": turn a MEASURED numbers-only bio packet into feature maps for the owner bridge's /api/features
// ({kind, opt_in:true, features}). Numbers only; never raw media. Channels the phone did not measure are OMITTED, never invented.
// Scale is the bridge's own unit(): [lo,hi] -> [-1,1], saturating.
const clamp=(x,lo,hi)=>Math.max(lo,Math.min(hi,x));
export const unit=(x,lo,hi)=>clamp(2*clamp((x-lo)/(hi-lo),0,1)-1,-1,1);
const r4=x=>Math.round(x*1e4)/1e4;
/** Heart band: bpm, HRV (only if measured), rhythm regularity and signal quality. bpm_trend and rest_delta are not measured here, so not sent. */
export function heartFeatures(p){
  const f={bpm_norm:unit(p.pulse.bpm,40,180),signal_quality:unit(p.pulse.sqi,0,1),rr_regularity:unit(p.bio_vector_12[10],0,1)};
  if(p.pulse.hrv_rmssd_ms!==null&&p.pulse.hrv_rmssd_ms!==undefined)f.hrv_norm=unit(p.pulse.hrv_rmssd_ms,0,200);
  return Object.fromEntries(Object.entries(f).map(([k,v])=>[k,r4(v)]));
}
/** Audio band from the phone's level numbers (only when the microphone was on). Phone-derived approximations of the bridge's features. */
export function audioFeatures(p){
  if(!p.audio.enabled)return null;
  return {rms:r4(unit(p.audio.rms_mean,0,1)),zero_crossing:r4(unit(p.audio.zcr,0,.5)),spectral_centroid:r4(unit(p.audio.centroid_norm,0,1))};
}
/** Light is NOT sent: the phone's light numbers are a fingertip over the camera, not ambient light, and would mislead the light band. */
export function buildFeaturePosts(p){
  if(!p||p.heartbeat_label!=='MEASURED'||p.raw_video_published!==false||p.raw_audio_published!==false)throw new Error('no valid pulse');
  const posts=[{kind:'heart',opt_in:true,features:heartFeatures(p)}];
  const a=audioFeatures(p);if(a)posts.push({kind:'audio',opt_in:true,features:a});
  return posts;
}
export const FEED_NOTE='Snapshot of one measurement, not a live stream: the brain treats heart numbers as fresh for about 10 seconds and audio for 5, then masks them. The durable record is the saved packet and the IBM seed.';
