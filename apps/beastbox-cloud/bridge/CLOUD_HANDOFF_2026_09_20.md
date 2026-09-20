# Cloud engine handoff — 2026-09-20

**Disposition: BLOCKED_HOSTING_BUDGET_AND_LIVE_VERIFICATION. No live backend launched.**

Owner: Cory Davis / NavisWORLD. Repository: `NavisWORLD/The-beast-box-`.
Continue only `feature/cosmic-chaos-vercel-app-001` and
[draft PR #84](https://github.com/NavisWORLD/The-beast-box-/pull/84).
Recovered source HEAD: `5e22973cba25cdf37f4a2fc6fbc638bf16e09106`.
The Dockerfile, Caddy configuration, Railway configuration, existing runtime,
and historical scientific evidence have been preserved. No main-branch change,
DNS change, production promotion, paid inference, IBM job or Azure resource
was made in this continuation.

## Verified account and deployment state

| Item | Observed result |
| --- | --- |
| Railway project | Existing `Beast Box COSMOS Engine`, `0f127a08-6074-4612-87bb-da8837f28fa1`; no duplicate created |
| Railway workspace | `49b6522b-fd2b-456e-bbf0-9db05b581418` |
| Railway environment | Existing `production`, `44d28bc1-5b3d-4a3a-8bf7-2c2851b3a867` |
| Railway services | Live connector returned an empty list; zero services/running replicas |
| Mounted backend volume / backend URL | None: no service to attach or expose; no volume created by this continuation |
| Workspace plan, invoice, remaining credit, actual limits | **NOT VERIFIED**: connector has no direct billing tool; billing browser shows Login; no local Railway credential available |
| Railway deployment logs | No deployed service to produce logs |
| Vercel metadata access | Retry succeeded for project/deployment reads in the connection's default scope (`teamId: ""`); explicit `zerefs-end` / `team_j1cniaZln5NJAnnw4wyO4hQD` still returns 403; team list empty |
| Vercel project | Verified existing `the-beast-box`, `prj_GI0JtKlE92yL9zDjAuxbOZhqL4qg`, account `team_j1cniaZln5NJAnnw4wyO4hQD`, Next.js; keep app root `apps/beastbox-cloud` |
| Vercel build log access | Advertised connector operation returned `Tool get_deployment_build_logs not found`; no live log claim |
| Vercel runtime logs | Default scope requires a team ID; supplying the verified account ID returns 403. No runtime-log inspection claimed |
| Existing frontend | `https://beastboxcosmos.xyz` appears in the READY feature Preview's alias list; protected `/api/session` fetch still returns a connector 403; no fresh owner-authenticated application test |
| Latest verified Preview | `dpl_DJGw1p3Cxo35fJZd4JwQX1noCVSm`, READY, target `null`, correct feature branch at `5e22973cba25cdf37f4a2fc6fbc638bf16e09106`; URL `https://the-beast-342pctfow-zerefs-end.vercel.app` |
| Screenshot's failed deployment | `dpl_APRCFhoV4a5QzPJXhRWacJqkhm95`, ERROR; redeploy of `main` at `fd785d34d06fa31f4ffb0e637ce24e130e3ed54e`, which lacks the configured app directory |
| Secrets | No live secrets generated, read, changed, exported or committed; installation deferred until both destinations are authorized |

The initial Vercel project call exposed a connector schema mismatch: it
advertised `projectId` but the upstream expected `idOrName`. Providing both
names and using the existing connection's default scope allowed project and
deployment metadata reads on retry. The previous blanket access-blocked
conclusion is superseded by these successful reads. Protected deployment
fetches and team-scoped runtime logs remain unavailable. Public GET probes
followed Vercel authentication redirects and returned HTML, not application
JSON. An anonymous POST received Vercel's 401 protected-deployment response.
None of these probes proves the app's owner session or bridge works.

The screenshot failure is now identified from Vercel deployment metadata:
`NOW_SANDBOX_WORKER_ROOTDIR_NOT_EXIST`, at `build-container-init`, with
`The specified Root Directory "apps/beastbox-cloud" does not exist. Please update your Project Settings.`
It belongs to the old `main` snapshot, not the READY feature Preview. Keep the
correct cloud app root and feature branch; do not redeploy that old commit or
merge/promote merely to clear the Production Deployment panel. The project
reports `live: false`; the existing custom-domain alias does not establish a
production release or backend connectivity. No aliases or DNS were changed.

## Budget decision

Approval is **$5 total Railway hosting per month**, not $5 plus overages.
Current official published pricing, independently of the unverified account:

| Component | Published amount / behavior |
| --- | --- |
| Hobby subscription | $5/month, including $5 usage credit; usage above the credit is charged |
| Container RAM | $10/GB-month |
| Container CPU | $20/vCPU-month |
| Network egress | $0.05/GB |
| Persistent volume storage | $0.15/GB-month |
| Compute hard limit | Minimum configurable amount $10; covers CPU, memory, storage and egress |
| Agent usage | Independently metered and limited; consumes the same included credit; not covered by the compute shutdown |
| Prepayment | Current plans documentation says new prepaid payment is no longer offered; purchased credits do not establish a $5 total cap |

Example: $7 usage on Hobby means $7 total before any applicable tax, not $12.
An estimate under $5 is still not an enforceable maximum. No $10 hard limit
was substituted, no plan upgrade was performed, and no paid Railway Agent
request was made to inspect billing because that request itself consumes
billable model tokens.

Sources checked on 2026-09-20:

- [Railway cost controls](https://docs.railway.com/pricing/cost-control)
- [Railway plans, resource rates, included credit and prepayment](https://docs.railway.com/pricing/plans)
- [Railway agent billing](https://docs.railway.com/pricing#railway-agent)

To use Railway Hobby, the owner would have to authorize a different ceiling:
at least the $10 compute threshold, with agent spend separately disabled or
budgeted and any tax/other charges included in the approved total. **This is
not a claim that $10 is a verified total invoice cap.** Confirm those details
on the real billing account before presenting an exact revised total for
approval. The present $5 approval remains binding; no increase is assumed.

## Alternatives investigated without provisioning

| Option | Suitability and next gate |
| --- | --- |
| Oracle Always Free, account kept unupgraded | A real Linux VM and persistent block volume can run the existing engine via the Linux service instructions in HOSTING.md. Candidate: one Always Free-eligible Ubuntu VM plus a separate block volume in the home region, within free allocations. Requires an owner account, verified free-only tenancy, available capacity, authorized host access and HTTPS configuration before any execution. No relevant OCI connector was found in the plugin directory search. |
| Railway Trial / Free | Documentation offers trial credit then $1/month Free credit, a 0.5 GB RAM/volume limit on Free and possible outbound restrictions on Limited Trial. It may support a bounded demonstration, but account eligibility, credit exhaustion, retention, runtime fit and continued access are unverified. Do not label it an always-running durable release. |
| Render Free | Rejected for the current engine: no persistent disks; its local SQLite/files are lost on restart/redeploy. Moving the database would change the runtime design. |

Oracle documents no actual charges unless the account is upgraded, but card
verification may cause temporary authorization holds. Capacity can be
unavailable and idle free instances can be reclaimed; independent backups
remain necessary. This is a researched hosting candidate, not a deployed,
benchmark-tested or guaranteed-uptime alternative. Do not sign up for duplicate
free accounts, upgrade to Pay As You Go, or change apex DNS to make it work.

- [Oracle Free Tier FAQ](https://www.oracle.com/cloud/free/faq/)
- [Oracle Free Tier account charging](https://docs.oracle.com/en/learn/cloud_free_tier/)
- [Oracle Always Free compute and block-volume limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Railway Trial / Free](https://docs.railway.com/pricing/free-trial)
- [Render Free limitations](https://render.com/docs/free)

## Verification completed here

Local commands on the recovered source plus the two additional BYOK tests:

```text
python -m unittest discover -s apps/beastbox-cloud/bridge/tests -p 'test_*.py' -v
  14 tests passed; no external inference/storage/quantum requests
node --test apps/beastbox-cloud/tests/*.test.mjs
  7 tests passed
cd apps/beastbox-cloud
npm run typecheck
  passed
npm run build
  passed (Next.js 16.3.5 resolved by existing package range)
```

New cases exercise both HF and Ollama Cloud through the real compatible
provider error path with an intentionally unavailable transport. They verify
fixed endpoints, bearer injection, sanitized errors, no reference generation,
unchanged identity, and no fabricated successful conversation. Another test
opens the same real SQLite/vault state in a new bridge instance, preserves its
profile/history/checkpoint, refuses chat without renewed owner cloud authority,
and keeps filesystem/quantum/export/authority routes unavailable. Its seeded
conversation uses the explicitly labeled reference fixture, not a hosted model.

The repository security audit initially flagged a placeholder private-key
example in untracked installed Next.js documentation under `node_modules`.
The example contains an ellipsis, not a live credential. After moving only
the locally generated dependency/build directories outside the checkout,
the unchanged `python scripts/security_audit.py` passed. No detection rule
was weakened and no tracked project file was removed to obtain that result.

Historical receipts were rechecked through GitHub, not rewritten:

- [Run 35495877810](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35495877810): `web` and `durable-image` jobs and all listed steps succeeded on the recovered HEAD. This includes desktop/iPhone-size checks and Docker/Caddy restart persistence with a disposable Docker volume.
- The recovered HEAD's repository CI, Product CI, security audit, configuration contract and macOS workflow also report success.
- Local Docker and a local browser runner were not installed in this environment; container/mobile verification ran in GitHub Actions, not locally.

Fresh checks on `a438ca622dba1981b42cb47624760fe4410d97d3` also succeeded:
[Cosmic Chaos Preview Checks 35503603130](https://github.com/NavisWORLD/The-beast-box-/actions/runs/35503603130)
passed 14 Python tests, 7 frontend checks, typecheck/build, the actual
Docker/Caddy mounted-volume/authentication/restart smoke, and desktop plus
390x844 iPhone-size browser acceptance with zero page errors or measured
horizontal overflow. Repository CI, Product CI, security audit and the
configuration contract also passed on that SHA. Evidence artifact
`cosmic-chaos-browser-evidence-35503603130`, ID `10603166672`, contains
2,602,699 bytes, SHA-256
`6ef97d5c607444ab3ae290689798109ebbd5e18e6d589bfd0b9f4fc842276a35`,
and expires 2026-10-20. These are isolated reference/offline checks; no hosted
model inference or actual Railway restart was performed. This later access
retry changes only this handoff document, so these receipts remain attributed
to their tested SHA.

## Live acceptance remains blocked

| Requested gate | Live status |
| --- | --- |
| Railway health, bearer rejection and authenticated runtime/provider endpoints | NOT EXECUTED — no backend deployed |
| Owner Vercel status with backendReachable=true; BRAIN recognition | NOT VERIFIED — backend missing and protected deployment fetch still denied; metadata reads now work |
| SETTINGS redacted encrypted vault listing | Implemented and tested offline; NOT VERIFIED on cloud |
| Genuine authorized multi-turn HF/Ollama conversation | NOT EXECUTED — no inference authorization/key or hosted engine |
| History, system identity and checkpoints after actual cloud restart | NOT EXECUTED — only local/container fixture persistence verified |
| Unavailable model fails without reference fallback | PASS offline transport-failure tests; live gate open |
| Model cannot obtain unrelated host/cloud/deployment authority | PASS scoped local boundary tests; deployed acceptance still open |

Azure Blob's offline adapter and optional read-only credential check do not
establish an upload lifecycle or persistent compute. IBM watsonx authentication
does not establish inference; IBM Quantum configuration does not establish a
job. These labels and the existing single-owner SETTINGS interface are retained.

## Exact continuation actions

1. **Account billing:** sign in to [Railway Workspace Usage](https://railway.com/workspace/usage), select the workspace above, inspect plan/credit/current usage and **Set Usage Limits**. Also inspect subscription/invoice tax and any agent charges. Do not save a limit above the approved ceiling. Either establish an enforceable $5 total or obtain a separately approved, fully quantified replacement budget. An alternative is authorizing access to a verified, unupgraded Oracle Free Tier account; any account signup/card/terms step belongs to the owner.
2. **Vercel access:** continue project/deployment metadata reads in the working default connection scope; no further reconnect is needed for those reads. For protected page/runtime-log access, verify the connected Vercel account's **zerefs-end** authorization. If that access must be renewed, use ChatGPT **Settings → Apps → Vercel → Disconnect**, then **Connect**, and complete Vercel authorization with the account/team that owns this project. Do not infer secret-write capability from successful metadata reads: the connected tools expose no environment-variable writer. [ChatGPT app connection instructions](https://help.openai.com/en/articles/11487775-connectors-in-chatgpt).
3. **When the hosting gate passes:** use the existing Railway project/environment and checked-in Docker/Caddy configuration. Attach the real volume at `/srv/beastbox/data`; confirm mounted/writable storage, one replica, loopback Python and non-root application/proxy processes. Do not set a billable model profile yet.
4. **Secret installation:** generate a new random bearer token and a separate 32-byte standard-base64 AES-GCM vault key inside an authorized secret-configuration session. Install the bearer only in Railway service variables and the matching Vercel Preview; install the vault key only on the durable host. No secret output in shell history, logs, files, chat or PR. Do not rotate the existing owner password or Vercel session secret.
5. **Secure UI if Vercel environment writes remain unavailable:** open project **zerefs-end / the-beast-box → Settings → Environment Variables**. Add `BEASTBOX_CLOUD_BRIDGE_URL` with the verified backend HTTPS origin and `BEASTBOX_CLOUD_BRIDGE_TOKEN` with the matching bearer. Select **Preview**, restrict to **feature/cosmic-chaos-vercel-app-001**, and mark the token sensitive. Save both before deployment; the host vault key never belongs in Vercel. Preserve existing owner/session variables. [Vercel environment-variable instructions](https://vercel.com/docs/environment-variables).
6. **Release the branch hold only after steps 1–5:** remove this branch's `false` entry in `apps/beastbox-cloud/vercel.json`; verify the deployment target is Preview even if an alias exists. Then deploy that feature branch only. The documented [git.deploymentEnabled control](https://vercel.com/docs/project-configuration/git-configuration) prevents automatic pushes from deploying while the hold remains. No main merge, promotion or DNS edit is authorized by these steps.
7. **Run live acceptance and separately authorize inference:** test every gate above, then use owner SETTINGS to save/test a real credential and explicitly activate a model under a separate inference budget. After a backend restart, reactivation is required because authority is deliberately not persisted. Record the real provider responses and restored state hashes without exporting secrets. Keep PR #84 Draft until required gates pass.

MODEL ≠ MEMORY. MODEL ≠ STATE. MODEL ≠ PROVENANCE. MODEL ≠ AUTHORITY.
