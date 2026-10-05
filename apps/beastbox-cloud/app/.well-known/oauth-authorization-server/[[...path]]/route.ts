import { authorizationServer } from '@/lib/muse/metadata';
import { json, originOf } from '@/lib/muse/server';

export const dynamic = 'force-dynamic';
// RFC 8414 metadata for the Beast Box pairing authorization server.
export async function GET(request: Request) {
  return json(200, authorizationServer(originOf(request)), { 'Access-Control-Allow-Origin': '*' });
}
