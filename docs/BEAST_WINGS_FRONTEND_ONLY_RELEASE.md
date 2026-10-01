# Beast Wings — live-safe frontend-only release

This release is an additive installable COSMIC web app and existing measured-signal display, **not** a product backend or model promotion.

- The iPhone app is installed using Safari → Share → Add to Home Screen, without local persistent caching of owner data.
- SYNAPSE TRACE renders actual checkpoint-backed `substrate-signal-v1` values; a missing receipt remains explicitly unavailable.
- The **bounded owner activation controls, master stop cloud bridge and the rest of PR #165 remain staged**. No UI control is shown for an unprovisioned backend route.
- No `beastbox/**`, `apps/beastbox-cloud/bridge/**`, `README.md`, `LICENSE` or `pyproject.toml` change is made, matching the existing Railway production watch set.
- Before a backend rollout, require a separately durable owner-volume backup and isolated restore proof. Do not enable closed-loop or Unicode reader flags until the existing persistent volume has been validated.

Live release requires exact-head GitHub CI and one-time Vercel deployment. Vercel's connected API scope may need user reconnection for independent post-deploy inspection. A public homepage response alone does not prove authenticated owner-model inference.
