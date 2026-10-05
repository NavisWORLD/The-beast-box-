import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export function GET(){
 return NextResponse.json({
  schema:'beast-cage-gba-release-v1',
  source_marker:'beast-cage-lost-cosmos-spark-alive-20261004',
  lost_cosmos_commit:'f2c3683f697b7ee5d35557028c4416556226bb9b',
  lost_cosmos_page:'https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/sol-spark-gate/?mode=handheld',
  same_cage_transfer:true,
  features:['guest-visual-test','download-gba-4bpp','qbeast-to-lost-cosmos-share','stable-one-cage-transfer','play-current-lost-cosmos','persistent-gba-player','shared-spark-care-ledger','model-bay-care','optional-explicit-owner-dyn12','in-page-v11-2-spark','lost-cosmos-field','continuous-public-spark','gesture-generated-voice','same-qbeast-native-art'],
  rom_release:'current-verified-v11.2-spark',
  rom_sha256:'303865b4d1c9d0297e5b59e3945e5ee74dbafdcc344aec8deb9434ab87f9899a',
  rom_asset:'lost-cosmos-v11.2-spark.gba',
  rom_url:'/api/gba-rom',
  sim_earth_embedded:false,
  emulator:'emulatorjs',
  guest_contains_private_memory:false,gbainference:false,hardware_tested:false
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
