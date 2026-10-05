import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { authenticate, getAccount } from '@/lib/muse/auth.mjs';
import { SERVER_VERSION } from '@/lib/muse/discovery.mjs';
import { createBridgeTalk } from '@/lib/muse/bridge-talk.mjs';
import { rateLimit } from '@/lib/muse/rate-limit.mjs';
import { callTool, listTools } from '@/lib/muse/tools.mjs';
import { NO_STORE, json, limited, mcpUrl, museStore, noStorage, originOf } from '@/lib/muse/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 60;

const INSTRUCTIONS = 'Beast Box connector for one paired virtual pet ("beast"). Read tools return the care save the owner\'s browser last synced. ' +
  'Write tools change only that beast\'s care save and are applied in the browser on its next sync. talk_to_beast returns an in-character reply ' +
  'from a game companion model; it is a game character, not a conscious mind. Nothing here buys, sends or shares anything.';

function unauthorized(origin: string, error = 'invalid_token', description = 'Pair Beast Box with Meta Muse and send a valid Bearer token.') {
  return json(401, { error, error_description: description }, {
    'WWW-Authenticate': `Bearer realm="beastbox", error="${error}", resource_metadata="${origin}/.well-known/oauth-protected-resource/api/mcp", scope="beast.read beast.care"`,
  });
}

export async function POST(request: Request) {
  const origin = originOf(request);
  const sent = request.headers.get('origin');
  if (sent && sent !== origin && sent !== new URL(request.url).origin) return json(403, { error: 'origin_not_allowed' });
  const store = museStore();
  if (!store) return noStorage();
  const header = request.headers.get('authorization');
  if (!header) return unauthorized(origin, 'invalid_request', 'Missing Bearer token.');
  const auth = await authenticate(store, header);
  if (!auth) return unauthorized(origin);
  const busy = await limited(store, 'mcp', auth.accountId);
  if (busy) return busy;
  if (Number(request.headers.get('content-length') || 0) > 64000) return json(413, { error: 'request_too_large' });

  const account = await getAccount(store, auth.accountId);
  const server = new Server({ name: 'beastbox', title: (account && account.deviceName) || 'Beast Box', version: SERVER_VERSION }, { capabilities: { tools: {} }, instructions: INSTRUCTIONS });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: listTools() as any }));
  server.setRequestHandler(CallToolRequestSchema, async (req) => (await callTool(req.params.name, (req.params.arguments || {}) as Record<string, unknown>, {
    store,
    auth,
    limit: (bucket: string) => rateLimit(store, bucket, auth.accountId),
    talk: createBridgeTalk(auth.accountId) || undefined,
  })) as any);
  const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
  await server.connect(transport);
  try {
    const response = await transport.handleRequest(request, {
      authInfo: { token: 'redacted', clientId: auth.clientId, scopes: auth.scope.split(' '), extra: { accountId: auth.accountId } },
    });
    const headers = new Headers(response.headers);
    for (const [k, v] of Object.entries(NO_STORE)) headers.set(k, v);
    return new Response(response.body, { status: response.status, headers });
  } finally {
    // Stateless: one server per request. Closing after the JSON body is built.
    void server.close().catch(() => undefined);
  }
}

function notAllowed(request: Request) {
  const origin = originOf(request);
  return json(405, { error: 'method_not_allowed', error_description: `This stateless MCP server accepts POST (Streamable HTTP, JSON responses) at ${mcpUrl(origin)}.` }, { Allow: 'POST' });
}
export const GET = notAllowed;
export const DELETE = notAllowed;
