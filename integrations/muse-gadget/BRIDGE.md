# Beast Box bridge protocol

The bridge links one or more Beast Box browser tabs to the Muse gadget so Muse
commands reach the **live** beast. It is `beastbox_musegadget/bridge.py`, run by
the `beastbox-bridge` systemd service as the same account as Muse's commands,
on port 8787 by default. Standard library only; HTTP + Server-Sent Events.

```
Muse ──link.invoke beastbox.feed──▶ musegadget (SDK, root)
                                     └─ child process as run-as account: musegadget-beastbox muse-command
                                          └─ POST /v1/admin/command (loopback + admin token)
                                               └─ SSE "command" event ──▶ browser tab (BeastBoxBridge)
                                                     tab applies it to its beast, POST /v1/results {result, state}
Muse ◀──link.result {beast state}──────────────────────┘
```

## Linking (one-time code)

1. Browser `POST /v1/pair/start {label}` → `{pair_id, poll_secret, code, expires_in: 600}`.
   The tab shows `code` (8 characters, no look-alikes, shown as `XXXX-XXXX`).
2. The user approves on the gadget: `musegadget-beastbox link CODE`, or tells
   Muse the code (`beastbox.link`). That calls `POST /v1/admin/link {code}`.
3. Browser polls `POST /v1/pair/claim {pair_id, poll_secret}` → `{status: "pending"}`
   until approved, then **once** `{status: "linked", link_id, token}`.

Rules: codes are single use, expire after 10 minutes, at most 8 wait at once,
and 10 wrong codes in 10 minutes lock approval for 10 minutes. Approving a
code alone doesn't hand out the token: only the tab holding the matching
`poll_secret` can claim it, so someone who sees the code over your shoulder
can't take the link.

## Live session (revocable token)

All with `Authorization: Bearer <token>`:

| Call | Purpose |
|---|---|
| `GET /v1/events` | SSE stream. `event: hello`, then one `event: command` per Muse command: `{id, action, args, issued_at}`. Comment pings every 15 s. A newer stream for the same link replaces the older one. |
| `POST /v1/state {state}` | The tab's current beast summary (sent on connect and whenever it likes). |
| `POST /v1/results {id, ok, result, state, error}` | Answer a command. Only accepted for commands issued to this link. |
| `POST /v1/revoke` | The tab revokes its own link. |

Actions: `status`, `feed` `{food?}`, `play` `{game?: spark|pet|train, hits?}`,
`talk` `{message}`, `attack` `{move?}`, `moves`, `lost_cosmos`. The state is the
summary `{name, species, island, element, temperament, mood, stage, stats:{xp,
next_stage_xp, bond, energy, combat}}`, the same shape the gadget returns
everywhere else.

A Muse command waits up to `bridge_timeout_s` (12 s) for the tab. If no tab is
connected or it doesn't answer, the gadget falls back to the connector or its
saved copy and says so; `status` can also return the last state the tab sent,
labelled as stale.

## Gadget side (admin)

Accepted only from loopback **and** with the admin token in
`~/.local/state/beastbox-musegadget/admin_token` (0600, created on first run):
`POST /v1/admin/link`, `GET /v1/admin/links`, `POST /v1/admin/unlink {link_id}`,
`POST /v1/admin/command {action, args, link_id?, timeout_s?}`, `GET /v1/admin/state`.

## Isolation and storage

Each link has its own token, command queue and last state. A tab can only
read commands and post results for its own link. The gadget itself is paired
to one Muse account (yours); links are per browser profile under it. Tokens
are stored as SHA-256 hashes in `bridge.json` (0600); plaintext codes and
tokens are never written to disk or logged. Request logging records only the
method and path.

## Browser security notes

- **CORS:** only origins in `bridge_origins` get CORS headers (default
  `http://localhost:3000`, `http://127.0.0.1:3000`). Add yours with
  `install.sh --allow-origin`. Private Network Access preflights are answered.
- **Mixed content:** an HTTPS page can't call `http://` on your LAN. Serve
  Beast Box locally over http, give the bridge TLS (`bridge_tls_cert`,
  `bridge_tls_key`), or use a relay (below).
- The token is kept in the browser's `localStorage` under
  `beastbox-muse-bridge-v1`; revoking it from either side ends the link.

## Relay through the connector (later)

When the browser can't reach the gadget directly, the same protocol can be
relayed through the Beast Box connector backend in `apps/beastbox-cloud`
(`/api/mcp`'s server): mount the browser routes above under it, and have the
gadget hold an outbound stream to it instead of serving them. That is a
change to `apps/beastbox-cloud` and was intentionally not made here. The gadget
already uses that connector's MCP tools as its second source.
