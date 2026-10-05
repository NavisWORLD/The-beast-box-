import { catalogResponse, discoveryOptions } from '@/lib/muse/discovery-http';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// AI Catalog: domain-level MCP discovery entrypoint that points at /api/mcp/server-card.
export const GET = catalogResponse;
export const OPTIONS = discoveryOptions;
