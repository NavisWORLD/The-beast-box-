# Validated Act II cartridge integration — 2026-10-13

The native game is preserved. This change repairs the web download endpoint's stale V11.8 digest, 1 MB exact-size assertion and 1.5 MB stream ceiling. The existing iframe already uses the native project's published release; no replacement emulator or game engine was introduced.

## Authoritative native evidence

- Native main: `e823f5fb01efabc7b2ecae2b0d85940db44714f7`, merged native PR [#65](https://github.com/NavisWORLD/Cosmic-synapse-the-living-universe-sim-engine-/pull/65).
- Established native build/controller QA: [run 38378844099](https://github.com/NavisWORLD/Cosmic-synapse-the-living-universe-sim-engine-/actions/runs/38378844099).
- Runtime cartridge: **2,097,152 bytes**, header `COSMOS V11.9`, SHA-256 `425e2ace92a7c2c3d15db9b1cdd61ef538ddf46510255a2857afa27e613657c2`.
- CI compiled imported-beast QA cartridge: `1211e1942a804f5ac420c45e08177842150c491fb460af76ba5e2db6acca5b03`; matching ELF `c2e4dc93b688e9019d21d71821bb447f4548d119940696fde279b87ca8d70674`. This QA artifact is distinct from the published runtime.
- Actual local mGBA controller-only replay used that exact QA ROM/ELF and the controller-earned Act I battery, without memory writes or injected savestates. Quests Q10–Q14 completed; the second cold boot retained Act II state. `act2_controller_report.json` reported `passed:true` and `cold_boot_passed:true`.

The local native build command was also attempted and failed because `clang` is absent. It is not reported as a successful local build. The exact authoritative CI build above remains the build evidence.

## Web verification

- The strict cartridge-pin regression failed before repair and passed afterward (7/7 focused cases).
- Full current-main application suite: 460 tests, 454 passed, zero failed, six existing skips. Typecheck and production build passed.
- Actual built Next.js `/api/gba-rom` fetched the published native runtime over HTTP, returned status 200 and exactly 2,097,152 bytes; SHA-256 and GBA header matched. `/api/gba-release` reported the same digest, size and native main revision. No fixture replaced the upstream response.
- The public browser workflow now builds and boots the exact Act II native revision instead of the old source pin. Its hosted result must pass before merge.

No research checkpoint, quantum receipt, personal memory, SRAM layout, quest flag or original cartridge source was changed. Physical-device and audible-output testing are separate from these automated checks.
