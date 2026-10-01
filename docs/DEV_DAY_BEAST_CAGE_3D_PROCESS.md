# DevDay Side Quest: 3D Models — Beast Box's original cosmic companion

**Owner and art direction:** Cory Davis / NavisWORLD
**Project:** [Beast Box](https://github.com/NavisWORLD/The-beast-box-)
**Reproducible model source:** [cosmic-companion-3d.tsx](https://github.com/NavisWORLD/The-beast-box-/blob/feature/beast-cage-live-sidequest-20261001/apps/beastbox-cloud/components/cosmic-companion-3d.tsx)
**Interactive 360° page:** `/beast-cage/turntable` on the current UI preview
**Actual record:** DevDay genuine 3D turntable video GitHub Actions artifact (generated after workflow runs).

## Original creation prompt / brief
“Transform my original custom galaxy-creature design into a recognizably similar, rotatable 3D companion for the EXISTING Beast Box web interface. Preserve the plump, translucent violet/blue galaxy body, iridescent radial fins, giant starry eyes, expressive mouth and small floating golden star. Use actual geometry, physically based translucent-looking materials, deterministic stellar texture and browser-safe WebGL performance. Integrate, don't replace, existing backend or security boundaries. Give users reduced-motion and static fallbacks. Render truthful operational states only; the sprite is a visual metaphor, not proof of life or emotion.”

## What was actually built
- Original, source-editable SVG character artwork and scene.
- Three.js geometry: body and lobes as 3D spheres; eleven extruded fin shapes; curved 3D smile; separate glossy eyes and 3D golden eye stars; orbit and top star geometry.
- Seeded canvas galaxy texture, physically based materials, ambient/warm/rim lighting.
- A true geometry turntable rotating the actual model through 360°, plus exact 0°, 90°, 180° and 270° viewpoints and a 390px mobile acceptance view.
- The exact same mesh is reused in the Beast Cage interface and visual companion. This video does not show successful conversation or claim that 3D animation is neural activity.

## How to reproduce
Check out the exact PR branch; in `apps/beastbox-cloud`, run:
```
npm install --no-audit --no-fund
npm test && npm run typecheck && npm run build
npm run start -- --port 3100
```
Open `http://localhost:3100/beast-cage/turntable`. Click "Rotate 360°" or a fixed-angle button. This page is publicly viewable only where the chosen deployment exposes it. The GitHub Actions workflow `DevDay genuine 3D turntable video` runs headless Chromium and captures genuine MP4 and four screenshots, fails when the WebGL mesh does not render, and captures a mobile screenshot.

**Submission:** Attach the actual resulting video and source-process text via the *authenticated* [DevDay Side Quests](https://side-quests.openai.chatgpt.site/) registration and 3D Models quest. An X post alone does not submit it. Do not claim a completed entry until the site confirms it.
