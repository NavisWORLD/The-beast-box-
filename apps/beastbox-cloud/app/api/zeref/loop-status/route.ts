import {loopStatus} from '@/lib/loop/loop-status.mjs';
import {safeJson} from '@/lib/security';
export const dynamic='force-static';
/** Every link of the loop, wired or not, with honest labels. Public, read-only, no secrets. */
export async function GET(){return safeJson(200,loopStatus());}
