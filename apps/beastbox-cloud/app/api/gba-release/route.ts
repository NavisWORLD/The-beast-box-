import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export function GET(){
 return NextResponse.json({
  schema:'beast-cage-gba-release-v1',
  source_marker:'beast-cage-lost-cosmos-pr31-2e600160-20261004',
  lost_cosmos_commit:'2e600160937943d3cafcf27e88a0474ba6aba43d',
  lost_cosmos_page:'https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/standalone/SIM_EARTH_7_08_REALITY_BODY.html',
  same_cage_transfer:true,
  features:['guest-visual-test','download-gba-4bpp','qbeast-to-lost-cosmos-share','stable-one-cage-transfer','play-current-lost-cosmos','persistent-gba-player','shared-spark-care-ledger','model-bay-care','optional-explicit-owner-dyn12','in-page-v11-2-spark'],
  rom_release:'lost-cosmos-v11.2-spark',
  rom_asset:'lost-cosmos-v11.2-spark.gba',
  rom_url:'/api/gba-rom',
  emulator:'emulatorjs',
  guest_contains_private_memory:false,gbainference:false,hardware_tested:false
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
