import { discoveryOptions, serverCardResponse } from '@/lib/muse/discovery-http';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// The same Server Card at an older draft discovery path, for clients that still probe it.
export const GET = serverCardResponse;
export const OPTIONS = discoveryOptions;
