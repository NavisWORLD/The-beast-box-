# One universe remeasure

Stage 6, part A. EMULATED Pixel 5. This agent's own measurement of `7c8b6f2511b5840de0908c442575593e316d2534` (merge of #922). These numbers are not a lab phone.

Both columns are that same head and the same production build. Flags off is the page with no `oneUniverse` query. Flags on is `?oneUniverse=state,light,population,tick,cameras` on that same build. The five flags are runtime on this head, so the first-load raw size, gzip size, and chunk count do not change between the columns.

## Method

Build: `apps/beastbox-cloud`, `npm run build`, exit 0. Gzip is Node `zlib.gzipSync` level 9, summed per `firstLoadChunkPaths` in `.next/diagnostics/route-bundle-stats.json`. `/spark/index.html` is a static page and has no Next first-load row.

Boot: `next start` on 127.0.0.1:3472. Playwright 1.55 Chromium headless, `--use-angle=swiftshader`, Pixel 5, CPU throttle 4×, Slow 4G (150 ms, 200000 B/s down, 93750 B/s up). Service workers blocked. One route at a time, fresh context. First frame is two animation frames after `getContext` on a connected canvas at least 2×2. `/sol-game` has no scene canvas and is the ready time (`domContentLoadedEventEnd`); it hits the 40 s frame deadline. Console errors are `pageerror` and console messages of type `error`, collected until the first frame or the ready time.

## First-load JS

Raw bytes, gzip bytes, and chunk count. Same for flags off and flags on.

| Route | Raw | Gzip | Chunks |
|---|---:|---:|---:|
| `/` | 1,850,860 | 607,844 | 21 |
| `/beast-cage` | 1,177,509 | 401,980 | 19 |
| `/beast-cage/look`, `/beast-cage/turntable` | 1,446,199 | 463,310 | 17 |
| `/beach-two`, `/sol-game` | 1,013,065 | 342,143 | 14 |
| `/beast-cage/field` | 1,037,882 | 351,593 | 15 |
| `/beast-cage/go` | 1,085,008 | 367,754 | 17 |
| `/beast-cage/world` | 1,018,207 | 344,165 | 15 |
| `/universe` | 1,867,104 | 567,864 | 19 |

## Boot

Time to first frame, script entries at that frame, and transferred script bytes. The script count at the first frame rises by 2 on every route when the five flags are on. The chunk count above does not. That rise is the flag readers loading after the first-load graph, on this measurement.

| Route | Off ms | On ms | Off scripts | On scripts | Off transfer | On transfer | Frame |
|---|---:|---:|---:|---:|---:|---:|---|
| `/` | 4572 | 4593 | 20 | 22 | 613257 | 616736 | 2d |
| `/beast-cage` | 3812 | 3884 | 19 | 20 | 407026 | 409747 | 2d |
| `/beast-cage/look` | 6232 | 6092 | 24 | 26 | 632973 | 636452 | webgl2 |
| `/beast-cage/turntable` | 6168 | 6032 | 24 | 26 | 632973 | 636452 | webgl2 |
| `/beach-two` | 5182 | 5138 | 13 | 15 | 344862 | 348341 | webgl2 `#c` |
| `/beast-cage/field` | 6279 | 6393 | 38 | 40 | 834359 | 837838 | webgl2 |
| `/beast-cage/go` | 6846 | 6879 | 26 | 28 | 594621 | 598100 | webgl2 |
| `/beast-cage/world` | 6772 | 6746 | 29 | 31 | 750928 | 754407 | webgl2 |
| `/universe` | 4028 | 4017 | 18 | 20 | 572814 | 576293 | 2d |
| `/spark/index.html` | 5426 | 5335 | 42 | 44 | 151007 | 156263 | 2d `#st1` |
| `/sol-game` | 1122 ready, wall 41147 | 1093 ready, wall 41145 | 22 | 24 | 442549 | 446028 | ready |

## Console errors

No `pageerror` and no console `error` on any of these routes, flags off or flags on, up to the first frame or the ready time.

| Route | Off | On |
|---|---|---|
| `/` | none | none |
| `/beast-cage` | none | none |
| `/beast-cage/look` | none | none |
| `/beast-cage/turntable` | none | none |
| `/beach-two` | none | none |
| `/beast-cage/field` | none | none |
| `/beast-cage/go` | none | none |
| `/beast-cage/world` | none | none |
| `/universe` | none | none |
| `/spark/index.html` | none | none |
| `/sol-game` | none | none |
