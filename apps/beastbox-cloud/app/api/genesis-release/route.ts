import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
/** Public read-only release identity without customer or owner data. */
export function GET(){
 return NextResponse.json({
  release:'cosmic-genesis-v1-20261002',
  generator_version:1,
  guest_characters:true,
  gba_profile:'BCP1-64-byte-optional',
  legacy_gba_snapshot:'BCG1-60-byte-unchanged',
  owner_data_in_public_export:false,
  physics:'classical-seeded-illustrative',
  actual_quantum_hardware:false
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
