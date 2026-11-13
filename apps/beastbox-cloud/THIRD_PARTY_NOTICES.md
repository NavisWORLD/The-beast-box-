# Third-party notices (apps/beastbox-cloud)

Code and techniques below are THIRD-PARTY, labelled as such in their file headers. No characters, creature
models, names or creature skins from these projects are used; Cory's creatures and Zeref's art are untouched.

## pallet-town-3d (MIT)

Used in: `lib/look/third-party/texture-lab.ts` (seeded simplex, torus-tiled fbm, wrap-around Sobel normal bake).
Also: the day hemisphere ground colour (green-meadow bounce) in `components/living-world.tsx`, taken from its Atmosphere rig idea; applied to our existing one-sun hemisphere, no new light.
Our changes: seeded from our sha256 stream instead of an RNG, returns raw bytes, tier-scaled bake size.

MIT License

Copyright (c) 2026 Paulius

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR OTHER DEALINGS IN THE SOFTWARE.
