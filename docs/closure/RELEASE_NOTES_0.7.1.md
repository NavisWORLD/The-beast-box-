# Beast Box 0.7.1 — Synapse Trace layout patch

**Release-hardened experimental software. Not universal production-ready software.**

Beast Box 0.7.1 is a narrow patch release built from the current verified source. It preserves the v0.7.0 release and its public audit result as historical evidence rather than replacing or rewriting those artifacts.

## What changed

- Fixed long Synapse Trace / provenance JSON forcing browser panels wider than the viewport.
- Applied the containment and safe wrapping correction across COSMIC.CYPHER, the modular HTML runtime, and the literal standalone HTML client shipped in the combined kit.
- Added real Chromium regression checks for the trace surface at desktop and 390 px mobile widths, including opened COSMIC technical details.
- Kept the runtime authority model, continuity semantics, memory behavior, model-provider boundary, and scientific claim boundaries unchanged.

## Release discipline

The v0.7.0 public stranger audit remains immutable historical evidence. The source correction is distributed only under the new v0.7.1 tag. This release workflow refuses stale `main`, requires the exact package version, reruns canonical/product/configuration/web/platform gates, rebuilds source-bound artifacts, regenerates checksums and release provenance, and then tests the published download separately.

## Scope and limitations

Beast Box remains a local-first experimental AI runtime and research/product harness. Deterministic reference providers used by acceptance tests are fixtures, not claims about trained model quality. iOS signing and physical-device validation remain external gates. Android may use debug signing when an owner release keystore is not supplied. Optional IBM/Azure workloads require owner credentials and do not establish quantum advantage, consciousness, sentience, biological life, or new physics.

## Patch acceptance target

A v0.7.1 release is accepted only when exact-source release gates complete successfully, public checksums validate, the public wheel installs in a blank environment, continuity survives restart/export/import, default tool authority remains denied, tampered portable state is rejected, both browser surfaces start from the public artifacts, and the post-publication stranger smoke succeeds.