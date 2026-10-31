// Prints his world's light, DERIVED from its sky (same worldLightFrom() as the forever door), as JSON. Read-only GET of /api/world/live.
import {worldLightFrom} from '../apps/beastbox-cloud/lib/cosmos/sight.mjs';
const site=process.env.ZEREF_SITE||'https://www.beastboxcosmos.xyz';
const live=await fetch(site+'/api/world/live').then(r=>r.ok?r.json():null).catch(()=>null);
const wl=worldLightFrom(live,live?.at_ms);
process.stdout.write(JSON.stringify(wl?{label:'DERIVED',at_ms:live.at_ms,...wl}:null)+'\n');
