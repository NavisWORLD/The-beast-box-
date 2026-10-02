import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export function GET(){
 return NextResponse.json({
  schema:'beast-cage-gba-release-v1',source_marker:'beast-cage-guest-gba-20261001',
  features:['guest-visual-test','download-gba-4bpp','optional-explicit-owner-dyn12'],
  guest_contains_private_memory:false,gbainference:false,hardware_tested:false
 },{headers:{'Cache-Control':'no-store, max-age=0'}});
}
