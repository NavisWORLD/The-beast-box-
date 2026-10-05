import { discoveryOptions, serverCardResponse } from '@/lib/muse/discovery-http';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// MCP Server Card at <streamable-http-url>/server-card (SEP-2127 reserved location).
export const GET = serverCardResponse;
export const OPTIONS = discoveryOptions;
