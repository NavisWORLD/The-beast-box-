import { SCOPES } from './auth.mjs';
import { mcpUrl } from './server';

export function protectedResource(origin: string) {
  return {
    resource: mcpUrl(origin),
    authorization_servers: [origin],
    scopes_supported: SCOPES,
    bearer_methods_supported: ['header'],
    resource_name: 'Beast Box (one paired virtual pet)',
    resource_documentation: 'https://github.com/NavisWORLD/The-beast-box-/blob/main/docs/meta-muse-connector.md',
  };
}

export function authorizationServer(origin: string) {
  return {
    issuer: origin,
    authorization_endpoint: origin + '/connect/meta-muse',
    token_endpoint: origin + '/api/muse/oauth/token',
    registration_endpoint: origin + '/api/muse/oauth/register',
    revocation_endpoint: origin + '/api/muse/oauth/revoke',
    response_types_supported: ['code'],
    response_modes_supported: ['query'],
    grant_types_supported: ['authorization_code', 'refresh_token'],
    code_challenge_methods_supported: ['S256'],
    token_endpoint_auth_methods_supported: ['none'],
    revocation_endpoint_auth_methods_supported: ['none'],
    scopes_supported: SCOPES,
    service_documentation: 'https://github.com/NavisWORLD/The-beast-box-/blob/main/docs/meta-muse-connector.md',
  };
}
