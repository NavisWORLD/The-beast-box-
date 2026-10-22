# COSMOS CONNECT acceptance

Checked 2026-10-01 against public endpoints and `PYTHONPATH=connect/cosmos-connect python -m unittest tests.test_connector` (15 tests passed).

MODEL ≠ MEMORY. MODEL ≠ STATE. MODEL ≠ AUTHORITY.

| Tool | Source | Authorization | Tested result | Limit |
| --- | --- | --- | --- | --- |
| beastbox_get_status | `beastboxcosmos.xyz/api/release`, GitHub `commits/main`, public site, bridge `/healthz`, unauthenticated `/api/orbit` and `/api/models` | none | Release `beast-wings-merged-senses-5116e70b` VERIFIED LIVE. Frontend `https://www.beastboxcosmos.xyz/` VERIFIED LIVE. Bridge readiness VERIFIED LIVE for process only. Activation and live inference NOT YET VERIFIED. Orbit and models HTTP 401. Main SHA `333b01c97474d6fe40fcb05c656a48b43f860b84` does not match the release marker. | Readiness is not inference. |
| beastbox_get_architecture | `docs/ECOSYSTEM_MANIFEST.json` at the resolved main SHA | none | 20 components. `cosmos-runtime` and `dyn12` IMPLEMENTED. Repository `NOT IMPLEMENTED` stays UNAVAILABLE. | Source map, not a live process map. |
| beastbox_list_models | `beastbox/providers.py` plus optional swap report | none | `ReferenceTextProvider` fixture, `LocalOllamaProvider` and `CompatibleChatProvider` adapters, all live production NOT YET VERIFIED. | A class is not a running model. |
| beastbox_get_research | Published markdown at the resolved SHA | none | `self-correction-005` returned the original text, including `0/8`, with no connector conclusion. State VERIFIED HISTORICAL. | Excerpt is bounded. |
| beastbox_get_sensory_status | Public release receipt | none | Browser features IMPLEMENTED. `proof_scope` `code_deployed_not_physical_sensor_test`. Hardware NOT YET VERIFIED. Camera, microphone, and biometric capture not activated. | No physical sensor test. |
| beastbox_get_ci | GitHub Actions workflow runs | none | Runs keep `head_sha`. `proves_live_inference` false. A later read showed `ci` success at `45cf767f1fc06cb58b78d6a497634b383267b0e5` and at `333b01c97474d6fe40fcb05c656a48b43f860b84`, both VERIFIED HISTORICAL. | A green check is not live inference or sensor capture. |
| beastbox_search_mentions | Local evidence catalog | none | Returns `resource_link` items. Desktop composer mentions are the specified extension. | Web and mobile may not show the picker. |
| beastbox_open_dashboard | Same public reads as status, architecture, and sensory | none | Sidebar metadata is a global entrypoint. Text tools still return the payload. | Global entry is specified for web and desktop. |
| Owner tools | Existing bridge routes, not called | disabled | `OWNER_CONNECTION_DISABLED`. `bridge_called` false. No credential stored. | Needs a server-side scoped secret, not a browser cookie. State-changing tools also need backup, isolated restoration, deployment, and live acceptance. |

Also checked: invalid experiment ids return `INVALID_INPUT`; a request to claim live inference returns `FALSE_STATUS_CLAIM`; GitHub rate-limit and timeout maps return `UPSTREAM_RATE_LIMIT` and `UPSTREAM_TIMEOUT`; a missing file returns `NOT_FOUND`; an unexpected unauthenticated bridge 200 withholds the body; delayed and closed sockets map to timeout and unavailable.

The Site at `http://127.0.0.1:8787/` rendered these sections on a wide window and at 390px with no horizontal overflow. Research and CI buttons call `/api/call`, which uses the same functions as `/mcp`.

ChatGPT Sites did not return a production URL. This environment has no ChatGPT session, so the plugin was not installed inside a fresh ChatGPT conversation and web, mobile, and desktop ChatGPT clients were not opened.
