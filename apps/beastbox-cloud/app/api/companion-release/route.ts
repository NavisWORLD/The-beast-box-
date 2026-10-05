import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export function GET(){
 return NextResponse.json({
  schema:'beastbox-companion-release-v1',
  source_marker:'beastbox-unified-spark-companion-20261004',
  renderer:'spark-beasts-recorded-seed',
  spark_alive_revision:'sol-spark-alive-1',
  game_chat_revision:'sol-spark-game-chat-1',
  in_game_guest_model_chat:true,
  in_game_cage_care:true,
  game_chat_preserves_native_player:true,
  continuous_habitat:true,
  gesture_only_audio:true,
  shared_qbeast_session:true,
  native_earned_evolution:true,
  surfaces:['beast-cage-customize','public-roamer','owner-dock','settings','gba-game-lab'],
  methods:['three-stage-preview','seeded-gait','blink-eyes','mood-reaction','generated-webaudio-voice','same-qbeast-handoff'],
  same_companion_profile:true,
  recorded_quantum_seed:true,
  live_quantum_link:false,
  sim_earth_embedded:false,
  owner_authority_copied:false,
  raw_sensor_media_stored:false,
  public_seed_pack:'owner-upload-20261004',
  public_seed_jobs_added:96,
  public_seed_shards:4,
  raw_circuits_published:false,
  user_ids_published:false,
  original_signal_payloads_published:false,
  derived_counts_public:true
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
