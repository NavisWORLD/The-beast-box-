import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export function GET(){
 return NextResponse.json({
  schema:'beastbox-companion-release-v1',
  source_marker:'beastbox-unified-spark-companion-20261004',
  renderer:'spark-beasts-recorded-seed',
  surfaces:['beast-cage-customize','public-roamer','owner-dock','settings','gba-game-lab'],
  methods:['three-stage-preview','seeded-gait','blink-eyes','mood-reaction','generated-webaudio-voice','same-qbeast-handoff'],
  same_companion_profile:true,
  recorded_quantum_seed:true,
  live_quantum_link:false,
  sim_earth_embedded:false,
  owner_authority_copied:false,
  raw_sensor_media_stored:false
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
