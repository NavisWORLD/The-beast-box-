# W8 P0 view counts — 2026-11-09

Report commit `4f13582a0fb956cefcda82bf35ac4b23ddbbc965` on `cursor/w7-w9-reports-44d7`, base `0995ff2fb32115fd6c97daf18caf3a9f8363c3cf`.

Measured live. PR #833 is merge `45e713b3c6a397fc6aa889f960dd4a8de9736c66`, merged 2026-11-06T16:12:24Z. 3D P1 was not started.

## How it was counted

Headless Chrome, `--use-angle=swiftshader`, started 2026-11-09T18:08:18Z, finished about 306s later, exit 0. A script installed before page scripts counted every `canvas.getContext` whose type contains `webgl`, and marked a context lost when `webglcontextlost` fired. The lost context on these pages is the software-GL probe in `apps/beastbox-cloud/lib/three/soft-gl.ts` (a throwaway context, then `loseContext`). Live counts below exclude it. `window.__glBudget.snapshot()` is the counter #833 added; it only records `living-world`, and only after that renderer is created (`components/living-world.tsx` lines 157–160).

The rasteriser string on every context was SwiftShader. On that rasteriser `isSoftwareGL()` is true, so home keeps the Cage pocket and does not mount the living world until "Enter the tiny world" (`components/home-pocket.tsx` lines 42–55). A real GPU would take the other branch. These numbers are the SwiftShader path, which is the same class of host the #833 note used, and they are not copied from that PR body.

Deployments, all production, team `team_j1cniaZln5NJAnnw4wyO4hQD`, project `prj_GI0JtKlE92yL9zDjAuxbOZhqL4qg`:

| Label | Deployment | Commit |
|---|---|---|
| Before | `dpl_ByrixeQk3AGbkAKfau23FHpvmhG7` | `51fd5cdfd9149fc5f45e8365ac665324ccfdbe85` (the production deploy immediately before #833) |
| After #833 | `dpl_EHaHnCCGxDny4FbEkJCtgzpvDuJ1` | `45e713b3c6a397fc6aa889f960dd4a8de9736c66` |
| Production now | `www.beastboxcosmos.xyz`, `dpl_3ZupxR5TaVwqgE7k4NtMNwb2EsWU` | `0995ff2fb32115fd6c97daf18caf3a9f8363c3cf` |

The two older deployment hosts answered 302 to Vercel SSO (checked 2026-11-09, `x-vercel-id` `iad1::mb5fw-1794247645883-ea5308481cad` and `iad1::tk46q-1794247646022-363a091009f1`). They were opened with a share link that is not recorded here. Production answered HTTP 200.

## Desktop 1366×860

Live WebGL contexts, then the living-world budget if the page created one.

| View | Before | After #833 | Production now |
|---|---|---|---|
| `/` on load | 2, both `powerPreference` `low-power`, antialias false. No budget. No living world. | 2, same options. No budget. | 1, `low-power`, antialias false. No budget. |
| `/` after Enter the tiny world | 3. The added context is `high-performance`, antialias true. No budget. `[data-living-world]=orbit`. | 4. Budget `{live:1, lost:0, view:"living-world", soft:true}`. The living-world context is `default`, antialias false. | 2. Budget 1 `living-world` `soft:true`. Contexts: one `low-power`, one `default` antialias false. |
| `/beast-cage/world` | 1, `high-performance`, antialias true. No budget. | 1, `default`, antialias false. Budget 1 `living-world` `soft:true`. | 1, `default`, antialias false. Budget 1 `living-world` `soft:true`. |
| `/beast-cage/world?glfail=living-world` | 1 `high-performance` antialias true still created. `seeded` false. No fail string. The query did nothing. | 0 live. `[data-seeded-land-2d]` present. `window.__lwGlFail` = `forced by ?glfail (receipt test)`. Budget null, because acquire runs only after a renderer exists. | Same as after: 0 live, seeded land present, same fail string. |

The view count did not go down. On this rasteriser #833 changed the living-world options from `high-performance` / antialias true to `default` / antialias false, because `lean` is true when `isSoftwareGL()` is true (`living-world.tsx` lines 154–157), and it added the budget plus the per-view fallback.

## Production phone size 390×844

Same SwiftShader host, mobile metrics, 2026-11-09 during the same run. Older deploys were not repeated at this size.

| View | Live WebGL | Budget | Fallback |
|---|---|---|---|
| `/` | 1 `low-power` | none | no |
| `/` plus tiny world | 2 (`low-power` and `default`) | 1 `living-world` `soft:true` | no |
| `/beast-cage/world` | 1 `default`, antialias false | 1 `living-world` `soft:true` | no |
| world `?glfail=living-world` | 0 | none | seeded land, fail string `forced by ?glfail (receipt test)` |

## Neighbor, production, 2026-11-09T18:13:50Z

`https://www.beastboxcosmos.xyz/?glfail=living-world`, then the tiny-world control. One live context remained: `low-power` (the pocket). Living-world did not create a context. `[data-seeded-land-2d]` was present. Fail string `forced by ?glfail (receipt test)`. Budget null. The pocket context was still live when the tiny-world view had already fallen back.
