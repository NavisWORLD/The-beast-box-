/**
 * Standards-based discovery for the Beast Box MCP connector.
 *
 * A client given only the site's base URL can find /api/mcp and its auth through:
 *   /.well-known/ai-catalog.json            AI Catalog -> Server Card URL (SEP-2127 discovery entrypoint)
 *   /.well-known/mcp/catalog.json           same catalog (MCP catalog alias)
 *   /api/mcp/server-card                    MCP Server Card v1 (application/mcp-server-card+json)
 *   /.well-known/mcp.json, /.well-known/mcp-server-card   the card at older draft paths (SEP-1649 / early SEP-2127)
 *   /.well-known/oauth-protected-resource[/api/mcp]   RFC 9728
 *   /.well-known/oauth-authorization-server           RFC 8414 (with RFC 7591 registration_endpoint)
 *
 * Meta Muse has no public third-party device-discovery API (only Meta hardware pairs that
 * way), so nothing here claims to be found by Muse automatically. PAIRING_METHODS keeps the
 * pairing paths in one registry so an official Muse device-pairing API can be added later
 * without touching the MCP server or OAuth code.
 */
export const SERVER_CARD_SCHEMA = "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json";
export const SERVER_CARD_TYPE = "application/mcp-server-card+json";
export const CATALOG_TYPE = "application/ai-catalog+json";
export const SERVER_NAME = "io.github.navisworld/beastbox";
export const SERVER_VERSION = "1.0.0";
import { SUPPORTED_PROTOCOL_VERSIONS } from "@modelcontextprotocol/sdk/types.js";
export { pairingLink, parsePairingFragment } from "./pairing-link.mjs";

/** Exactly what the bundled MCP SDK server negotiates. */
export const PROTOCOL_VERSIONS = [...SUPPORTED_PROTOCOL_VERSIONS];
export const DOCS_URL = "https://github.com/NavisWORLD/The-beast-box-/blob/main/docs/meta-muse-connector.md";

export const PAIRING_METHODS = [
  { id: "mcp-oauth", label: "MCP OAuth 2.1 (Muse app connectors, any MCP client)", available: true,
    how: "Add the connector URL; the client discovers OAuth metadata, registers itself (RFC 7591), and opens the Beast Box consent page where the owner types the pairing code." },
  { id: "muse-code-token", label: "Muse Code mcp_servers with a Bearer token", available: true,
    how: "Make a revocable token in Beast Box and paste the mcp_servers snippet into Muse Code." },
  { id: "meta-muse-device-pairing", label: "Meta Muse device pairing", available: false,
    how: "Not available: Meta has no public API for third-party device discovery in Muse. Only Meta hardware pairs that way." },
];

const mcpUrlOf = (origin) => origin + "/api/mcp";

/**
 * MCP Server Card v1. `device` (optional) adds the owner's chosen device name.
 * @param {string} origin
 * @param {{ deviceId: string, deviceName: string } | null} [device]
 */
export function serverCard(origin, device = null) {
  const card = {
    $schema: SERVER_CARD_SCHEMA,
    name: SERVER_NAME,
    version: SERVER_VERSION,
    title: device ? device.deviceName : "Beast Box",
    description: "Read and care for one paired Beast Box virtual pet: stats, care, moves, feeding, play and talk.",
    websiteUrl: DOCS_URL,
    repository: { url: "https://github.com/NavisWORLD/The-beast-box-", source: "github", subfolder: "apps/beastbox-cloud" },
    remotes: [{
      type: "streamable-http",
      url: mcpUrlOf(origin),
      headers: [{ name: "Authorization", description: "Bearer token from OAuth 2.1 (discovered via /.well-known/oauth-protected-resource) or a Beast Box Muse Code token.", isRequired: true, isSecret: true, placeholder: "Bearer bbm_..." }],
      supportedProtocolVersions: PROTOCOL_VERSIONS,
    }],
    _meta: {
      "io.github.navisworld/beastbox": {
        authorization: { protectedResourceMetadata: origin + "/.well-known/oauth-protected-resource/api/mcp", authorizationServer: origin, dynamicClientRegistration: origin + "/api/muse/oauth/register", scopes: ["beast.read", "beast.care"] },
        toolClasses: { read: ["get_beast", "get_care_status", "get_lost_cosmos_progress", "list_moves"], write: ["feed_beast", "play_with_beast", "rename_beast", "talk_to_beast"], sensitiveWrite: [] },
        device: device ? { id: device.deviceId, name: device.deviceName } : null,
        pairingMethods: PAIRING_METHODS.map(({ id, available }) => ({ id, available })),
        companionNote: "talk_to_beast replies come from a game companion model, not a conscious mind.",
      },
    },
  };
  return card;
}

export function serverCardUrl(origin, deviceId = "") {
  return origin + "/api/mcp/server-card" + (deviceId ? "?device=" + encodeURIComponent(deviceId) : "");
}

/** AI Catalog listing the one Beast Box server. */
export function aiCatalog(origin) {
  const host = new URL(origin).host;
  return { specVersion: "1.0", entries: [{ identifier: `urn:air:${host}:mcp:beastbox`, type: SERVER_CARD_TYPE, url: serverCardUrl(origin) }] };
}

export const DISCOVERY_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET",
  "Access-Control-Allow-Headers": "Content-Type, If-None-Match",
  "Access-Control-Expose-Headers": "ETag",
  "X-Content-Type-Options": "nosniff",
};
