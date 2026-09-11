# BEAST BOX // Standalone Web Runtime

`html/` is a first-class browser client for the canonical Beast Box runtime. It does not replace or reimplement the Python durable substrate. The standalone server is a transport adapter around `beastbox.cosmic_web.CosmicApp`.

## Run

From the repository root:

```bash
python -m html.serve --data-dir ./my-beast --host 127.0.0.1 --port 8081
```

Open `http://127.0.0.1:8081/html/`.

The server is loopback-bound by default and issues an HttpOnly, SameSite session cookie for state-changing API calls. Existing Beast Box authority controls remain in the canonical runtime.

## Architecture

```text
canonical Beast Box runtime
        |
        +-- CosmicApp / versioned API boundary
        |
        +-- html/serve.py (transport + static assets)
        |
        +-- html/app.js (browser workstation)
        |
        +-- html/src/{api,capabilities,providers,runtime,storage}
```

The browser client consumes existing `/healthz`, `/api/orbit`, `/api/memory`, `/api/trace`, `/api/provider`, `/api/conversation`, `/api/storage`, `/api/context`, `/api/chat`, and authority/workspace routes. It does not create a second canonical memory database.

## Browser capabilities

At startup the client feature-detects WebAssembly, WebGPU, IndexedDB, OPFS, file selection, workers, service workers, and network availability. Execution planning is capability-driven; no claim of unrestricted native hardware access is made.

The browser UI can use the canonical deterministic reference runtime without a language-model download. WebGPU/WASM capability detection and the local-model adapter are present, but a GGUF file is **not** executed merely because WebGPU exists. A compatible browser inference engine must be supplied before local inference can be enabled. This is deliberate rather than a fake local-model claim.

## GGUF / local models

Brain Bay provides a real file-selection workflow. GGUF headers are validated and safe metadata is retained in IndexedDB. The selected model is not uploaded by the client. Oversized or malformed files are rejected. Current browser distribution is capability-limited for inference until an actual compatible WASM/WebGPU engine is bundled or supplied as an approved adapter.

The provider architecture supports:

- `ReferenceProvider`
- `LocalModelProvider`
- `OllamaProvider`
- remote/custom endpoint providers

## Ollama / Azure / remote endpoints

Ollama may be configured with a user-owned endpoint such as `http://127.0.0.1:11434`. The browser cannot assume that localhost is reachable; CORS, mixed-content rules, firewall policy, and device topology can prevent access. The Test Connection action reports failure instead of fabricating success.

Remote-compatible endpoints must use HTTPS except loopback development endpoints. API keys are represented as environment-variable names for the host runtime. Private keys, master credentials, and privileged authority tokens are never bundled in static assets.

Azure-specific authentication should remain server-side. The browser is a client, not a secret vault.

## Offline mode

The service worker caches the application shell when served over HTTP(S). If the network disappears, the shell remains available and the UI explicitly reports the canonical runtime as unavailable. Browser-local UI/model metadata remains available. The deterministic Beast Box reference provider is still a host-runtime feature and is not falsely simulated by the browser.

## Storage

- IndexedDB: browser-local model metadata and browser preferences.
- OPFS: detected and available for future approved large local artifacts.
- localStorage: only small settings such as the API base URL.
- Cache Storage/service worker: application shell.
- Canonical memory/state: remains in Beast Box's durable runtime when connected.

Uninstalling the web app, clearing site data, storage exhaustion, or device failure can destroy browser-local state. Export important state when the canonical runtime's portable-state contract is required.

## Import / export

Browser-state export/import is explicit and only covers browser-local client configuration. It never silently overwrites canonical Beast Box state. Canonical portable snapshots continue to use the existing runtime's verified import/export APIs.

## Security

The web server applies a restrictive Content Security Policy, `nosniff`, `no-referrer`, Permissions Policy, and a SameSite/HttpOnly session cookie. Imported files are treated as untrusted. User-rendered conversation and trace text is HTML-escaped. Arbitrary browser filesystem access is not requested.

The existing runtime's invariant remains:

```text
STATE MAY TRAVEL.
INFORMATION MAY TRAVEL.
AUTHORITY DOES NOT TRAVEL AUTOMATICALLY.
```

## Mobile / installability

The UI is responsive down to approximately 320px, uses safe-area-aware browser behavior through viewport configuration, avoids hover-dependent interaction, and exposes touch-sized controls. `manifest.webmanifest` supports browser installation/Home Screen behavior. The service worker requires a secure context (or localhost).

For iPhone Safari, use **Share → Add to Home Screen**. For Android Chrome, use **Add to Home screen / Install app** when offered.

A true literal one-file distribution is intentionally not the default because external JS, worker, service-worker, manifest, and CSP boundaries are useful security and maintainability properties. The `html/` directory is the portable static web bundle; it can be copied and served as static assets, while API POST operations require a Beast Box runtime endpoint/session.

## Tests

```bash
cd html
node --test tests/*.test.js
```

These tests cover capability selection, GGUF validation, provider registry behavior, local-provider honesty, runtime selection, secret exclusion, XSS-safe rendering, and filesystem restrictions.

The repository's normal Python regression suite remains the source of truth for the canonical runtime:

```bash
python -m pytest -q
```

## Known limitations

1. A browser cannot receive unrestricted filesystem, process, GPU, or device authority.
2. WebGPU availability does not imply that an arbitrary GGUF architecture/quantization can execute.
3. The current web distribution validates GGUF metadata but does not ship a full GGUF inference engine; local inference is therefore capability-limited rather than simulated.
4. Ollama access may be blocked by CORS or network policy even on a reachable device.
5. Cross-origin static hosting needs appropriate server CORS configuration; the client never bypasses browser policy.
6. Canonical durable memory, provenance, authority, and workspace controls remain host-runtime responsibilities.
7. iPhone/Android acceptance depends on the actual device/browser version and was not claimed here without a device run.
