import { protectedResource } from '@/lib/muse/metadata';
import { json, originOf } from '@/lib/muse/server';

export const dynamic = 'force-dynamic';
// RFC 9728 metadata for the Meta Muse MCP endpoint (/api/mcp).
export async function GET(request: Request) {
  return json(200, protectedResource(originOf(request)), { 'Access-Control-Allow-Origin': '*' });
}
