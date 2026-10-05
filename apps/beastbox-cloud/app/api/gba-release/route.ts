import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export function GET(){
 return NextResponse.json({
  schema:'beast-cage-gba-release-v1',
  source_marker:'beast-cage-lost-cosmos-spark-alive-20261004',
  lost_cosmos_commit:'5dd5ea0081ef61922f0a7b4b394736c9ac321629',
  // Game repo main now includes PR #33 (Act I story, chiptune music and SFX, padding and flicker fixes) on top of
  // #34, #35 and controller bridge #38. The ROM bytes stay V11.3; #38 fixes browser input routing into the mounted core.
  lost_cosmos_main_commit:'e5eb46e36096a6c024f6c035923d821d18833f41',
  lost_cosmos_main_prs:[33,34,35,38,39],
  lost_cosmos_page:'https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/arcade/sol-spark-gate/?mode=handheld',
  same_cage_transfer:true,
  features:['guest-visual-test','download-gba-4bpp','qbeast-to-lost-cosmos-share','stable-one-cage-transfer','play-current-lost-cosmos','persistent-gba-player','shared-spark-care-ledger','model-bay-care','optional-explicit-owner-dyn12','in-page-v11-2-spark','lost-cosmos-field','continuous-public-spark','gesture-generated-voice','same-qbeast-native-art','procedural-beast-music','beast-boy-controller-bridge','beast-boy-android-touch-direct','cache-busted-controller-receiver'],
  rom_release:'current-verified-v11.3',
  rom_sha256:'6f9c22fa22b32694d606c854b4da26b4394b2ecaa86842cc1998c8cfe57b1fb3',
  rom_asset:'lost-cosmos-v11.3.gba',
  rom_url:'/api/gba-rom',
  sim_earth_embedded:false,
  emulator:'emulatorjs',
  guest_contains_private_memory:false,gbainference:false,hardware_tested:false
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
