# BEAST BOX // COSMOS CONNECT

Read-only Site and remote MCP server for Cory Davis’s existing COSMOS. Apache-2.0, same as the repository. This directory does not replace the runtime, copy a Railway token, or deploy the owner bridge.

MODEL ≠ MEMORY. MODEL ≠ STATE. MODEL ≠ AUTHORITY.

## Run

From `connect/cosmos-connect`:

```bash
PYTHONPATH=. python -m cosmos_connect
```

The site listens on `127.0.0.1:8787` unless `PORT` is set. `PORT` binds `0.0.0.0` for a host that assigns the port. MCP is `POST /mcp`. The install card is `/install`.

```bash
PYTHONPATH=. python -m unittest tests.test_connector
```

## Evidence labels

`VERIFIED LIVE`, `VERIFIED HISTORICAL`, `IMPLEMENTED`, `UNAVAILABLE`, and `NOT YET VERIFIED` stay separate. A GitHub success is a historical source check at `head_sha`. Bridge `/healthz` is process readiness. Neither one is live inference or physical sensor capture.

Public tools call only:

- `https://beastboxcosmos.xyz/api/release`
- `https://beastboxcosmos.xyz/`
- `https://cosmos-owner-bridge-production.up.railway.app/healthz`
- unauthenticated `GET /api/orbit` and `GET /api/models` on that bridge
- the GitHub API and raw files for `NavisWORLD/The-beast-box-`

## Owner connection

Owner tools are listed and fail closed with `OWNER_CONNECTION_DISABLED`. No credential is read from the environment. A browser cookie is not bridge authorization. State-changing tools stay disabled until backup, isolated restoration, deployment, and live acceptance are recorded outside this connector. The plugin does not start a camera, microphone, or biometric capture.

## ChatGPT

`.openai/hosting.json` has no `project_id`. Sites adds one after the project is provisioned. Publish from ChatGPT Sites as a private Site, then point the personal plugin at `https://<site>/mcp`. `plugin/.mcp.json` uses `https://cosmos-connect.invalid/mcp` until that host exists.

Composer at-mentions are specified for desktop. The global sidebar entry is specified for web and desktop. Text tools remain the path when a client has no interactive extension. This repository cannot open the ChatGPT installation dialog without the account session.
