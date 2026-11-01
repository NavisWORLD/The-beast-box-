import {sparkPulse} from '@/lib/zeref/spark-pulse.mjs';
export const dynamic='force-dynamic';
export function GET(){return Response.json(sparkPulse(Date.now()),{headers:{'cache-control':'no-store'}});}
