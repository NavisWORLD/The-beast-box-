# Beast Box / Cosmos visual system

Swap the brain, keep the story. Beast Box is a persistent system with replaceable
inference. The visual design separates models, retained memory, system state,
receipts and explicit owner authority.

## Source and reconstruction

This pass is reconstructed from main at `8f90e440f0f4ceba502b1a3f8637507491fb23b0`
(v0.7.1). The prior scratch checkout could not be accessed from the active
session. Its 18 uncommitted files were not recovered, and its historical test
results do not validate this reconstruction. The prior branch and this document
were absent on GitHub when inspected.

The style reference is
[Cosmos](https://github.com/NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2/blob/main/cosmos/web/templates/cosmos.html):
midnight backgrounds, navy and indigo surfaces, cyan, violet and pink lighting.
Beast Box keeps local system font stacks, local assets and the existing CSP.
It does not adopt Cosmos's unrelated model, collective or consciousness claims.

## Frontend inspection

- `beastbox/cosmic_ui.py` renders the loopback console as HTML and vanilla
  JavaScript. `beastbox/cosmic_web.py` serves the existing runtime contracts.
- `html/index.html` and `html/app.js` form the standalone browser client.
  `html/build.mjs` produces the static directory and literal single-file client.
- Both clients previously maintained separate compressed styles, small labels,
  green-gray panels and inconsistent controls.
- This pass retains all 15 console views, eight standalone views, control IDs,
  input constraints, requests and authority decisions. It introduces no framework.

## Design plan and implementation

1. Share tokens, typography, cards, controls, navigation and status styles.
2. Make the orbital overview the visual identity anchor. Its values still come
   from the runtime; decorative orbits do not represent measured neural activity.
3. Give model, memory, system state, receipts, tools and authority distinct accents
   with readable text labels.
4. Unify provider cards, memory threads, provenance stages, diagnostics, empty
   states and settings controls.
5. Keep content in normal flow when text grows. The checkpoint caption occupies
   its own grid row; minimum node widths cannot exceed the available width.
6. Verify both clients, narrow layouts, enlarged text, connection loss, generated
   distributions and installed package resources.

## Semantic tokens

| Domain | Token | Color |
| --- | --- | --- |
| System / CNS | `--system` | Cyan `#65e2f5` |
| Replaceable model | `--model` | Blue `#86aeff` |
| Durable memory | `--memory` | Violet `#c1a1ff` |
| Receipts / continuity | `--receipts` | Magenta `#ef9cdb` |
| Explicit authority | `--authority` | Amber `#f3cc89` |
| Tools / workspace | `--tools` | Slate blue `#9dbacf` |
| Verified integrity | `--success` | Mint `#83e2bb` |
| Error / unavailable | `--red` | Rose `#ff9daa` |

A reachable standalone server receives a `ready` state, not a verified badge.
Only a valid integrity result produces `verified`. Live device capture and enabled
authority use amber. After a failed console poll, retained values are explicitly
marked **Last observed / not reverified**. A last-check timestamp is not repeatedly
announced to screen readers.

## Source of truth

| File | Responsibility |
| --- | --- |
| `beastbox/ui_theme.css` | Shared tokens, controls, cards, navigation, statuses and accessibility |
| `beastbox/cosmic_layout.css` | Console map, memory, trace, authority, workspace and storage layouts |
| `beastbox/cosmic_ui.py` | Existing console markup and interactions; cached inline package resources |
| `html/layout.css` | Standalone-specific layouts |
| `html/build.mjs` | Combines canonical theme and standalone layout; builds distributions |
| `html/styles.css`, `html/standalone.html` | Generated artifacts; regenerate rather than hand-edit |
| `pyproject.toml` | Packages console CSS in the wheel and source distribution |
| `scripts/smoke/cosmic_visual.py` | Real-browser responsive, caption, navigation and stale-state checks |
| `scripts/smoke/cosmic_package.py` | Resource-byte and isolated-wheel verification |

Apply semantic accents using `data-domain`. Use `.primary` for the principal action,
`.danger` for consequential actions, native `disabled` and `aria-busy` for work in
progress, and `.pill[data-state]` for status presentation.

Body text is 16px at the default browser setting. Controls use at least 44px
height and 14px type; secondary metadata uses 12–13px. Layouts wrap instead of
clipping long text. Narrow navigation scrolls horizontally and remains in normal
document flow so it cannot cover an error notice. Skip links, visible keyboard
focus, current-page markers, selected-provider states, reduced motion and forced
colors have explicit treatments.

## Build and verification

```bash
python -m pip install -e . pytest playwright==1.55.0 build ruff
python -m playwright install --with-deps chromium
node html/build.mjs
cp html/dist/standalone.html html/standalone.html
node --test html/tests/*.test.js
python -m pytest tests/test_cosmic_web.py tests/test_cosmic_completion.py \
  tests/test_cosmic_closure.py tests/test_cosmic_product_polish.py tests/test_html_server.py
python scripts/smoke/cosmic_browser.py
python scripts/smoke/html_browser.py
python scripts/smoke/html_short_desktop.py
python scripts/smoke/cosmic_visual.py
python -m build
python scripts/smoke/cosmic_package.py
```

Commit generated assets with their sources and bump the service-worker cache
when changing cached distribution assets. Restart the console after editing CSS;
resources are cached once per process.

The Cosmic UI polish workflow runs the focused Python contracts, JavaScript
tests, deterministic artifact checks, 161 layout checks over both clients,
status-loss/recovery checks and clean installed-wheel verification. Existing
Product CI and Web Runtime workflows retain their full owner-flow checks.
Workflow output is the authority for pass/fail; these instructions are not a
claim that a run passed.

Screenshots in `build/cosmic-visual/` come from real Chromium and a temporary
deterministic reference runtime. The result records source and image hashes.
These UI artifacts are separate from sealed scientific evidence and do not
validate physical devices, native platform appearance, model quality or new
model-swap claims. No runtime, memory, policy, API or evidence implementation is
changed by this visual pass.
