# Owner model selection and slow-chat failure behavior

## Why this change exists

A Vercel Preview displayed a selected \`gpt-oss:120b\` provider label but returned
"COSMOS did not confirm a completed answer." The label is a **saved profile**,
not evidence of completed paid cloud inference or of a working provider key.
The existing Railway service continued to report SUCCESS and its pinned local
SmolLM2 loopback was loaded; a separate chat job could return a failure while
Railway health continued passing. Do not infer that a provider was billed from a
profile name. No external inference is run by the checks in this update.

## Scope and authority

- **Brain Bay → Choose your brain** fetches a small bearer-protected catalog
  through the existing owner-cookie Vercel BFF. Only locally verified
  SmolLM2-135M-Instruct-Q4_K_M and *actually saved encrypted* Hugging Face /
  Ollama Cloud connections are shown. An IBM watsonx key alone does not create
  an inference adapter or an available model option. No arbitrary model URL,
  provider identifier, credential or runtime resource configuration is
  accepted from the browser.
- The local model selection rechecks the private loopback \`/v1/models\` and
  returns a truthful selection receipt. It does **not** invoke billable
  inference and revokes old cloud/tool grants via the existing handoff. The
  same durable memory/checkpoint/system identity stays in place.
- Remote selection uses the existing vault activation path and requires a new,
  explicit owner checkbox acknowledging **the provider's possible charges**.
  Railway's one-time Trial credit is unrelated to provider billing. Saved
  credentials do not prove remote model availability or payment headroom, so
  the UI says inference remains unverified until an actual completed turn.
  No automatic fallback or remote model testing is performed by this control.
- The model switch and save/remove credential action are admitted only when
  the owner's CPU/chat job coordinator has no active job. If a turn is running,
  the request returns 409 and does not move the profile or wipe context.
- A cloud-selected profile may survive a host restart, but cloud authority
  does not. When the tiny-model host flag is set, the pinned local weights
  and health still verify, while the remote choice remains unapproved until
  the owner explicitly reselects it or switches back to local. The startup
  guard must not prevent the whole app from booting just because a remote
  profile had previously been selected.

## Long-running chat

The browser now waits up to 11 minutes through individual short authenticated
polls. Each request still honors Vercel's timeout. A failed job only exposes
a sanitized category, never a provider's raw response, private prompt, token,
secret, stack trace, or account balance. It retains the original text in the
composer on failure and **never retries an ambiguous turn automatically**.
An interrupted page/session can lose the RAM job ID; refresh Conversation
before consciously starting another request. The host's underlying provider
timeout may still fail earlier than the browser deadline, which is reported
as an unconfirmed turn. This change does not promise a successful response
from every configured third-party model.

## Gates

Run Python unit tests including fixture-only in-flight switching, restart
without remote authority, malformed model requests, and unchanged exact
system ID/checkpoint after a local handoff. Run JS BFF contract tests,
Playwright mobile no-overlay tests, real local GGUF CPU + same-volume restart,
security, and normal CI before merge. Observe the live authenticated
\`gpt-oss:120b\` failure mode only with the owner's explicit provider
spending approval; no billable inference is authorized by a test suite.

No DNS, user files, secrets, host quota, Railway service, cloud account,
camera/microphone policy or storage volume is changed by this patch.
