# Beast Wings owner app — release scope and proof

This is a connection to the existing product, not a replacement model, open-ended autonomous agent or scientific advantage claim.

- Next.js COSMIC becomes an installable web app. On iPhone open Safari → Share → Add to Home Screen. This is **not** an App Store binary; native distribution requires a separate signed app.
- The owner bridge alone exposes authenticated, same-origin and shape-restricted `activation` and `master_stop`. The public landing and guest interfaces receive no task controls.
- The cloud cannot enqueue arbitrary sensor events, grant tools, or issue unbounded model requests. The queue begins stopped. Browser run budget is at most 3 tasks / 8 seconds. No owner private data or API credentials are cached offline by this patch.
- Interrupted queue work is **at-least-once**; an in-flight provider call is not preemptible, and owner reconciliation may be required after a restart.

**Release verification:** require exact PR-head automated checks, a verified persistent-volume recovery procedure, an installed-provider inference receipt (per model), a synthetic owner task + master stop check, an app/mobile check, and exact live Vercel/Railway revisions. Do not turn closed-loop/Unicode flags on over an existing production database until private authenticated backup and isolated restoration are validated. Preserve distinct stable 14K and experimental 18K identity and original PHOS/SAMGO weights. Five-model historical evidence: https://github.com/NavisWORLD/The-beast-box-/actions/runs/36770497000.
