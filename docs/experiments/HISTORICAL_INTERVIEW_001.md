# Historical interview prototype (archived)

The early `i dare you/` JEV/PHOS interview prototype from merged [PR #82](https://github.com/NavisWORLD/The-beast-box-/pull/82) was an **incomplete offline substrate experiment**. It did not execute the external JEV decision model or an authentic PHOS model-swap conversation. The original source and evidence descriptions remain permanently available in Git history at merge commit `21ecef58011409a257394e5f7e2fb1bdf8a681a6`.

Its obsolete active code and tests were removed from `main` during app preparation, not rewritten to imply a successful provider result. This historical archive page intentionally has **no provider credential requirements**.

The later SmolLM2/PHOS work stays on independent experimental branch `experiment/i-dare-you-smollm-phos-001` and is **not merged or advertised as production-ready**. Its 10-minute native-server run `35484660249` failed the test-import gate before inference; retain that failure. An earlier 10-turn run `35483820438` used a separate 64-character custom greedy adapter; do not conflate it with the native-server experiment.

## Vercel deployment boundary

The Beast Box repository root is a **Python research/runtime monorepo**, not a deployable Vercel web application. Do not set `[tool.vercel] entrypoint` to `Endsupdate.beastbox.web:Handler` or any other arbitrary `Handler` merely to clear Vercel's auto-detection. That would target the wrong runtime and would not provide durable storage, user authentication, or model compute.

First build and test a dedicated Vercel frontend under an isolated app folder (for example `apps/beastbox-cloud/`), then configure **Root Directory** in Vercel to that exact existing folder. Deploy a private Preview until the separately hosted durable Python runtime, authentication, storage, provider health, and attachment flows have passed. Preserve default-deny model/tool authority and label unavailable features rather than faking them.

The existing owner-controlled local COSMIC workstation remains available from the published Beast Box release and source. No cloud-app release is claimed by this archive operation.
